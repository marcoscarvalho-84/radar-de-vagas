"""Varredura de vagas: o LinkedIn pelo endpoint público (sem login) e, nas buscas no Brasil,
os portais da Gupy e da Sólides (radar/fontes.py, docs/fontes-de-vagas.md).

    bin/radar varrer coleta  [--horas 48] [--fontes linkedin,gupy,solides] [--saida arquivo.json]
    bin/radar varrer filtra  [--entrada coleta.json] [--saida candidatas.json]
    bin/radar varrer descricao <id ou link> [...]
    bin/radar varrer checa   <id ou link> [...]

Os ids: o do LinkedIn é o número da vaga; os outros levam a fonte e a empresa no portal
(`gupy-asaas-12836874`, `solides-inchurch-940811`). Um link de vaga de qualquer ATS também
serve para descricao e checa: a página é lida pelo JSON-LD JobPosting.

Regras aprendidas na prática no LinkedIn (detalhes em docs/linkedin-tecnico.md):
- uma palavra-chave por vez: a busca do LinkedIn não respeita OR nem aspas;
- paginação de 10 em 10 pelo `start`, e a parada é POR PALAVRA-CHAVE (página sem id novo
  para ela), não pelo conjunto global, senão palavras sobrepostas morrem na 2ª página;
- 429 é frequente: espera crescente a partir de 30s e ritmo de 3 a 6s entre chamadas;
- filtro de título por palavra inteira (\\b), nunca por substring: "ux" casa com
  "auxiliar" e "ui" com "máquinas";
- no macOS, rode sob `caffeinate -i`: com o Mac em repouso cada palavra leva minutos.

Ritmo humano é regra: isto é uma pessoa procurando emprego, não um robô de dados.
"""

import html
import json
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from . import buscas as _buscas
from . import caminhos, config, fontes
from .arquivos import gravar_json, ler_json

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
BUSCA = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
POSTAGEM = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
PAGINAS_MAX = 30  # 300 vagas por palavra-chave é mais que suficiente
PAUSA = (3, 6)


def _pausa(intervalo=PAUSA):
    time.sleep(random.uniform(*intervalo))


def baixar(url: str, tentativas: int = 6, com_url: bool = False) -> tuple:
    """(código HTTP, corpo). Código 0 = desistiu depois de todas as tentativas.

    Com `com_url`, devolve também o endereço final, depois dos redirecionamentos: a Gupy
    manda a vaga que sumiu para a tela de login."""
    for t in range(tentativas):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                corpo = r.read().decode("utf-8", "replace")
                return (r.status, corpo, r.geturl()) if com_url else (r.status, corpo)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return (e.code, "", url) if com_url else (e.code, "")
            codigo = e.code
        except (urllib.error.URLError, TimeoutError) as e:
            codigo = f"rede ({e})"
        espera = 30 + 30 * t
        print(f"   {codigo}: nova tentativa em {espera}s", file=sys.stderr, flush=True)
        time.sleep(espera)
    return (0, "", url) if com_url else (0, "")


