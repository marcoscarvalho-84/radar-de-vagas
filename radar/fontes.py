"""Fontes de vaga além do LinkedIn: os portais da Gupy e da Sólides.

Os dois são portais de ATS brasileiros cuja página de busca chama um JSON aberto, sem
login. O Radar faz a mesma chamada que a página. Não é API documentada: o formato pode
mudar sem aviso (os testes cobrem o que os portais devolviam em novembro de 2026), e quem
mantém o projeto confere de tempos em tempos. Detalhes em docs/fontes-de-vagas.md.

Regras:
- só entram buscas no Brasil, porque os dois portais só têm vaga brasileira. Busca por
  cidade ("Curitiba, Paraná, Brazil") fica com as vagas da cidade e as remotas;
- uma palavra-chave por vez e pausa entre chamadas, como no LinkedIn;
- os dois devolvem do mais novo para o mais velho: a página que passa da janela de horas
  encerra a palavra-chave;
- a vaga já vem com o link do ATS, que serve de `url` e de `url_candidatura`;
- os termos da Gupy para candidatos proíbem "agregar" vagas da plataforma. O Radar lê para
  uma pessoa decidir onde se candidatar e não republica nada; quem não quiser desliga a
  fonte em `config.json > rotina > fontes`.

O id da vaga carrega a fonte e o endereço da empresa no portal, para descrição e checagem
montarem o link sem consultar nada: `gupy-asaas-12836874`, `solides-inchurch-940811`. O
id do LinkedIn continua só o número.

Também mora aqui o leitor de `JobPosting` (JSON-LD), o dado estruturado que quase todo site
de vaga põe na página para o Google. É ele que diz se a vaga de um ATS ainda está aberta.
"""

import html
import json
import re
import unicodedata
import urllib.parse
from datetime import date, timedelta

FONTES = ("linkedin", "gupy", "solides")
NOMES = {"linkedin": "LinkedIn", "gupy": "Gupy", "solides": "Sólides"}

GUPY_BUSCA = "https://portal.gupy.io/api/job-search/jobs?"
SOLIDES_BUSCA = "https://vagas.solides.com.br/api/vacancies?"
GUPY_POR_PAGINA = 50     # o portal aceita 50; mais que isso não foi testado
SOLIDES_POR_PAGINA = 20  # com 50 o portal responde erro 500
PAGINAS_MAX = 10

MODELO = {"remote": "remoto", "hybrid": "híbrido", "on-site": "presencial",
          "remoto": "remoto", "hibrido": "híbrido", "presencial": "presencial"}
# "banco de talentos" na Gupy não é vaga: é cadastro para uma vaga futura
GUPY_NAO_E_VAGA = ("talent_pool",)
SUBDOMINIO = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _norm(texto) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "").casefold()).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def no_brasil(local: str) -> bool:
    """'Brazil', 'Brasil' ou 'Cidade, Estado, Brazil'. Região ('Latin America') e vazio, não."""
    return any(_norm(p) in ("brazil", "brasil") for p in str(local or "").split(","))


def para_locais(locais, ligadas) -> list[str]:
    """As fontes que a coleta lê para estes locais, na ordem de FONTES: o LinkedIn em
    qualquer local, a Gupy e a Sólides só quando algum local é no Brasil."""
    brasil = any(no_brasil(l) for l in locais or [])
    ligadas = {str(f).strip().lower() for f in (ligadas.split(",") if isinstance(ligadas, str) else ligadas or [])}
    return [f for f in FONTES if f in ligadas and (f == "linkedin" or brasil)]


def cidade_da_busca(local: str) -> str:
    """A cidade de uma busca por cidade, normalizada; '' quando a busca é o país inteiro."""
    partes = [p.strip() for p in str(local or "").split(",") if p.strip()]
    return _norm(partes[0]) if len(partes) > 1 else ""


def _na_cidade(vaga: dict, cidade: str) -> bool:
    return not cidade or vaga.get("modelo") == "remoto" or _norm(vaga.get("local")).startswith(cidade)


