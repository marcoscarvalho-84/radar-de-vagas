"""Prepara a pasta de dados, recebe quem chega e roda a demonstração.

    bin/radar         primeira vez: cria meus-dados/, mostra a abertura no terminal e abre
                      a tela de boas-vindas no navegador; depois disso, abre o painel
    bin/radar init    cria meus-dados/ com os arquivos vazios que o questionário preenche
    bin/radar demo    sobe o painel em cima de uma CÓPIA dos exemplos, com as datas
                      trazidas para hoje (os exemplos não envelhecem)
"""

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from . import caminhos
from .arquivos import gravar_json, ler_json

CONFIG_VAZIO = {
    "_leia": "Suas preferências. Preencha com /radar-configurar. Campo vazio = a rotina PERGUNTA antes de responder um formulário.",
    "objetivo": {"portas": [], "senioridade_minima": "", "dominios_fortes": [], "dominios_evitar": [], "o_que_busca": ""},
    "trabalho": {"cidade_base": "", "modelos_aceitos": [], "hibrido_ou_presencial_so_em": [],
                 "aceita_internacional": None, "autorizacao_trabalho": "", "exige_visto_ou_relocation": "perguntar"},
    "remuneracao": {"regra": "", "clt_mensal": "", "pj_mensal": "", "usd_anual": "", "piso": "", "ultima_remuneracao": "perguntar"},
    "disponibilidade": "",
    "fit": {"pesos": {"dominio": 25, "senioridade": 20, "porta": 20, "escopo": 20, "modelo": 15},
            "fit_minimo_para_aprofundar": 60, "vagas_trabalhadas_por_dia": 2},
    "pessoas": {"por_vaga": 3, "papeis": ["recruiter da vaga", "hiring manager provável", "head ou director da área, ou par sênior"]},
    "cv": {"idioma_padrao": "", "perguntar_antes_de_traduzir": True, "nome_arquivo": "{Nome}-CV-{Empresa}-{Cargo}.pdf", "secao_why": True,
           "diferencial": ""},
    "carta": {"quando": "só quando o formulário pedir", "palavras_min": 120, "palavras_max": 200},
    "formulario": {"senioridade_declarada": "",
                   "nunca_preencher": ["documentos (CPF, RG, passaporte)", "dados bancários", "endereço completo",
                                       "autodeclaração de diversidade", "senha, conta nova ou captcha"],
                   "sempre_perguntar": ["aceites jurídicos fora do padrão", "perguntas de saúde ou vida pessoal",
                                        "vaga com relocation ou visto"]},
    "estilo": {"tom": "", "proibicoes": [], "max_frases_de_efeito_por_resposta": 1},
    "rotina": {"horario": "", "janela_horas": 48, "follow_up_dias": 7, "triagem_expira_dias": 14, "aprovado_alerta_dias": 3},
    "painel": {"porta": 8322},
}

FATOS_MODELO = """# Fatos confirmados

A ÚNICA fonte de fatos para CV, carta e formulário. Nada fora daqui (ou do perfil.json
confirmado) aparece como fato em seu nome. Cada fato leva a data em que você confirmou.

## Provas com número
<!-- - Reduzi o abandono do checkout em 12% (A/B, Loja X, 2020). Confirmado em AAAA-MM-DD -->

## Escopo real de cada experiência
<!-- ### Empresa · Cargo (AAAA-MM a AAAA-MM)
- o que era seu de verdade, tamanho de time, produtos, público -->

## O que você NÃO tem (para responder com honestidade)
<!-- - Nunca trabalhei com app nativo; o mais perto foi ... -->
"""


