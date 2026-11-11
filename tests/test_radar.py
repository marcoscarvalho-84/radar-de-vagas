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


if __name__ == "__main__":
    unittest.main()