# ---------------------------------------------------------------- ids e links

def url_do_id(id_: str) -> str:
    """O link da vaga a partir do id do Radar ('' quando o id não é de nenhuma fonte)."""
    id_ = str(id_ or "").strip()
    if re.fullmatch(r"\d+", id_):
        return f"https://www.linkedin.com/jobs/view/{id_}"
    m = re.fullmatch(r"gupy-([a-z0-9-]+)-(\d+)", id_)
    if m:
        return f"https://{m.group(1)}.gupy.io/jobs/{m.group(2)}"
    m = re.fullmatch(r"solides-([a-z0-9-]+)-(\d+)", id_)
    if m:
        return f"https://{m.group(1)}.vagas.solides.com.br/vaga/{m.group(2)}"
    return ""


def id_da_url(url: str) -> str:
    """O inverso: o id do Radar a partir do link ('' quando o link não é de nenhuma fonte)."""
    url = str(url or "")
    m = re.search(r"linkedin\.com/jobs/view/(\d+)", url)
    if m:
        return m.group(1)
    m = re.match(r"https?://([a-z0-9-]+)\.gupy\.io/jobs?/(\d+)", url)
    if m:
        return f"gupy-{m.group(1)}-{m.group(2)}"
    m = re.match(r"https?://([a-z0-9-]+)\.vagas\.solides\.com\.br/vaga/(\d+)", url)
    if m:
        return f"solides-{m.group(1)}-{m.group(2)}"
    return ""


def fonte_do_id(id_: str) -> str:
    id_ = str(id_ or "")
    if re.fullmatch(r"\d+", id_):
        return "linkedin"
    return next((f for f in ("gupy", "solides") if id_.startswith(f + "-")), "")


# ---------------------------------------------------------------- cada portal

def _subdominio(url: str, dominio: str) -> str:
    m = re.match(rf"https?://([a-z0-9-]+)\.{re.escape(dominio)}(?:/|$)", str(url or "").lower())
    return m.group(1) if m and SUBDOMINIO.match(m.group(1)) else ""


def vaga_gupy(j: dict, palavra_chave: str, local: str) -> dict | None:
    sub = _subdominio(j.get("jobUrl"), "gupy.io")
    if not str(j.get("id") or "").isdigit() or not sub:
        return None
    if any(t in str(j.get("type") or "") for t in GUPY_NAO_E_VAGA):
        return None
    modelo = MODELO.get(str(j.get("workplaceType") or ""), "")
    lugar = ", ".join(x for x in (j.get("city"), j.get("state")) if x)
    return {
        "id": f"gupy-{sub}-{j['id']}",
        "fonte": "gupy",
        "titulo": str(j.get("name") or "").strip(),
        "empresa": str(j.get("careerPageName") or "").strip(),
        "local": lugar or ("Remoto" if modelo == "remoto" else "Brasil"),
        "modelo": modelo,
        "data": str(j.get("publishedDate") or "")[:10],
        "prazo": str(j.get("applicationDeadline") or "")[:10],
        "url": f"https://{sub}.gupy.io/jobs/{j['id']}",
        "palavra_chave": palavra_chave,
        "busca_local": local,
    }


def _reais(valor) -> str:
    try:
        return "R$ " + f"{float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return ""


