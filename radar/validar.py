"""Confere os dados do Radar contra as regras de docs/esquemas.md e docs/padroes.md.

    bin/radar validar

Erro = algo que quebra o fluxo ou arrisca uma ação pública errada (id duplicado, vaga
já aplicada ainda com botão de aplicar). Aviso = algo que degrada (link fora do padrão,
campo faltando). Sai com código 1 quando há erro.
"""

import re
from datetime import date

from . import caminhos
from .arquivos import ler_json
from .varredura import chave

STATUS_VAGA = {"proposto", "aprofundar", "aprovado", "ajuste", "recusado", "executado"}
STATUS_PESSOA = STATUS_VAGA
PROFUNDIDADE = {"triagem", "completa"}
STATUS_REGISTRO = {"Analisada", "CV pronto", "Aplicada", "Networking", "Entrevista", "Oferta",
                   "Recusada", "Encerrada", "Descartada"}
STATUS_PESSOA_REGISTRO = {"mapeada", "enviado", "aceito", "respondeu"}
APLICADAS = {"Aplicada", "Networking", "Entrevista", "Oferta"}
PENDENTES = {"proposto", "aprofundar", "aprovado", "ajuste"}

URL_VAGA_LINKEDIN = re.compile(r"^https://(www\.|[a-z]{2}\.)?linkedin\.com/jobs/view/\d+/?$")
URL_PESSOA = re.compile(r"^https://(www\.)?linkedin\.com/in/[^/?#]+/?$")
DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def checar_vagas(vagas: dict) -> list[tuple[str, str]]:
    achados = []
    erro = lambda m: achados.append(("erro", m))  # noqa: E731
    aviso = lambda m: achados.append(("aviso", m))  # noqa: E731

    lista, pessoas = vagas.get("vagas", []), vagas.get("pessoas", [])
    ids = [x.get("id") for x in lista + pessoas]
    for i in {i for i in ids if ids.count(i) > 1}:
        erro(f"id duplicado: {i}")
    pares = {}
    for v in lista:
        id_ = v.get("id", "?")
        if not re.fullmatch(r"vaga-\d+", str(v.get("id", ""))):
            erro(f"{id_}: id fora do formato vaga-N")
        if v.get("status") not in STATUS_VAGA:
            erro(f"{id_}: status '{v.get('status')}' desconhecido")
        if v.get("profundidade") not in PROFUNDIDADE:
            aviso(f"{id_}: profundidade deveria ser triagem ou completa")
        if not v.get("empresa") or not v.get("cargo"):
            erro(f"{id_}: sem empresa ou cargo")
        fit = v.get("fit")
        if not isinstance(fit, (int, float)) or not 0 <= fit <= 100:
            aviso(f"{id_}: fit deveria ser um número de 0 a 100")
        url = v.get("url") or ""
        if url and "linkedin.com" in url and not URL_VAGA_LINKEDIN.match(url):
            aviso(f"{id_}: link do LinkedIn não é permalink /jobs/view/{{id}} ({url})")
        if not v.get("adicionada_em") or not DATA.match(str(v.get("adicionada_em"))):
            aviso(f"{id_}: sem adicionada_em (AAAA-MM-DD)")
        if v.get("status") == "aprovado" and not v.get("aprovado_em"):
            aviso(f"{id_}: aprovada sem aprovado_em (o painel não consegue alertar se ficar parada)")
        for campo in ("cv", "cv_preview"):
            caminho = v.get(campo)
            if caminho:
                if not str(caminho).startswith("/cvs/"):
                    aviso(f"{id_}: {campo} deveria começar com /cvs/")
                elif not (caminhos.cvs() / caminho[len("/cvs/"):]).exists():
                    aviso(f"{id_}: {campo} aponta para arquivo que não existe ({caminho})")
        if v.get("salario") and not v.get("salario_fonte"):
            aviso(f"{id_}: salário sem fonte (publicada na vaga ou estimativa com fonte)")
        k = chave(v.get("empresa", ""), v.get("cargo", ""))
        if k in pares and v.get("status") in PENDENTES and pares[k] in PENDENTES:
            erro(f"{id_}: mesma empresa e cargo de outra vaga pendente (duplicata)")
        pares[k] = v.get("status")

    ids_vaga = {v.get("id") for v in lista}
    for p in pessoas:
        id_ = p.get("id", "?")
        if not re.fullmatch(r"pessoa-\d+", str(p.get("id", ""))):
            erro(f"{id_}: id fora do formato pessoa-N")
        if p.get("vaga_id") not in ids_vaga:
            erro(f"{id_}: vaga_id {p.get('vaga_id')} não existe")
        if p.get("status") not in STATUS_PESSOA:
            erro(f"{id_}: status '{p.get('status')}' desconhecido")
        if p.get("url") and not URL_PESSOA.match(p["url"]):
            aviso(f"{id_}: link de pessoa deveria ser linkedin.com/in/... ({p['url']})")
    return achados


