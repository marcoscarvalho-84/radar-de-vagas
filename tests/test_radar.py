"""Testes do Radar: python3 -m unittest discover tests

Só biblioteca padrão. Cada teste roda numa pasta temporária (RADAR_DADOS), nunca nos
seus dados. Os testes de PDF pulam sozinhos quando o weasyprint não está instalado.
"""

import http.client
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import zipfile
from datetime import date, timedelta
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLOS = RAIZ / "exemplos"


class ComDados(unittest.TestCase):
    """Base: uma cópia dos exemplos numa pasta temporária."""

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp(prefix="radar-teste-"))
        for f in EXEMPLOS.glob("*.json"):
            shutil.copy(f, self.pasta / f.name)
        (self.pasta / "decisoes.json").write_text('{"decisoes": []}', encoding="utf-8")
        self._antes = os.environ.get("RADAR_DADOS")
        os.environ["RADAR_DADOS"] = str(self.pasta)

    def tearDown(self):
        if self._antes is None:
            os.environ.pop("RADAR_DADOS", None)
        else:
            os.environ["RADAR_DADOS"] = self._antes
        shutil.rmtree(self.pasta, ignore_errors=True)

    def ler(self, nome):
        return json.loads((self.pasta / nome).read_text(encoding="utf-8"))


class TestIds(unittest.TestCase):
    def test_max_mais_um_e_nao_tamanho_da_lista(self):
        from radar.ids import proximo_id
        itens = [{"id": "vaga-1"}, {"id": "vaga-7"}]  # vaga-2..6 foram arquivadas
        self.assertEqual(proximo_id(itens, "vaga"), "vaga-8")

    def test_piso_de_leva_arquivada(self):
        from radar.ids import proximo_id
        self.assertEqual(proximo_id([], "pessoa", piso=300), "pessoa-301")


class TestArquivos(ComDados):
    def test_gravacao_concorrente_nao_perde_escrita(self):
        from radar.arquivos import editar_json
        alvo = self.pasta / "contador.json"

        def somar():
            for _ in range(25):
                with editar_json(alvo, {"n": 0}) as d:
                    d["n"] += 1

        threads = [threading.Thread(target=somar) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(self.ler("contador.json")["n"], 200)


class TestServidor(ComDados):
    def setUp(self):
        super().setUp()
        from radar import servidor
        from radar import caminhos
        servidor.gerar_dados.gerar()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(servidor.Handler, directory=str(caminhos.painel())))
        self.porta = self.srv.server_address[1]
        servidor.Handler.porta = self.porta
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def post(self, corpo, tipo="application/json", origem=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        h = {"Content-Type": tipo, "Host": host or f"localhost:{self.porta}"}
        if origem:
            h["Origin"] = origem
        c.request("POST", "/api/decisao", body=json.dumps(corpo), headers=h)
        r = c.getresponse()
        return r.status, json.loads(r.read() or b"{}"), dict(r.getheaders())

    def status_de(self, id_):
        d = self.ler("vagas.json")
        return next(x for x in d["vagas"] + d["pessoas"] if x["id"] == id_)

    def test_aprovar_grava_status_data_e_fila(self):
        st, res, cab = self.post({"id": "vaga-1", "acao": "aprovar"})
        self.assertEqual(st, 200, res)
        self.assertEqual(self.status_de("vaga-1")["status"], "aprovado")
        self.assertIn("aprovado_em", self.status_de("vaga-1"))
        self.assertEqual(self.ler("decisoes.json")["decisoes"][-1]["acao"], "aprovar")
        self.assertNotIn("Access-Control-Allow-Origin", cab)

    def test_recusa_post_de_outro_site(self):
        st, _, _ = self.post({"id": "vaga-1", "acao": "aprovar"}, origem="https://site-qualquer.com")
        self.assertEqual(st, 403)
        self.assertEqual(self.status_de("vaga-1")["status"], "proposto")

    def test_recusa_post_text_plain(self):
        st, _, _ = self.post({"id": "vaga-1", "acao": "aprovar"}, tipo="text/plain")
        self.assertEqual(st, 415)
        self.assertEqual(self.status_de("vaga-1")["status"], "proposto")

    def test_recusa_host_estranho(self):
        st, _, _ = self.post({"id": "vaga-1", "acao": "aprovar"}, host="evil.example:80")
        self.assertEqual(st, 403)

    def test_ajuste_sem_nota_e_recusado(self):
        st, res, _ = self.post({"id": "vaga-1", "acao": "ajustar", "nota": "  "})
        self.assertEqual(st, 400, res)

    def test_cliques_simultaneos_nao_se_perdem(self):
        ids = ["vaga-1", "vaga-3", "vaga-4", "vaga-5", "pessoa-1", "pessoa-2", "pessoa-3"]
        threads = [threading.Thread(target=self.post, args=({"id": i, "acao": "pular"},)) for i in ids * 3]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(self.ler("decisoes.json")["decisoes"]), len(ids) * 3)
        self.assertTrue(all(self.status_de(i)["status"] == "recusado" for i in ids))

    def test_cvs_nao_escapa_da_pasta(self):
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        c.request("GET", "/cvs/../config.json", headers={"Host": f"localhost:{self.porta}"})
        self.assertEqual(c.getresponse().status, 404)