def vaga_solides(v: dict, palavra_chave: str, local: str) -> dict | None:
    slug = str(v.get("slug") or "").strip().lower()
    if not str(v.get("id") or "").isdigit() or not SUBDOMINIO.match(slug):
        return None
    if v.get("isDisabled") is True or v.get("receivingResume") is False:
        return None
    cidade = (v.get("city") or {}).get("name") or ""
    uf = (v.get("state") or {}).get("code") or ""
    modelo = MODELO.get(_norm(v.get("jobType")), "")
    vaga = {
        "id": f"solides-{slug}-{v['id']}",
        "fonte": "solides",
        "titulo": str(v.get("title") or "").strip(),
        "empresa": str(v.get("companyName") or "").strip(),
        "local": ", ".join(x for x in (cidade, uf) if x) or ("Remoto" if modelo == "remoto" else "Brasil"),
        "modelo": modelo,
        "data": str(v.get("createdAt") or "")[:10],
        "url": f"https://{slug}.vagas.solides.com.br/vaga/{v['id']}",
        "palavra_chave": palavra_chave,
        "busca_local": local,
    }
    # faixa só quando a empresa escolheu mostrar para quem se candidata
    salario = v.get("salary") or {}
    faixa = [_reais(salario.get(k)) for k in ("initialRange", "finalRange") if salario.get(k)]
    if salario.get("showRangeToApplicant") and any(faixa):
        vaga["salario"] = " a ".join(f for f in faixa if f)
        vaga["salario_fonte"] = "publicada na vaga"
    return vaga


def _json(baixar, url):
    codigo, corpo = baixar(url)
    if codigo != 200:
        return None
    try:
        return json.loads(corpo)
    except ValueError:
        return None


def _paginas(baixar, pausa, montar_url, ler_itens, data_do_item, corte):
    """Itens de todas as páginas até a janela acabar. (itens, completo)"""
    itens = []
    for pagina in range(PAGINAS_MAX):
        if pagina:
            pausa()
        dados = _json(baixar, montar_url(pagina))
        if dados is None:
            return itens, False
        lote, por_pagina = ler_itens(dados)
        itens.extend(lote)
        datas = [data_do_item(x) for x in lote if data_do_item(x)]
        if len(lote) < por_pagina or (datas and min(datas) < corte):
            break
    return itens, True


def coletar_gupy(palavra_chave, local, corte, baixar, pausa):
    def url(pagina):
        return GUPY_BUSCA + urllib.parse.urlencode(
            {"jobName": palavra_chave, "limit": GUPY_POR_PAGINA, "offset": pagina * GUPY_POR_PAGINA})
    itens, completo = _paginas(baixar, pausa, url, lambda d: (d.get("data") or [], GUPY_POR_PAGINA),
                               lambda j: str(j.get("publishedDate") or "")[:10], corte)
    return [v for v in (vaga_gupy(j, palavra_chave, local) for j in itens) if v], completo


def coletar_solides(palavra_chave, local, corte, baixar, pausa):
    def url(pagina):
        return SOLIDES_BUSCA + urllib.parse.urlencode(
            {"page": pagina + 1, "take": SOLIDES_POR_PAGINA, "title": palavra_chave})
    itens, completo = _paginas(baixar, pausa, url, lambda d: (d.get("data") or [], SOLIDES_POR_PAGINA),
                               lambda v: str(v.get("createdAt") or "")[:10], corte)
    return [v for v in (vaga_solides(x, palavra_chave, local) for x in itens) if v], completo


COLETORES = {"gupy": coletar_gupy, "solides": coletar_solides}


def coletar(grupos, horas, fontes, baixar, pausa, avisar=lambda s: None):
    """Gupy e Sólides para cada palavra-chave das buscas no Brasil. (vagas por id, falhas)

    A mesma palavra-chave na mesma cidade roda uma vez por fonte, mesmo que apareça em dois
    grupos. As vagas fora da janela ainda vêm (a última página passa dela); quem corta é o
    `varrer filtra`, igual ao LinkedIn.
    """
    corte = (date.today() - timedelta(hours=int(horas))).isoformat()
    vagas, falhas, feitas = {}, [], set()
    for grupo in grupos or []:
        local = str(grupo.get("local") or "")
        if not no_brasil(local):
            continue
        cidade = cidade_da_busca(local)
        for kw in grupo.get("palavras_chave") or []:
            for fonte in ("gupy", "solides"):
                marca = (fonte, _norm(kw), cidade)
                if fonte not in fontes or marca in feitas:
                    continue
                if feitas:
                    pausa()
                feitas.add(marca)
                achadas, completo = COLETORES[fonte](kw, local, corte, baixar, pausa)
                achadas = [v for v in achadas if _na_cidade(v, cidade)]
                for v in achadas:
                    vagas.setdefault(v["id"], v)
                if not completo:
                    falhas.append({"fonte": fonte, "local": local, "palavra_chave": kw})
                    avisar(f"ATENÇÃO: {NOMES[fonte]} · {local} / {kw} não respondeu; resultado incompleto")
                avisar(f"{NOMES[fonte]} · {local} · {kw}: {len(achadas)}")
    return vagas, falhas