def checar_registro(registro: dict) -> list[tuple[str, str]]:
    achados = []
    for dia in registro.get("dias", []):
        if not DATA.match(str(dia.get("data", ""))):
            achados.append(("erro", f"dia sem data AAAA-MM-DD: {dia.get('data')}"))
        for v in dia.get("vagas", []):
            if v.get("status") not in STATUS_REGISTRO:
                achados.append(("erro", f"{dia.get('data')} {v.get('empresa')}: status '{v.get('status')}' fora do vocabulário"))
            if v.get("status") in APLICADAS and not v.get("data_candidatura"):
                achados.append(("aviso", f"{dia.get('data')} {v.get('empresa')}: aplicada sem data_candidatura"))
        for p in dia.get("pessoas", []):
            if p.get("status") not in STATUS_PESSOA_REGISTRO:
                achados.append(("aviso", f"{dia.get('data')} {p.get('nome')}: status de pessoa '{p.get('status')}'"))
    return achados


def checar_consistencia(vagas: dict, registro: dict) -> list[tuple[str, str]]:
    """A falha mais cara do Radar: vaga já aplicada que continua na mesa com botão de aplicar."""
    aplicadas = {}
    for dia in registro.get("dias", []):
        for v in dia.get("vagas", []):
            if v.get("status") in APLICADAS:
                aplicadas[chave(v.get("empresa", ""), v.get("cargo", ""))] = v.get("data_candidatura") or dia.get("data")
    achados = []
    for v in vagas.get("vagas", []):
        k = chave(v.get("empresa", ""), v.get("cargo", ""))
        if k in aplicadas and v.get("status") in PENDENTES:
            achados.append(("erro", f"{v.get('id')} ({v.get('empresa')}): aplicada em {aplicadas[k]} no registro, "
                                    f"mas segue '{v.get('status')}' no Radar. Rode: bin/radar marcar {v.get('id')} executado"))
    return achados


def checar_tudo() -> list[tuple[str, str]]:
    vagas = ler_json(caminhos.vagas(), {"vagas": [], "pessoas": []}) or {}
    registro = ler_json(caminhos.registro(), {"dias": []}) or {}
    achados = checar_vagas(vagas) + checar_registro(registro) + checar_consistencia(vagas, registro)
    hoje = date.today().isoformat()
    if vagas.get("data") and vagas["data"] > hoje:
        achados.append(("aviso", f"vagas.json com data no futuro ({vagas['data']})"))
    return achados


def main() -> int:
    achados = checar_tudo()
    for nivel, msg in sorted(achados, key=lambda x: x[0] != "erro"):
        print(f"{'ERRO ' if nivel == 'erro' else 'aviso'}  {msg}")
    erros = sum(1 for n, _ in achados if n == "erro")
    print(f"{erros} erro(s), {len(achados) - erros} aviso(s)" if achados else "Tudo certo.")
    return 1 if erros else 0