class TestValidar(ComDados):
    def test_exemplos_sem_erro(self):
        from radar import validar
        erros = [m for n, m in validar.checar_tudo() if n == "erro"]
        self.assertEqual(erros, [])

    def test_aplicada_no_registro_e_pendente_no_radar_e_erro(self):
        from radar import validar
        vagas = self.ler("vagas.json")
        vagas["vagas"][0]["status"] = "proposto"
        registro = {"dias": [{"data": "2026-11-10", "vagas": [
            {"empresa": "Acme Pagamentos", "cargo": "Staff Product Designer, Plataforma",
             "status": "Aplicada", "data_candidatura": "2026-11-10"}]}]}
        achados = validar.checar_consistencia(vagas, registro)
        self.assertTrue(any("vaga-1" in m for n, m in achados if n == "erro"))

    def test_link_de_busca_vira_aviso(self):
        from radar import validar
        vagas = {"vagas": [{"id": "vaga-1", "empresa": "X", "cargo": "Y", "status": "proposto", "fit": 70,
                            "profundidade": "triagem", "adicionada_em": "2026-11-10",
                            "url": "https://www.linkedin.com/jobs/search/?keywords=design"}], "pessoas": []}
        self.assertTrue(any("permalink" in m for _, m in validar.checar_vagas(vagas)))


class TestManutencao(ComDados):
    def test_expirar_so_mexe_com_aplicar(self):
        from radar import manutencao
        vagas = self.ler("vagas.json")
        for v in vagas["vagas"]:
            v["adicionada_em"] = date.today().isoformat()
        vagas["vagas"][3]["adicionada_em"] = (date.today() - timedelta(days=30)).isoformat()  # vaga-4
        (self.pasta / "vagas.json").write_text(json.dumps(vagas), encoding="utf-8")
        self.assertEqual(len(manutencao.expirar(14, aplicar=False)), 1)
        self.assertEqual(self.ler("vagas.json")["vagas"][3]["status"], "proposto")
        manutencao.expirar(14, aplicar=True)
        self.assertEqual(self.ler("vagas.json")["vagas"][3]["status"], "recusado")

    def test_arquivar_recomeca_vazio_e_preserva_ids(self):
        from radar import manutencao
        manutencao.arquivar()
        self.assertEqual(self.ler("vagas.json")["vagas"], [])
        self.assertTrue((self.pasta / "arquivo" / "leva-1" / "vagas.json").exists())
        self.assertEqual(manutencao.proximo("vaga"), "vaga-8")


class TestVarredura(ComDados):
    def test_filtro_por_palavra_inteira_e_duplicata(self):
        from radar import varredura
        hoje = date.today().isoformat()
        coleta = {"vagas": [
            {"id": "1", "titulo": "Senior Product Designer", "empresa": "Nova", "data": hoje},
            {"id": "2", "titulo": "Auxiliar de Produção Sênior", "empresa": "Fábrica", "data": hoje},
            {"id": "3", "titulo": "Junior Product Designer", "empresa": "Nova", "data": hoje},
            {"id": "4", "titulo": "Staff Product Designer, Plataforma", "empresa": "Acme Pagamentos", "data": hoje},
            {"id": "5", "titulo": "Senior Product Designer", "empresa": "Nova", "data": hoje},
            {"id": "1000000003", "titulo": "Senior Product Designer", "empresa": "Outra", "data": hoje},
        ]}
        entrada = self.pasta / "coleta.json"
        entrada.write_text(json.dumps(coleta), encoding="utf-8")
        candidatas = varredura.filtra(entrada, self.pasta / "candidatas.json")
        self.assertEqual([c["id"] for c in candidatas], ["1"])

    def test_duplicata_no_arquivo_tambem_conta(self):
        from radar import varredura
        leva = self.pasta / "arquivo" / "leva-1"
        leva.mkdir(parents=True)
        (leva / "vagas.json").write_text(json.dumps({"vagas": [
            {"id": "vaga-1", "empresa": "Velha SA", "cargo": "Senior Product Designer"}]}), encoding="utf-8")
        _, pares = varredura._ja_no_radar()
        self.assertIn(varredura.chave("Velha S.A.", "Senior Product Designer"), pares)


class TestPerfil(ComDados):
    def test_importa_export_do_linkedin_sem_dados_de_terceiros(self):
        from radar import perfil
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Profile.csv", "First Name,Last Name,Headline,Summary,Geo Location,Websites\n"
                                      "Bia,Costa,Senior PD,Resumo,Recife,https://bia.example.com\n")
            z.writestr("Positions.csv", "Company Name,Title,Description,Location,Started On,Finished On\n"
                                        "Empresa X,Designer,Fez coisas,Recife,Mar 2021,\n")
            z.writestr("Connections.csv", "Notes:\nNão leia isto\n\nFirst Name,Last Name\nFulano,De Tal\n")
        origem = self.pasta / "export.zip"
        origem.write_bytes(buf.getvalue())
        (self.pasta / "perfil.json").unlink()
        destino = perfil.importar(origem)
        p = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(p["nome"], "Bia Costa")
        self.assertEqual(p["experiencias"][0]["inicio"], "2021-03")
        self.assertEqual(p["experiencias"][0]["fim"], "atual")
        self.assertNotIn("Fulano", destino.read_text(encoding="utf-8"))

    def test_nao_sobrescreve_perfil_existente(self):
        from radar import perfil
        origem = self.pasta / "csvs"
        origem.mkdir()
        (origem / "Profile.csv").write_text("First Name,Last Name\nBia,Costa\n", encoding="utf-8")
        destino = perfil.importar(origem)
        self.assertEqual(destino.name, "perfil.importado.json")
        self.assertEqual(self.ler("perfil.json")["nome"], "Ana Souza")


