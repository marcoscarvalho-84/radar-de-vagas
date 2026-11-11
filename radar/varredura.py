"""Varredura de vagas pelo endpoint público (sem login) do LinkedIn.

    bin/radar varrer coleta  [--horas 48] [--saida arquivo.json]
    bin/radar varrer filtra  [--entrada coleta.json] [--saida candidatas.json]
    bin/radar varrer descricao <id> [<id>...]
    bin/radar varrer checa   <id> [<id>...]

Regras aprendidas na prática (detalhes em docs/linkedin-tecnico.md):
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

from . import caminhos, config
from .arquivos import gravar_json, ler_json

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
BUSCA = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
POSTAGEM = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
PAGINAS_MAX = 30  # 300 vagas por palavra-chave é mais que suficiente
PAUSA = (3, 6)


def _pausa(intervalo=PAUSA):
    time.sleep(random.uniform(*intervalo))


def baixar(url: str, tentativas: int = 6) -> tuple[int, str]:
    """(código HTTP, corpo). Código 0 = desistiu depois de todas as tentativas."""
    for t in range(tentativas):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, ""
            codigo = e.code
        except (urllib.error.URLError, TimeoutError) as e:
            codigo = f"rede ({e})"
        espera = 30 + 30 * t
        print(f"   {codigo}: nova tentativa em {espera}s", file=sys.stderr, flush=True)
        time.sleep(espera)
    return 0, ""


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

def coleta(horas: int, saida: Path) -> dict:
    buscas = ler_json(caminhos.buscas(), None)
    if not buscas or not buscas.get("grupos"):
        raise SystemExit(f"Sem palavras-chave: preencha {caminhos.buscas()} (o questionário faz isso)")
    tpr = f"r{int(horas) * 3600}"
    vagas, falhas = {}, []
    for grupo in buscas["grupos"]:
        local = grupo["local"]
        for kw in grupo["palavras_chave"]:
            vistos_kw, start = set(), 0
            for _ in range(PAGINAS_MAX):
                q = urllib.parse.urlencode({"keywords": kw, "location": local, "f_TPR": tpr, "start": start})
                codigo, corpo = baixar(BUSCA + q)
                if codigo == 0:
                    falhas.append({"local": local, "palavra_chave": kw, "start": start})
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
            print(f"{local} · {kw}: {len(vistos_kw)}", file=sys.stderr, flush=True)
    resultado = {"horas": horas, "em": date.today().isoformat(), "vagas": list(vagas.values()), "falhas": falhas}
    gravar_json(saida, resultado)
    print(f"{len(vagas)} vagas únicas -> {saida}" + (f" ({len(falhas)} buscas incompletas)" if falhas else ""))
    return resultado


# ---------------------------------------------------------------- filtra

def _ja_no_radar() -> tuple[set, set]:
    """Ids do LinkedIn e pares empresa+cargo já vistos: Radar atual, histórico e arquivo."""
    ids, pares = set(), set()

    def anotar(v):
        m = re.search(r"jobs/view/(\d+)", v.get("url") or "")
        if m:
            ids.add(m.group(1))
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
    gravar_json(saida, {"entrada": str(entrada), "candidatas": candidatas, "cortes": motivos})
    print(f"{len(coletadas)} coletadas, {len(candidatas)} candidatas -> {saida}")
    for m, n in sorted(motivos.items(), key=lambda x: -x[1]):
        print(f"  {n:4} {m}")
    return candidatas


# ---------------------------------------------------------------- descrição e checagem

def descricao(ids, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for i in ids:
        codigo, corpo = baixar(POSTAGEM.format(i))
        criterios = " | ".join(_txt(r"(.*)", x) for x in
                               re.findall(r"description__job-criteria-text[^>]*>(.*?)</span>", corpo, re.S))
        fechada = "FECHADA" if (codigo in (404, 410) or "No longer accepting applications" in corpo) else ""
        m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", corpo, re.S)
        texto = html.unescape(re.sub(r"<br\s*/?>|</li>|</p>", "\n", m.group(1) if m else ""))
        texto = re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "", texto)).strip()
        (pasta / f"{i}.txt").write_text(f"{codigo} {fechada}\nCRITÉRIOS: {criterios}\n{texto}", encoding="utf-8")
        print(i, codigo, fechada or "aberta", f"{len(texto)} caracteres", flush=True)
        _pausa()


def checa(ids, saida: Path) -> dict:
    """Aberta ou fechada, retomável: o que já está no arquivo de saída não é baixado de novo."""
    resultado = ler_json(saida, {}) or {}
    for i in ids:
        if i in resultado:
            continue
        codigo, corpo = baixar(POSTAGEM.format(i))
        resultado[i] = {
            "codigo": codigo,
            "fechada": (codigo in (404, 410) or "No longer accepting applications" in corpo) if codigo else None,
            "ha": _txt(r"posted-time-ago__text[^>]*>(.*?)<", corpo),
            "titulo": _txt(r"topcard__title[^>]*>(.*?)<", corpo),
        }
        gravar_json(saida, resultado)
        print(i, resultado[i], flush=True)
        _pausa((4, 7))
    return resultado


def pasta_do_dia() -> Path:
    return caminhos.varredura() / date.today().isoformat()