# ---------------------------------------------------------------- a página de uma vaga

def _itens_ld(dados):
    if isinstance(dados, list):
        for x in dados:
            yield from _itens_ld(x)
    elif isinstance(dados, dict):
        if "@graph" in dados:
            yield from _itens_ld(dados["@graph"])
        else:
            yield dados


def jobposting(corpo: str) -> dict | None:
    """O primeiro JSON-LD do tipo JobPosting da página. Aceita o JSON com as entidades HTML
    escapadas (a Gupy serve assim) e o formato com @graph."""
    for bloco in re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", corpo or "", re.S | re.I):
        dados = None
        for texto in (bloco.strip(), html.unescape(bloco.strip())):
            try:
                dados = json.loads(texto)
                break
            except ValueError:
                continue
        for item in _itens_ld(dados):
            tipo = item.get("@type")
            if "JobPosting" in (tipo if isinstance(tipo, list) else [tipo]):
                return item
    return None


def texto_de_html(trecho: str) -> str:
    t = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", str(trecho or ""), flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def _nome(x) -> str:
    return str(x.get("name") or "") if isinstance(x, dict) else str(x or "")


def _local_ld(jp: dict) -> str:
    lugares = jp.get("jobLocation")
    lugares = lugares if isinstance(lugares, list) else [lugares]
    for lugar in lugares:
        endereco = (lugar or {}).get("address") if isinstance(lugar, dict) else None
        if isinstance(endereco, dict):
            partes = [endereco.get(k) for k in ("addressLocality", "addressRegion")]
            texto = ", ".join(str(p) for p in partes if p)
            if texto:
                return texto
    return "Remoto" if str(jp.get("jobLocationType") or "").upper() == "TELECOMMUTE" else ""


def ler_vaga(url: str, baixar) -> dict:
    """Aberta ou fechada, pela página da vaga num ATS (ou em qualquer site com JobPosting).

    Fechada: 404/410, a página mandou para outro endereço (a Gupy manda para o login quando
    a vaga some) ou `validThrough` já passou. Página no ar sem JobPosting: não dá para dizer
    (`fechada: None`), abra e confira.
    """
    codigo, corpo, final = baixar(url, com_url=True)
    jp = jobposting(corpo) if codigo == 200 else None
    validade = str((jp or {}).get("validThrough") or "")[:10]
    caminho = lambda u: urllib.parse.urlparse(u or "").path.rstrip("/")
    saiu = bool(final) and caminho(final) != caminho(url)
    if codigo == 0:
        fechada = None
    elif codigo in (404, 410) or saiu or (validade and validade < date.today().isoformat()):
        fechada = True
    else:
        fechada = False if jp else None
    jp = jp or {}
    return {
        "codigo": codigo,
        "fechada": fechada,
        "ha": str(jp.get("datePosted") or "")[:10],
        "valida_ate": validade,
        "titulo": str(jp.get("title") or "").strip(),
        "empresa": _nome(jp.get("hiringOrganization")).strip(),
        "local": _local_ld(jp),
        "tipo": ", ".join(jp["employmentType"]) if isinstance(jp.get("employmentType"), list) else str(jp.get("employmentType") or ""),
        "candidatura": "externa",
        "descricao": texto_de_html(jp.get("description")),
    }