class TestCartaECv(ComDados):
    def test_corpo_da_carta_ignora_cabecalho(self):
        from radar.carta import corpo_da_carta
        md = "Vaga: X\nÂngulo: Y\n---\nPrimeiro parágrafo\ncontinua.\n\nSegundo."
        self.assertEqual(corpo_da_carta(md), ["Primeiro parágrafo continua.", "Segundo."])

    def test_cv_sem_dados_pessoais_fixos(self):
        from radar import cv
        html = cv.montar_html(json.loads((EXEMPLOS / "cv-exemplo.json").read_text(encoding="utf-8")),
                              self.ler("perfil.json"))
        self.assertIn("Ana<br>Souza", html)
        self.assertNotIn("{{", html)

    def test_cv_gera_uma_pagina(self):
        try:
            import weasyprint  # noqa: F401
        except Exception:
            self.skipTest("weasyprint não instalado")
        from radar import cv
        self.assertEqual(cv.gerar(EXEMPLOS / "cv-exemplo.json", self.pasta / "cvs" / "teste.pdf"), 0)


class TestPainel(ComDados):
    def test_painel_vai_para_dados_e_nao_para_o_modelo(self):
        from radar import gerar_dados
        modelo = (RAIZ / "dashboard" / "index.html").read_text(encoding="utf-8")
        saida = Path(gerar_dados.gerar())
        self.assertTrue(str(saida).startswith(str(self.pasta.resolve())))
        self.assertIn("Acme Pagamentos", saida.read_text(encoding="utf-8"))
        self.assertEqual(modelo, (RAIZ / "dashboard" / "index.html").read_text(encoding="utf-8"))

    def test_config_do_painel_nao_vaza_pretensao(self):
        from radar import config
        cfg = config.carregar()
        cfg["remuneracao"]["clt_mensal"] = "R$ 99.999"
        recorte = config.para_painel(cfg, self.ler("perfil.json"))
        self.assertNotIn("99.999", json.dumps(recorte, ensure_ascii=False))
        self.assertTrue(recorte["pretensao_definida"])

    def test_portas_do_painel_vem_da_config_de_cada_pessoa(self):
        from radar import config
        cfg = config.carregar()
        cfg["objetivo"]["portas"] = [{"id": "analise", "titulo": "Análise", "cargos": ["Data Analyst"]},
                                     {"titulo": "sem id, fica de fora"}]
        self.assertEqual(config.para_painel(cfg, {})["portas"], [{"id": "analise", "titulo": "Análise"}])
        modelo = (RAIZ / "dashboard" / "index.html").read_text(encoding="utf-8")
        for fixo in ('"lideranca"', '"ic"', "IC sênior"):  # nada de porta de uma pessoa só no código
            self.assertNotIn(fixo, modelo)


