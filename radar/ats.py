"""Acha a vaga direto no ATS da empresa: Greenhouse, Lever e Ashby, pelas APIs públicas.

    bin/radar ats "<empresa>" "<cargo>" [--slug identificador]

Sem login, o anúncio do LinkedIn não mostra o link externo de candidatura (ele só diz que a
candidatura é "no site da empresa"). Greenhouse, Lever e Ashby publicam o quadro de vagas de
cada empresa em JSON aberto, feito exatamente para isso. O comando tenta os identificadores
prováveis da empresa (figma, acme-corp, acmecorp, acme), lê o quadro que existir e devolve
as vagas com título parecido, com o link para se candidatar.

Não achou: a empresa usa outro ATS (Gupy, InHire, Workday...) ou outro identificador. Passe
`--slug` se souber (é o pedaço da URL do quadro: boards.greenhouse.io/<slug>) ou procure a
página de carreiras com WebSearch.

Quadro encontrado sem a vaga também é informação: a vaga pode ter fechado no site da empresa
e continuar aberta no LinkedIn.

O último palpite é a primeira palavra do nome ("acme"), que pode ser o quadro de outra
empresa com o mesmo começo: confira o nome no link antes de usar.
"""

import json
import re
import sys
import urllib.error
import urllib.request

from .varredura import UA, normalizar

QUADROS = {
    "Greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "Lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "Ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
}
PARECIDA = 0.6  # fração das palavras do cargo procurado que aparecem no título do quadro
MIUDAS = {"de", "da", "do", "das", "dos", "e", "em", "of", "the", "and", "for", "to", "a", "o", "at"}


def _baixar_json(url: str):
    """O JSON do quadro, ou None quando a empresa não tem quadro com esse identificador."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _vagas(ats: str, dados) -> list[dict]:
    """Título, link e local de cada vaga aberta, no formato de cada ATS."""
    if ats == "Greenhouse" and isinstance(dados, dict):
        return [{"titulo": j.get("title", ""), "url": j.get("absolute_url", ""),
                 "local": (j.get("location") or {}).get("name", "")} for j in dados.get("jobs") or []]
    if ats == "Lever" and isinstance(dados, list):
        return [{"titulo": j.get("text", ""), "url": j.get("hostedUrl", ""),
                 "local": (j.get("categories") or {}).get("location", "")} for j in dados]
    if ats == "Ashby" and isinstance(dados, dict):
        return [{"titulo": j.get("title", ""), "url": j.get("jobUrl", ""),
                 "local": j.get("location", "")} for j in dados.get("jobs") or []]
    return []


# só a forma societária sai do nome: "Corp" e "Co" costumam fazer parte do identificador
# do quadro (acmecorp), ao contrário da regra de duplicata, que os ignora
FORMA_SOCIETARIA = re.compile(r"( (sa|ltda|me|eireli|inc|llc|ltd|gmbh|plc|ag|bv))+$")


def identificadores(empresa: str) -> list[str]:
    """'Acme Corp S.A.' -> ['acmecorp', 'acme-corp', 'acme']: os formatos que os quadros usam."""
    palavras = FORMA_SOCIETARIA.sub("", normalizar(empresa)).split()
    if not palavras:
        return []
    saida = []
    for s in ("".join(palavras), "-".join(palavras), palavras[0]):
        if len(s) >= 2 and s not in saida:
            saida.append(s)
    return saida


def _palavras(texto: str) -> set[str]:
    return {p for p in normalizar(texto).split() if p not in MIUDAS}


def parecido(procurado: str, titulo: str) -> float:
    """Quanto do cargo procurado está no título: 1.0 quando todas as palavras aparecem."""
    alvo = _palavras(procurado)
    return len(alvo & _palavras(titulo)) / len(alvo) if alvo else 0.0


def procurar(empresa: str, cargo: str, slug: str = "", baixar=_baixar_json) -> dict:
    """{'quadros': [{ats, slug, abertas}], 'vagas': [{ats, titulo, url, local, nota}]}"""
    quadros, vagas = [], []
    for s in [slug] if slug else identificadores(empresa):
        for ats, modelo in QUADROS.items():
            dados = baixar(modelo.format(s))
            if dados is None:
                continue
            abertas = _vagas(ats, dados)
            quadros.append({"ats": ats, "slug": s, "abertas": len(abertas)})
            for v in abertas:
                nota = parecido(cargo, v["titulo"])
                if nota >= PARECIDA and v["url"]:
                    vagas.append({"ats": ats, **v, "nota": round(nota, 2)})
        if quadros:
            break  # achou o quadro da empresa: os outros identificadores seriam palpite
    vagas.sort(key=lambda v: (-v["nota"], len(v["titulo"])))
    return {"quadros": quadros, "vagas": vagas}


def main(empresa: str, cargo: str, slug: str = "") -> int:
    r = procurar(empresa, cargo, slug)
    if not r["quadros"]:
        tentados = ", ".join([slug] if slug else identificadores(empresa)) or "nenhum"
        print(f"Nenhum quadro de {empresa} no Greenhouse, Lever ou Ashby (identificadores tentados: {tentados}).")
        print("Procure a página de carreiras com WebSearch, ou passe --slug se souber o identificador.")
        return 1
    for q in r["quadros"]:
        print(f"{q['ats']} · {q['slug']}: {q['abertas']} vagas abertas")
    if not r["vagas"]:
        print(f"Nenhuma com título parecido com \"{cargo}\". A vaga pode ter fechado no site da empresa;"
              " confira a lista do quadro antes de aprofundar.")
        return 1
    for v in r["vagas"][:8]:
        local = f" · {v['local']}" if v["local"] else ""
        print(f"  {v['nota']:.2f}  {v['titulo']}{local}\n        {v['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