def _txt(padrao: str, corpo: str) -> str:
    m = re.search(padrao, corpo, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    s = s.replace(".", "")  # "S.A." e "SA" são a mesma coisa
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


SUFIXOS_EMPRESA = re.compile(r"( (sa|ltda|me|eireli|inc|llc|ltd|gmbh|corp|co))+$")


def chave(empresa: str, cargo: str) -> tuple[str, str]:
    """A mesma regra de duplicata do Radar inteiro: empresa + cargo, normalizados.

    Sufixo societário não diferencia empresa: "Acme S.A." e "Acme" são a mesma.
    """
    return SUFIXOS_EMPRESA.sub("", normalizar(empresa)), normalizar(cargo)


# ---------------------------------------------------------------- coleta

def escolher_fontes(pedidas=None) -> list[str]:
    """As fontes desta coleta: as pedidas na linha de comando ou as de config.rotina.fontes."""
    lista = pedidas if pedidas is not None else config.carregar()["rotina"].get("fontes")
    if isinstance(lista, str):
        lista = lista.split(",")
    escolhidas = [str(f).strip().lower() for f in lista or [] if str(f).strip()]
    desconhecidas = [f for f in escolhidas if f not in fontes.FONTES]
    if desconhecidas:
        raise SystemExit(f"Fonte desconhecida: {', '.join(desconhecidas)}. Use {', '.join(fontes.FONTES)}.")
    if not escolhidas:
        raise SystemExit("Nenhuma fonte de vaga ligada: confira config.json > rotina > fontes.")
    return escolhidas


def coleta(horas: int, saida: Path, quais=None) -> dict:
    buscas = _buscas.ler()
    onde = "diga as posições que você quer no passo Posições (bin/radar, Seu contexto) ou rode /radar-configurar busca"
    if _buscas.e_exemplo(buscas):
        raise SystemExit(f"{caminhos.buscas()} ainda tem as palavras-chave do exemplo, que não são as suas: {onde}")
    if not _buscas.palavras(buscas):
        raise SystemExit(f"Sem palavras-chave em {caminhos.buscas()}: {onde}")
    ligadas = escolher_fontes(quais)
    aviso = lambda s: print(s, file=sys.stderr, flush=True)
    # os portais de ATS primeiro: a mesma vaga no LinkedIn fica como repetida, e a que segue
    # é a que já tem o link de candidatura direto
    vagas, falhas = fontes.coletar(buscas["grupos"], horas, ligadas, baixar, lambda: _pausa((2, 4)), aviso)
    if vagas and "linkedin" in ligadas:
        _pausa()
    if "linkedin" in ligadas:
        _linkedin(buscas, horas, vagas, falhas)
    contagem = {}
    for v in vagas.values():
        contagem[v.get("fonte", "linkedin")] = contagem.get(v.get("fonte", "linkedin"), 0) + 1
    resultado = {"horas": horas, "em": date.today().isoformat(), "fontes": contagem,
                 "vagas": list(vagas.values()), "falhas": falhas}
    gravar_json(saida, resultado)
    por_fonte = ", ".join(f"{fontes.NOMES[f]} {n}" for f, n in contagem.items())
    print(f"{len(vagas)} vagas únicas -> {saida}" + (f" ({por_fonte})" if por_fonte else "")
          + (f" ({len(falhas)} buscas incompletas)" if falhas else ""))
    return resultado


def _linkedin(buscas: dict, horas: int, vagas: dict, falhas: list) -> None:
    tpr = f"r{int(horas) * 3600}"
    feitas = 0
    for grupo in buscas["grupos"]:
        local = grupo.get("local", "")
        for kw in grupo.get("palavras_chave") or []:
            if feitas:
                _pausa((6, 10))  # entre palavras-chave também: o 429 vem rápido
            feitas += 1
            vistos_kw, start = set(), 0
            for _ in range(PAGINAS_MAX):
                # sem local, a busca não leva o parâmetro (o LinkedIn usa o mundo todo)
                q = urllib.parse.urlencode({"keywords": kw, **({"location": local} if local else {}),
                                            "f_TPR": tpr, "start": start})
                codigo, corpo = baixar(BUSCA + q)
                if codigo == 0:
                    falhas.append({"fonte": "linkedin", "local": local, "palavra_chave": kw, "start": start})
                    print(f"ATENÇÃO: {local} / {kw} parou no start={start} por bloqueio; resultado incompleto",
                          file=sys.stderr, flush=True)
                    break
                novos = 0
                for card in corpo.split("<li>")[1:]:
                    m = re.search(r"urn:li:jobPosting:(\d+)", card)
                    if not m or m.group(1) in vistos_kw:
                        continue
                    id_ = m.group(1)
                    vistos_kw.add(id_)
                    novos += 1
                    data = re.search(r'datetime="([^"]+)"', card)
                    vagas.setdefault(id_, {
                        "id": id_,
                        "fonte": "linkedin",
                        "titulo": _txt(r"base-search-card__title[^>]*>(.*?)</h3>", card),
                        "empresa": _txt(r"base-search-card__subtitle[^>]*>(.*?)</h4>", card),
                        "local": _txt(r"job-search-card__location[^>]*>(.*?)</span>", card),
                        "data": data.group(1) if data else "",
                        "url": f"https://www.linkedin.com/jobs/view/{id_}",
                        "palavra_chave": kw,
                        "busca_local": local,
                    })
                if novos == 0:
                    break
                start += 10
                _pausa((3, 5))
            print(f"LinkedIn · {local} · {kw}: {len(vistos_kw)}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- filtra

def _ja_no_radar() -> tuple[set, set]:
    """Ids de vaga (de qualquer fonte) e pares empresa+cargo já vistos: Radar atual,
    histórico e arquivo."""
    ids, pares = set(), set()

    def anotar(v):
        for campo in ("url", "url_candidatura"):
            id_ = fontes.id_da_url(v.get(campo))
            if id_:
                ids.add(id_)
        if v.get("empresa") and v.get("cargo"):
            pares.add(chave(v["empresa"], v["cargo"]))

    pastas = [caminhos.dados()] + sorted(p for p in caminhos.arquivo().glob("*") if p.is_dir())
    for pasta in pastas:
        for v in (ler_json(pasta / "vagas.json", {}) or {}).get("vagas", []):
            anotar(v)
        for dia in (ler_json(pasta / "registro.json", {}) or {}).get("dias", []):
            for v in dia.get("vagas", []):
                anotar(v)
    return ids, pares


def _regex(palavras) -> re.Pattern | None:
    termos = [re.escape(normalizar(p)) for p in palavras or [] if normalizar(p)]
    return re.compile(r"\b(" + "|".join(termos) + r")\b") if termos else None


def filtra(entrada: Path, saida: Path) -> list:
    coletadas = (ler_json(entrada, {}) or {}).get("vagas", [])
    regras = (ler_json(caminhos.buscas(), {}) or {}).get("filtro_titulo", {})
    precisa, senior, fora = (_regex(regras.get(k)) for k in ("precisa_ter", "senioridade", "descartar_se_tiver"))
    horas = (ler_json(caminhos.buscas(), {}) or {}).get("janela_horas") or config.carregar()["rotina"]["janela_horas"]
    corte_data = (date.today() - timedelta(hours=int(horas))).isoformat()
    ids, pares = _ja_no_radar()

    motivos, candidatas, vistas = {}, [], set()

    def cortar(motivo):
        motivos[motivo] = motivos.get(motivo, 0) + 1

    for v in coletadas:
        titulo = normalizar(v.get("titulo"))
        if precisa and not precisa.search(titulo):
            cortar("título fora da área")
        elif fora and fora.search(titulo):
            cortar("título descartado (júnior, outra função)")
        elif senior and not senior.search(titulo):
            cortar("sem senioridade no título")
        elif v.get("data") and v["data"] < corte_data:
            cortar("fora da janela de horas")
        elif v["id"] in ids or chave(v.get("empresa"), v.get("titulo")) in pares:
            cortar("já está no Radar ou no arquivo")
        elif chave(v.get("empresa"), v.get("titulo")) in vistas:
            cortar("repetida na coleta (mesma vaga em outra cidade)")
        else:
            vistas.add(chave(v.get("empresa"), v.get("titulo")))
            candidatas.append(v)

    candidatas.sort(key=lambda x: x.get("data", ""), reverse=True)
    rendimento = por_palavra(coletadas, candidatas)
    gravar_json(saida, {"entrada": str(entrada), "candidatas": candidatas, "cortes": motivos,
                        "por_palavra": rendimento})
    print(f"{len(coletadas)} coletadas, {len(candidatas)} candidatas -> {saida}")
    for m, n in sorted(motivos.items(), key=lambda x: -x[1]):
        print(f"  {n:4} {m}")
    if len(rendimento) > 1:
        print("  por palavra-chave (coletadas -> candidatas):")
        for kw, r in rendimento.items():
            print(f"  {r['coletadas']:4} -> {r['candidatas']:<3} {kw}")
    return candidatas


def por_palavra(coletadas: list, candidatas: list) -> dict:
    """Quanto cada palavra-chave trouxe e quanto passou no filtro, com os títulos que passaram.

    É aqui que aparece o termo que pega outra área: "Revenue" traz revenue management de
    hotel, uma sigla curta casa com o nome de uma empresa. Os títulos de exemplo deixam o
    padrão visível sem abrir vaga por vaga.
    """
    saida = {}
    for v in coletadas:
        r = saida.setdefault(v.get("palavra_chave", ""), {"coletadas": 0, "candidatas": 0, "titulos": []})
        r["coletadas"] += 1
    for v in candidatas:
        r = saida.setdefault(v.get("palavra_chave", ""), {"coletadas": 0, "candidatas": 0, "titulos": []})
        r["candidatas"] += 1
        if len(r["titulos"]) < 8 and v.get("titulo") and v["titulo"] not in r["titulos"]:
            r["titulos"].append(v["titulo"])
    return dict(sorted(saida.items(), key=lambda x: -x[1]["coletadas"]))


# ---------------------------------------------------------------- descrição e checagem

# Sem login, o LinkedIn não mostra o link externo de candidatura, mas diz se ela é no site
# da empresa (botão "offsite") ou no próprio LinkedIn (Easy Apply, "onsite").
CANDIDATURA = {"externa": "no site da empresa (bin/radar ats acha o link)", "linkedin": "Easy Apply no LinkedIn"}


def _fechada(codigo, corpo: str) -> bool:
    return codigo in (404, 410) or "No longer accepting applications" in corpo


def _candidatura(corpo: str) -> str:
    """'externa', 'linkedin' ou '' (a página não disse)."""
    if "apply-link-offsite" in corpo:
        return "externa"
    if "apply-link-onsite" in corpo:
        return "linkedin"
    return ""


def _alvo(item: str) -> tuple[str, str]:
    """(id, link) de um argumento que pode ser o id do Radar ou o link da vaga."""
    item = str(item).strip()
    if item.startswith("http"):
        id_ = fontes.id_da_url(item)
        return id_ or re.sub(r"[^a-z0-9]+", "-", item.split("//", 1)[-1].lower()).strip("-")[:80], item
    url = fontes.url_do_id(item)
    if not url:
        raise SystemExit(f"'{item}' não é id de vaga do Radar nem link: use o número do LinkedIn, "
                         "o id da coleta (gupy-…, solides-…) ou o endereço da vaga")
    return item, url


def _descricao_ats(id_: str, url: str, pasta: Path) -> None:
    r = fontes.ler_vaga(url, baixar)
    fechada = "FECHADA" if r["fechada"] else ""
    criterios = " | ".join(x for x in (r["tipo"], r["local"], r["valida_ate"] and f"inscrições até {r['valida_ate']}") if x)
    onde = f"no site da empresa, pelo próprio link da vaga: {url}"
    (pasta / f"{id_}.txt").write_text(f"{r['codigo']} {fechada}\nCANDIDATURA: {onde}\nCRITÉRIOS: {criterios}\n"
                                      f"{r['descricao']}", encoding="utf-8")
    estado = "FECHADA" if r["fechada"] else ("aberta" if r["fechada"] is False else "sem dado de vaga na página")
    print(id_, r["codigo"], estado, f"{len(r['descricao'])} caracteres", flush=True)


def descricao(ids, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for item in ids:
        i, url = _alvo(item)
        if fontes.fonte_do_id(i) != "linkedin":
            _descricao_ats(i, url, pasta)
            _pausa()
            continue
        codigo, corpo = baixar(POSTAGEM.format(i))
        criterios = " | ".join(_txt(r"(.*)", x) for x in
                               re.findall(r"description__job-criteria-text[^>]*>(.*?)</span>", corpo, re.S))
        fechada = "FECHADA" if _fechada(codigo, corpo) else ""
        onde = CANDIDATURA.get(_candidatura(corpo), "")
        m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", corpo, re.S)
        texto = html.unescape(re.sub(r"<br\s*/?>|</li>|</p>", "\n", m.group(1) if m else ""))
        texto = re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "", texto)).strip()
        (pasta / f"{i}.txt").write_text(f"{codigo} {fechada}\nCANDIDATURA: {onde}\nCRITÉRIOS: {criterios}\n{texto}",
                                        encoding="utf-8")
        print(i, codigo, fechada or "aberta", f"{len(texto)} caracteres", onde, flush=True)
        _pausa()


def checa(ids, saida: Path) -> dict:
    """Aberta ou fechada, retomável: o que já está no arquivo de saída não é baixado de novo."""
    resultado = ler_json(saida, {}) or {}
    for item in ids:
        i, url = _alvo(item)
        if i in resultado:
            continue
        if fontes.fonte_do_id(i) != "linkedin":
            r = fontes.ler_vaga(url, baixar)
            resultado[i] = {k: r[k] for k in ("codigo", "fechada", "ha", "valida_ate", "titulo", "empresa", "candidatura")}
            resultado[i]["url"] = url
            gravar_json(saida, resultado)
            print(i, resultado[i], flush=True)
            _pausa((4, 7))
            continue
        codigo, corpo = baixar(POSTAGEM.format(i))
        resultado[i] = {
            "codigo": codigo,
            "fechada": _fechada(codigo, corpo) if codigo else None,
            "ha": _txt(r"posted-time-ago__text[^>]*>(.*?)<", corpo),
            "titulo": _txt(r"topcard__title[^>]*>(.*?)<", corpo),
            "empresa": _txt(r"topcard__org-name-link[^>]*>(.*?)<", corpo),
            "candidatura": _candidatura(corpo),
        }
        gravar_json(saida, resultado)
        print(i, resultado[i], flush=True)
        _pausa((4, 7))
    return resultado


def pasta_do_dia() -> Path:
    return caminhos.varredura() / date.today().isoformat()