def export_linkedin(com_conexoes=True) -> bytes:
    """Um export mínimo do LinkedIn, com um CSV de terceiros que nunca pode ser lido."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Profile.csv", "First Name,Last Name,Headline,Summary,Geo Location,Websites\n"
                                  "Bia,Costa,Senior PD,Resumo,Recife,https://bia.example.com\n")
        z.writestr("Positions.csv", "Company Name,Title,Description,Location,Started On,Finished On\n"
                                    "Empresa X,Designer,Fez coisas,Recife,Mar 2021,\n")
        z.writestr("Email Addresses.csv", "Email Address,Confirmed,Primary\nBia@Example.com,Yes,Yes\n")
        if com_conexoes:
            z.writestr("Connections.csv", "First Name,Last Name\nFulano,De Tal\n")
    return buf.getvalue()


class TestBuscas(ComDados):
    """As buscas nascem das posições da pessoa, nunca dos cargos do exemplo."""

    def setUp(self):
        super().setUp()
        for nome in ("contexto.json", "buscas.json"):
            (self.pasta / nome).unlink()
        (self.pasta / "perfil.json").write_text(json.dumps({
            "nome": "Bia Costa", "headline": "Analista de Dados | SQL e Python", "local": "Recife, Pernambuco, Brazil",
            "experiencias": [
                {"empresa": "Velha", "cargo": "Analista de BI", "inicio": "2018-01", "fim": "2021-02"},
                {"empresa": "Nova", "cargo": "Analista de Dados Sênior", "inicio": "2021-03", "fim": "atual"},
            ]}), encoding="utf-8")

    def test_init_cria_buscas_vazio_sem_o_exemplo(self):
        from radar import inicio
        inicio.init(silencioso=True)
        texto = (self.pasta / "buscas.json").read_text(encoding="utf-8")
        self.assertEqual(json.loads(texto)["grupos"], [])
        self.assertNotIn("Designer", texto)

    def test_posicoes_viram_buscas_no_pais_do_perfil(self):
        from radar import contexto
        r = contexto.salvar({"posicoes": ["Data Analyst", " data  analyst ", "Analista de Dados Sênior"]})
        self.assertEqual(r["posicoes"], ["Data Analyst", "Analista de Dados Sênior"])
        self.assertTrue(r["feitos"]["posicoes"])
        b = self.ler("buscas.json")
        self.assertEqual(b["origem"], "posicoes")
        self.assertEqual(b["grupos"], [{"local": "Brazil", "palavras_chave": ["Data Analyst", "Analista de Dados Sênior"]}])
        # a sugestão vem da trajetória, mais recente primeiro, sem repetir o que já foi escolhido
        self.assertEqual(r["sugestoes_posicoes"], ["Analista de Dados", "Analista de BI"])

    def test_exemplo_e_substituido_mas_o_questionario_nao(self):
        from radar import buscas, contexto
        shutil.copy(EXEMPLOS / "buscas.json", self.pasta / "buscas.json")
        self.assertTrue(buscas.e_exemplo(buscas.ler()))
        contexto.salvar({"posicoes": ["Analista de Dados"]})
        self.assertEqual(buscas.palavras(buscas.ler()), ["Analista de Dados"])
        refinado = {**buscas.ler(), "origem": "questionario",
                    "grupos": [{"local": "Brazil", "palavras_chave": ["Data Analyst", "Analista de Dados"]}]}
        (self.pasta / "buscas.json").write_text(json.dumps(refinado), encoding="utf-8")
        r = contexto.salvar({"posicoes": ["Cientista de Dados"]})
        self.assertEqual(buscas.palavras(buscas.ler()), ["Data Analyst", "Analista de Dados"])
        self.assertEqual(r["buscas"]["origem"], "questionario")

    def test_coleta_recusa_sem_palavra_chave_e_com_o_exemplo(self):
        from radar import buscas, varredura
        from radar.arquivos import gravar_json
        gravar_json(self.pasta / "buscas.json", buscas.vazio())
        with self.assertRaises(SystemExit):
            varredura.coleta(24, self.pasta / "coleta.json")
        shutil.copy(EXEMPLOS / "buscas.json", self.pasta / "buscas.json")
        with self.assertRaises(SystemExit) as erro:
            varredura.coleta(24, self.pasta / "coleta.json")
        self.assertIn("exemplo", str(erro.exception))
        self.assertFalse((self.pasta / "coleta.json").exists())

    def test_posicoes_invalidas(self):
        from radar import contexto
        for posicoes in (["x"], ["Analista"] * 1 + [f"Cargo {i}" for i in range(8)], "Analista"):
            with self.assertRaises(contexto.ContextoInvalido, msg=posicoes):
                contexto.salvar({"posicoes": posicoes})
        self.assertFalse((self.pasta / "buscas.json").exists())


class TestIdiomaDaBusca(ComDados):
    """País que pede outra língua: a pessoa sabe antes da varredura que a mesa vai encolher."""

    PERFIL = {"local": "Recife, Pernambuco, Brazil", "idiomas": [
        {"idioma": "Portuguese", "nivel": "Native or bilingual proficiency"},
        {"idioma": "English", "nivel": "Full professional proficiency"},
        {"idioma": "French", "nivel": "Elementary proficiency"}]}

    def busca(self, *locais):
        return {"grupos": [{"local": local, "palavras_chave": ["Product Designer"]} for local in locais]}

    def test_pais_que_pede_lingua_sem_fluencia_avisa(self):
        from radar import buscas
        avisos = buscas.avisos_idioma(self.busca("Paris, Île-de-France, France", "Brazil"), self.PERFIL)
        self.assertEqual(len(avisos), 1)
        self.assertIn("francês", avisos[0])

    def test_fluente_regiao_e_pais_anglofono_nao_avisam(self):
        from radar import buscas
        fluente = {**self.PERFIL, "idiomas": [{"idioma": "Francês", "nivel": "Proficiência profissional completa"}]}
        self.assertEqual(buscas.avisos_idioma(self.busca("France"), fluente), [])
        self.assertEqual(buscas.avisos_idioma(self.busca("European Union", "United Kingdom", "EMEA"), self.PERFIL), [])

    def test_nivel_do_linkedin_em_portugues(self):
        from radar import buscas
        limitado = {"idiomas": [{"idioma": "Alemão", "nivel": "Proficiência de trabalho limitada"}]}
        self.assertEqual(len(buscas.avisos_idioma(self.busca("Alemanha"), limitado)), 1)

    def test_sem_idiomas_no_perfil_so_avisa_fora_do_pais_da_pessoa(self):
        from radar import buscas
        sem_idiomas = {"local": "Lyon, Auvergne-Rhône-Alpes, France"}
        self.assertEqual(buscas.avisos_idioma(self.busca("France"), sem_idiomas), [])
        avisos = buscas.avisos_idioma(self.busca("Germany"), sem_idiomas)
        self.assertIn("não lista idiomas", avisos[0])

    def test_aviso_chega_na_tela_e_no_validar(self):
        from radar import buscas, validar
        from radar.arquivos import gravar_json
        gravar_json(self.pasta / "perfil.json", {**self.ler("perfil.json"), **self.PERFIL})
        gravar_json(self.pasta / "buscas.json", {**buscas.vazio(), "origem": "posicoes", **self.busca("France")})
        self.assertEqual(len(buscas.resumo(buscas.ler(), self.PERFIL)["avisos"]), 1)
        self.assertTrue(any("francês" in m for _, m in validar.checar_buscas()))


class TestAts(unittest.TestCase):
    """A vaga direto no quadro público da empresa, sem depender do login no LinkedIn."""

    def test_identificadores_do_nome_da_empresa(self):
        from radar import ats
        self.assertEqual(ats.identificadores("Acme Corp S.A."), ["acmecorp", "acme-corp", "acme"])
        self.assertEqual(ats.identificadores("Figma"), ["figma"])

    def test_acha_a_vaga_no_quadro_e_para_no_primeiro_identificador_que_existe(self):
        from radar import ats
        pedidos = []

        def falso(url):
            pedidos.append(url)
            if url == ats.QUADROS["Greenhouse"].format("acmecorp"):
                return {"jobs": [
                    {"title": "Account Executive", "absolute_url": "https://boards.greenhouse.io/acmecorp/jobs/1"},
                    {"title": "Senior Product Designer, Payments", "absolute_url": "https://boards.greenhouse.io/acmecorp/jobs/2",
                     "location": {"name": "Remote"}}]}
            return None

        r = ats.procurar("Acme Corp", "Senior Product Designer", baixar=falso)
        self.assertEqual(r["quadros"], [{"ats": "Greenhouse", "slug": "acmecorp", "abertas": 2}])
        self.assertEqual([v["url"] for v in r["vagas"]], ["https://boards.greenhouse.io/acmecorp/jobs/2"])
        self.assertFalse(any("acme-corp" in u for u in pedidos))

    def test_sem_quadro_nenhum(self):
        from radar import ats
        r = ats.procurar("Ninguém", "Designer", baixar=lambda url: None)
        self.assertEqual(r, {"quadros": [], "vagas": []})


class TestRetornoDeUso(ComDados):
    """O que quebrou ou atrasou no primeiro uso de outra pessoa."""

    def test_onde_se_candidata(self):
        from radar import varredura
        self.assertEqual(varredura._candidatura('<a class="apply-link-offsite x">'), "externa")
        self.assertEqual(varredura._candidatura('<button class="apply-link-onsite">'), "linkedin")
        self.assertEqual(varredura._candidatura("<p>sem botão</p>"), "")

    def test_rendimento_por_palavra_chave(self):
        from radar import varredura
        coletadas = [{"palavra_chave": "revenue", "titulo": f"Revenue Manager Hotel {i}"} for i in range(5)]
        coletadas += [{"palavra_chave": "product designer", "titulo": "Senior Product Designer"}]
        candidatas = coletadas[:2] + coletadas[-1:]
        r = varredura.por_palavra(coletadas, candidatas)
        self.assertEqual(list(r), ["revenue", "product designer"])
        self.assertEqual((r["revenue"]["coletadas"], r["revenue"]["candidatas"]), (5, 2))
        self.assertIn("Revenue Manager Hotel 0", r["revenue"]["titulos"])

    def test_biblioteca_faltando_vira_comando_que_resolve(self):
        from unittest import mock
        from radar import cv
        erro = OSError("cannot load library 'libgobject-2.0-0': dlopen(libgobject-2.0-0, 0x0002): tried: ...")
        self.assertIn("glib", cv.diagnostico(erro))
        importar = __import__

        def sem_glib(nome, *args, **kwargs):
            if nome == "weasyprint":
                raise erro
            return importar(nome, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=sem_glib):
            with self.assertRaises(SystemExit) as saida:
                cv.motor()
        self.assertIn("glib", str(saida.exception))

    def test_url_candidatura_tem_que_ser_do_ats(self):
        from radar import validar
        base = {"id": "vaga-1", "empresa": "X", "cargo": "Y", "status": "proposto", "fit": 70,
                "profundidade": "completa", "adicionada_em": "2026-11-10",
                "url": "https://www.linkedin.com/jobs/view/123"}
        ruim = {"vagas": [{**base, "url_candidatura": "https://www.linkedin.com/jobs/view/123"}], "pessoas": []}
        boa = {"vagas": [{**base, "url_candidatura": "https://jobs.lever.co/x/abc"}], "pessoas": []}
        self.assertTrue(any("url_candidatura" in m for _, m in validar.checar_vagas(ruim)))
        self.assertFalse(any("url_candidatura" in m for _, m in validar.checar_vagas(boa)))


class TestFontes(ComDados):
    """Gupy e Sólides: o formato que os portais devolviam em nov/2026, sem rede."""

    def _gupy(self, id_, nome, dias=0, modelo="remote", cidade="", tipo="vacancy_type_effective", sub="acme"):
        quando = (date.today() - timedelta(days=dias)).isoformat()
        return {"id": id_, "name": nome, "careerPageName": "Acme", "type": tipo, "workplaceType": modelo,
                "city": cidade, "state": "Santa Catarina" if cidade else "", "publishedDate": quando + "T10:00:00.000Z",
                "applicationDeadline": "2027-01-01T00:00:00.000Z",
                "jobUrl": f"https://{sub}.gupy.io/job/eyJqb2JJZCI6MX0=?jobBoardSource=gupy_portal"}

    def _solides(self, id_, titulo, dias=0, modelo="remoto", slug="beta", **extra):
        return {"id": str(id_), "title": titulo, "companyName": "Beta Ltda", "slug": slug, "jobType": modelo,
                "city": {"name": "Joinville"}, "state": {"code": "SC"},
                "createdAt": (date.today() - timedelta(days=dias)).isoformat(), **extra}

    def test_vaga_de_cada_portal_vira_o_formato_da_coleta(self):
        from radar import fontes
        g = fontes.vaga_gupy(self._gupy(123, "Senior Product Designer"), "Product Designer", "Brazil")
        self.assertEqual(g["id"], "gupy-acme-123")
        self.assertEqual(g["url"], "https://acme.gupy.io/jobs/123")
        self.assertEqual((g["fonte"], g["modelo"], g["local"]), ("gupy", "remoto", "Remoto"))
        self.assertEqual(g["data"], date.today().isoformat())
        self.assertIsNone(fontes.vaga_gupy(self._gupy(9, "Banco", tipo="vacancy_type_talent_pool"), "x", "Brazil"))
        self.assertIsNone(fontes.vaga_gupy({**self._gupy(9, "X"), "jobUrl": "https://evil.com/x"}, "x", "Brazil"))
        s = fontes.vaga_solides(self._solides(77, "Product Designer", salary={
            "showRangeToApplicant": True, "initialRange": 9000, "finalRange": 12000}), "Product Designer", "Brazil")
        self.assertEqual(s["url"], "https://beta.vagas.solides.com.br/vaga/77")
        self.assertEqual((s["local"], s["salario"]), ("Joinville, SC", "R$ 9.000 a R$ 12.000"))
        self.assertIsNone(fontes.vaga_solides(self._solides(78, "X", slug="não vale"), "x", "Brazil"))
        self.assertIsNone(fontes.vaga_solides(self._solides(79, "X", receivingResume=False), "x", "Brazil"))

    def test_ids_e_links_vao_e_voltam(self):
        from radar import fontes
        for id_, url in (("4471678311", "https://www.linkedin.com/jobs/view/4471678311"),
                         ("gupy-solar-coca-12897336", "https://solar-coca.gupy.io/jobs/12897336"),
                         ("solides-inchurch-940811", "https://inchurch.vagas.solides.com.br/vaga/940811")):
            self.assertEqual(fontes.url_do_id(id_), url)
            self.assertEqual(fontes.id_da_url(url), id_)
        self.assertEqual(fontes.url_do_id("vaga-301"), "")
        self.assertEqual(fontes.fonte_do_id("gupy-acme-1"), "gupy")

    def test_coleta_so_no_brasil_para_na_janela_e_respeita_a_cidade(self):
        from radar import fontes
        chamadas = []
        gupy = [self._gupy(i, "Product Designer", dias=0) for i in range(1, 50)] + [self._gupy(50, "Product Designer", dias=5)]
        gupy[3] = self._gupy(4, "Product Designer", modelo="on-site", cidade="Joinville")
        gupy[4] = self._gupy(5, "Product Designer", modelo="hybrid", cidade="Curitiba")

        def baixar(url):
            chamadas.append(url)
            if "gupy" in url:
                return 200, json.dumps({"data": gupy if "offset=0" in url else [self._gupy(99, "Velha", dias=9)]})
            return 200, json.dumps({"data": [self._solides(7, "Product Designer")]})

        grupos = [{"local": "Curitiba, Paraná, Brazil", "palavras_chave": ["Product Designer"]},
                  {"local": "France", "palavras_chave": ["Product Designer"]},
                  {"local": "Latin America", "palavras_chave": ["Product Designer"]}]
        vagas, falhas = fontes.coletar(grupos, 48, ["gupy", "solides"], baixar, lambda: None)
        self.assertEqual(falhas, [])
        self.assertTrue(all("portal.gupy.io" in u or "solides" in u for u in chamadas))
        # uma página só: a primeira já passou da janela de 48h
        self.assertEqual(sum("gupy" in u for u in chamadas), 1)
        self.assertIn("gupy-acme-5", vagas)        # híbrida em Curitiba
        self.assertNotIn("gupy-acme-4", vagas)     # presencial em Joinville
        self.assertIn("solides-beta-7", vagas)     # remota entra em qualquer cidade
        sem_gupy, _ = fontes.coletar(grupos, 48, ["solides"], baixar, lambda: None)
        self.assertTrue(all(v["fonte"] == "solides" for v in sem_gupy.values()))

    def test_portal_fora_do_ar_marca_resultado_incompleto(self):
        from radar import fontes
        vagas, falhas = fontes.coletar([{"local": "Brazil", "palavras_chave": ["Designer"]}], 48, ["gupy"],
                                       lambda url: (0, ""), lambda: None)
        self.assertEqual((vagas, [f["fonte"] for f in falhas]), ({}, ["gupy"]))

    def test_jobposting_escapado_e_vaga_fechada(self):
        from radar import fontes
        ld = json.dumps({"@context": "http://schema.org", "@type": "JobPosting", "title": "Designer",
                         "datePosted": "2026-11-17", "validThrough": "2099-01-01",
                         "hiringOrganization": {"@type": "Organization", "name": "Acme"},
                         "description": "<p>Fazer &amp; medir</p><ul><li>Figma</li></ul>"})
        escapado = ld.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        pagina = f'<script type="application/ld+json">{escapado}</script>'
        url = "https://acme.gupy.io/jobs/1"
        aberta = fontes.ler_vaga(url, lambda u, com_url: (200, pagina, u))
        self.assertEqual((aberta["fechada"], aberta["empresa"], aberta["valida_ate"]), (False, "Acme", "2099-01-01"))
        self.assertIn("Fazer & medir", aberta["descricao"])
        grafo = f'<script type="application/ld+json">{{"@graph": [{{"@type": "WebPage"}}, {ld}]}}</script>'
        self.assertEqual(fontes.jobposting(grafo)["title"], "Designer")
        vencida = pagina.replace("2099-01-01", "2020-01-01")
        self.assertTrue(fontes.ler_vaga(url, lambda u, com_url: (200, vencida, u))["fechada"])
        login = fontes.ler_vaga(url, lambda u, com_url: (200, "<html></html>", "https://acme.gupy.io/candidates/signin"))
        self.assertTrue(login["fechada"])
        self.assertTrue(fontes.ler_vaga(url, lambda u, com_url: (404, "", u))["fechada"])
        self.assertIsNone(fontes.ler_vaga(url, lambda u, com_url: (200, "<html>sem dados</html>", u))["fechada"])

    def test_vaga_do_portal_ja_no_radar_e_duplicata(self):
        from radar import varredura
        (self.pasta / "vagas.json").write_text(json.dumps({"vagas": [
            {"id": "vaga-301", "empresa": "Outra", "cargo": "Outro", "url": "https://acme.gupy.io/jobs/123"}]}),
            encoding="utf-8")
        ids, _ = varredura._ja_no_radar()
        self.assertIn("gupy-acme-123", ids)

    def test_fonte_desconhecida_recusa(self):
        from radar import varredura
        with self.assertRaises(SystemExit):
            varredura.escolher_fontes("linkedin,catho")
        self.assertEqual(varredura.escolher_fontes("Gupy, solides"), ["gupy", "solides"])
        self.assertEqual(varredura.escolher_fontes(None), ["linkedin", "gupy", "solides"])


class TestContexto(ComDados):
    """Os 6 passos da tela de abertura, sem servidor."""

    def setUp(self):
        super().setUp()
        for nome in ("contexto.json", "perfil.json"):  # pessoa nova: sem contexto nem perfil
            (self.pasta / nome).unlink()

    def test_primeira_vez_ate_concluir(self):
        from radar import contexto
        self.assertTrue(contexto.primeira_vez())
        contexto.concluir()
        self.assertFalse(contexto.primeira_vez())

    def test_contatos_vao_para_o_perfil_sem_protocolo(self):
        from radar import contexto
        contexto.salvar({"linkedin_url": "https://www.linkedin.com/in/bia-costa/", "email": " Bia@Example.com ",
                         "portfolio": "bia.example.com", "outros_links": ["github.com/bia"]})
        p = self.ler("perfil.json")
        self.assertEqual(p["contatos"]["linkedin"], "linkedin.com/in/bia-costa")
        self.assertEqual(p["contatos"]["email"], "bia@example.com")
        self.assertEqual(p["contatos"]["portfolio"], "bia.example.com")
        ctx = self.ler("contexto.json")
        self.assertEqual(ctx["portfolio"]["outros"], ["https://github.com/bia"])
        self.assertTrue(all(contexto.estado()["feitos"][k] for k in ("linkedin", "email", "portfolio")))

    def test_recusa_entrada_invalida_sem_gravar_nada(self):
        from radar import contexto
        for campos in ({"linkedin_url": "linkedin.com/company/acme"}, {"email": "bia@"},
                       {"portfolio": "linkedin.com/in/bia"}, {"outros_links": ["a.com", "b.com", "c.com", "d.com"]}):
            with self.assertRaises(contexto.ContextoInvalido, msg=campos):
                contexto.salvar(campos)
        self.assertFalse((self.pasta / "perfil.json").exists())

    def test_nome_de_arquivo_nao_escapa_da_pasta(self):
        from radar import contexto
        r = contexto.receber("anexo", "../../../etc/Meu Caso (final).PDF", b"%PDF-1.4 teste")
        arquivo = r["anexos"][0]["arquivo"]
        self.assertEqual(arquivo, "anexos/meu-caso-final.pdf")
        self.assertTrue((self.pasta / arquivo).exists())
        r = contexto.receber("anexo", "meu caso final.pdf", b"%PDF-1.4 outro")
        self.assertEqual(r["anexos"][1]["arquivo"], "anexos/meu-caso-final-2.pdf")

    def test_confere_os_bytes_e_nao_so_a_extensao(self):
        from radar import contexto
        with self.assertRaises(contexto.ContextoInvalido):
            contexto.receber("cv", "cv.pdf", b"<html>nada de pdf</html>")
        with self.assertRaises(contexto.ContextoInvalido):
            contexto.receber("anexo", "script.sh", b"#!/bin/sh")
        with self.assertRaises(contexto.ContextoInvalido):
            contexto.receber("cv", "cv.pdf", b"")

    def test_remover_so_mexe_dentro_de_anexos(self):
        from radar import contexto
        contexto.receber("anexo", "a.txt", "certificado".encode())
        alvo = self.pasta / "config.json"
        with self.assertRaises(contexto.ContextoInvalido):
            contexto.remover("../config.json")
        self.assertTrue(alvo.exists())
        r = contexto.remover("anexos/a.txt")
        self.assertEqual(r["anexos"], [])
        self.assertFalse((self.pasta / "anexos" / "a.txt").exists())

    def test_comentario_do_anexo(self):
        from radar import contexto
        r = contexto.receber("anexo", "caso.pdf", b"%PDF-1.4 caso")
        self.assertEqual(r["anexos"][0]["comentario"], "")
        r = contexto.comentar("anexos/caso.pdf", "  Estudo de caso\n do app,  usar em vaga de fintech ")
        self.assertEqual(r["anexos"][0]["comentario"], "Estudo de caso do app, usar em vaga de fintech")
        self.assertEqual(contexto.comentar("anexos/caso.pdf", "")["anexos"][0]["comentario"], "")
        with self.assertRaises(contexto.ContextoInvalido):
            contexto.comentar("anexos/caso.pdf", "x" * (contexto.MAX_COMENTARIO + 1))
        with self.assertRaises(contexto.ContextoInvalido):
            contexto.comentar("anexos/outro.pdf", "nada")

    def test_export_completa_o_perfil_minimo_e_some_do_disco(self):
        from radar import contexto
        contexto.salvar({"linkedin_url": "linkedin.com/in/bia-costa", "email": "bia@trabalho.com"})
        r = contexto.receber("linkedin", "Basic_LinkedInDataExport.zip", export_linkedin())
        p = self.ler("perfil.json")
        self.assertEqual(p["nome"], "Bia Costa")
        self.assertEqual(p["contatos"]["linkedin"], "linkedin.com/in/bia-costa")
        self.assertEqual(p["contatos"]["email"], "bia@trabalho.com")  # o digitado vence o do export
        self.assertEqual(r["sugestoes"]["portfolio"], "https://bia.example.com")
        self.assertEqual(r["linkedin"]["fonte"], "export")
        restos = [f.name for f in self.pasta.rglob("*") if f.suffix == ".zip"]
        self.assertEqual(restos, [])
        self.assertNotIn("Fulano", "".join(f.read_text(encoding="utf-8", errors="ignore")
                                         for f in self.pasta.rglob("*") if f.is_file()))

    def test_export_nao_atropela_perfil_de_verdade(self):
        from radar import contexto
        shutil.copy(EXEMPLOS / "perfil.json", self.pasta / "perfil.json")
        r = contexto.receber("linkedin", "export.zip", export_linkedin())
        self.assertEqual(self.ler("perfil.json")["nome"], "Ana Souza")
        self.assertTrue((self.pasta / "perfil.importado.json").exists())
        self.assertIn("perfil.importado.json", r["aviso"])

    def test_cv_docx_vira_texto_e_substitui_o_anterior(self):
        from radar import contexto
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:p><w:t>Bia Costa</w:t></w:p>"
                                            "<w:p><w:t>Designer &amp; pesquisadora</w:t></w:p></w:document>")
        contexto.receber("cv", "cv-velho.docx", buf.getvalue())
        r = contexto.receber("cv", "cv-novo.docx", buf.getvalue())
        self.assertEqual(r["cv"]["arquivo"], "anexos/cv-atual.docx")
        self.assertEqual(r["cv"]["palavras"], 5)
        self.assertIn("Designer & pesquisadora", (self.pasta / "anexos" / "cv-atual.txt").read_text(encoding="utf-8"))
        self.assertEqual(sorted(f.name for f in (self.pasta / "anexos").iterdir()), ["cv-atual.docx", "cv-atual.txt"])


class TestAbertura(TestServidor):
    """A tela de abertura pelo servidor: redireciona na primeira vez e recebe arquivos."""

    def setUp(self):
        super().setUp()
        (self.pasta / "contexto.json").unlink()

    def pedir(self, metodo, rota, corpo=b"", cabecalhos=None):
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        h = {"Host": f"localhost:{self.porta}", **(cabecalhos or {})}
        c.request(metodo, rota, body=corpo, headers=h)
        r = c.getresponse()
        return r.status, r.read(), {k.lower(): v for k, v in r.getheaders()}

    def arquivo(self, conteudo, nome="caso.pdf", tipo="anexo", **extra):
        h = {"Content-Type": "application/octet-stream", "X-Radar-Tipo": tipo, "X-Radar-Nome": nome, **extra}
        st, corpo, _ = self.pedir("POST", "/api/arquivo", conteudo, h)
        return st, json.loads(corpo or b"{}")

    def test_primeira_vez_vai_para_a_abertura_e_depois_para_o_painel(self):
        st, _, cab = self.pedir("GET", "/")
        self.assertEqual((st, cab.get("location")), (302, "/boas-vindas"))
        st, corpo, cab = self.pedir("GET", "/boas-vindas")
        self.assertEqual(st, 200)
        self.assertIn("text/html", cab["content-type"])
        self.assertIn(b"Seu contexto", corpo)
        self.assertEqual(self.pedir("GET", "/boas-vindas.css")[0], 200)
        for js in ("/radar-3d.js", "/vendor/three.module.min.js"):
            st, _, cab = self.pedir("GET", js)
            self.assertEqual(st, 200, js)
            self.assertIn("javascript", cab["content-type"])  # módulo ES exige tipo JS
        st, corpo, _ = self.pedir("POST", "/api/contexto", json.dumps({"acao": "concluir"}).encode(),
                                  {"Content-Type": "application/json"})
        self.assertEqual(st, 200, corpo)
        self.assertEqual(self.pedir("GET", "/")[0], 200)

    def test_recebe_anexo_com_nome_codificado(self):
        st, r = self.arquivo(b"%PDF-1.4 caso", nome="Estudo%20de%20caso%20%C3%A1.pdf")
        self.assertEqual(st, 200, r)
        self.assertEqual(r["anexos"][0]["arquivo"], "anexos/estudo-de-caso-a.pdf")
        self.assertEqual(r["anexos"][0]["nome_original"], "Estudo de caso á.pdf")
        st, corpo, _ = self.pedir("POST", "/api/contexto",
                                  json.dumps({"acao": "comentar", "arquivo": "anexos/estudo-de-caso-a.pdf",
                                              "comentario": "Portfólio resumido"}).encode(),
                                  {"Content-Type": "application/json"})
        self.assertEqual(st, 200, corpo)
        self.assertEqual(json.loads(corpo)["anexos"][0]["comentario"], "Portfólio resumido")

    def test_arquivo_de_outro_site_ou_sem_octet_stream_e_recusado(self):
        st, _ = self.arquivo(b"%PDF-1.4", **{"Origin": "https://site-qualquer.com"})
        self.assertEqual(st, 403)
        st, _, _ = self.pedir("POST", "/api/arquivo", b"%PDF-1.4",
                              {"Content-Type": "text/plain", "X-Radar-Tipo": "anexo", "X-Radar-Nome": "a.pdf"})
        self.assertEqual(st, 415)
        self.assertFalse((self.pasta / "anexos").exists())

    def test_arquivo_falso_volta_com_mensagem(self):
        st, r = self.arquivo(b"MZ executavel", nome="foto.png")
        self.assertEqual(st, 400)
        self.assertIn(".png", r["erro"])

    def test_anexos_nao_sao_servidos(self):
        self.arquivo(b"%PDF-1.4 caso", nome="caso.pdf")
        self.assertEqual(self.pedir("GET", "/anexos/caso.pdf")[0], 404)
        self.assertEqual(self.pedir("GET", "/../anexos/caso.pdf")[0], 404)

    def test_contexto_salva_pela_api(self):
        st, corpo, _ = self.pedir("POST", "/api/contexto",
                                  json.dumps({"acao": "salvar", "campos": {"email": "nada"}}).encode(),
                                  {"Content-Type": "application/json"})
        self.assertEqual(st, 400)
        self.assertIn("e-mail", json.loads(corpo)["erro"])
        st, corpo, _ = self.pedir("GET", "/api/contexto")
        self.assertEqual(json.loads(corpo)["feitos"]["email"], False)


if __name__ == "__main__":
    unittest.main()