def init(silencioso: bool = False) -> Path:
    pasta = caminhos.dados()
    pasta.mkdir(parents=True, exist_ok=True)
    criados = []
    for caminho, conteudo in (
        (caminhos.config(), CONFIG_VAZIO),
        (caminhos.vagas(), {"data": "", "resumo_busca": "", "vagas": [], "pessoas": []}),
        (caminhos.registro(), {"leva": 1, "leva_inicio": date.today().isoformat(), "dias": []}),
        (caminhos.decisoes(), {"decisoes": []}),
    ):
        if not caminho.exists():
            gravar_json(caminho, conteudo)
            criados.append(caminho.name)
    if not caminhos.buscas().exists():
        shutil.copyfile(caminhos.EXEMPLOS / "buscas.json", caminhos.buscas())
        criados.append("buscas.json")
    if not caminhos.fatos().exists():
        caminhos.fatos().write_text(FATOS_MODELO, encoding="utf-8")
        criados.append("fatos.md")
    for sub in (caminhos.cvs(), caminhos.arquivo(), caminhos.varredura(), pasta / "anexos"):
        sub.mkdir(exist_ok=True)
    if silencioso:
        return pasta
    print(f"Pasta de dados: {pasta}")
    print("Criados: " + (", ".join(criados) if criados else "nada (já existia tudo)"))
    print("Próximo passo: rode bin/radar para abrir a tela de abertura no navegador")
    return pasta


def abertura_terminal(porta: int) -> None:
    """O que aparece no terminal na primeira vez, antes do navegador abrir."""
    cor = sys.stdout.isatty()
    negrito = (lambda t: f"\033[1m{t}\033[0m") if cor else (lambda t: t)
    marca = (lambda t: f"\033[1;30;103m {t} \033[0m") if cor else (lambda t: t)
    linhas = [
        "",
        f"  {negrito('RADAR DE')} {marca('VAGAS')}",
        "  Aplicar é fácil. Aplicar bem é raro.",
        "",
        "  Varre vagas novas, dá a cada uma uma nota de fit honesta, aprofunda as",
        "  melhores, gera o CV sob medida e mapeia quem contatar. Nada sai sem o seu ok.",
        "",
        f"  {negrito('Primeira vez aqui.')} A tela de abertura vai abrir no seu navegador:",
        "  5 passos (LinkedIn, CV, e-mail, portfólio e anexos), uns 5 minutos.",
        f"  Tudo fica em {caminhos.dados()}, no seu computador.",
        "",
        f"  → http://localhost:{porta}/boas-vindas",
        "",
    ]
    print("\n".join(linhas), flush=True)


DATA_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _deslocar(obj, dias: int):
    """Soma `dias` a toda string que começa com AAAA-MM-DD."""
    if isinstance(obj, dict):
        return {k: _deslocar(v, dias) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deslocar(v, dias) for v in obj]
    if isinstance(obj, str):
        m = DATA_ISO.match(obj)
        if m:
            try:
                nova = date.fromisoformat(m.group(1)) + timedelta(days=dias)
                return nova.isoformat() + obj[10:]
            except ValueError:
                return obj
    return obj


def preparar_demo() -> Path:
    destino = Path(tempfile.gettempdir()) / "radar-de-vagas-demo"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir()
    base = date.fromisoformat(ler_json(caminhos.EXEMPLOS / "vagas.json")["data"])
    dias = (date.today() - base).days
    for nome in ("vagas.json", "registro.json", "config.json", "perfil.json", "buscas.json", "contexto.json"):
        dados = json.loads((caminhos.EXEMPLOS / nome).read_text(encoding="utf-8"))
        gravar_json(destino / nome, _deslocar(dados, dias))
    gravar_json(destino / "decisoes.json", {"decisoes": []})
    (destino / "cvs").mkdir()
    os.environ["RADAR_DADOS"] = str(destino)
    pdf = destino / "cvs" / "Ana-Souza-CV-Acme-Staff-Product-Designer.pdf"
    try:  # o CV de exemplo é opcional: sem weasyprint a demo sobe sem ele
        from . import cv
        cv.gerar(caminhos.EXEMPLOS / "cv-exemplo.json", pdf)
    except (SystemExit, Exception) as e:
        print(f"(demo sem PDF de exemplo: {e})")
    # sem o arquivo, o painel apontaria para um 404: tira o link em vez de quebrar
    vagas = ler_json(destino / "vagas.json")
    for v in vagas["vagas"]:
        for campo, arquivo in (("cv", pdf), ("cv_preview", pdf.with_suffix(".png"))):
            if v.get(campo) and not arquivo.exists():
                v[campo] = ""
    gravar_json(destino / "vagas.json", vagas)
    return destino
