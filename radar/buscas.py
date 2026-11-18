"""O que a varredura procura no LinkedIn: as buscas de cada pessoa, nunca as do exemplo.

O caminho do buscas.json:

1. `bin/radar init` cria o arquivo vazio. Sem palavra-chave, a coleta recusa e diz onde
   preencher, em vez de varrer cargos que não são os da pessoa.
2. O passo "Posições" da tela de abertura monta a primeira versão: cada posição que a
   pessoa escreveu vira uma busca, no país do perfil do LinkedIn (`origem: "posicoes"`).
3. O `/radar-configurar` (bloco Busca) lê o LinkedIn e o CV e refina: variações em
   português e inglês, títulos equivalentes, filtro de título (`origem: "questionario"`).
   Daí em diante a tela não sobrescreve mais; posição nova entra pelo questionário.

O `exemplos/buscas.json` (cargos de design) só existe para a demonstração. Uma cópia dele
nos dados de alguém é tratada como vazia: a coleta recusa e o passo "Posições" substitui.
"""

import copy
import re
import unicodedata

from . import caminhos
from .arquivos import editar_json, ler_json

MAX_POSICOES = 8

VAZIO = {
    "_leia": "O que a varredura procura. Nasce das posições que você escreveu na tela de "
             "abertura e é refinado pelo /radar-configurar a partir do seu LinkedIn e CV. "
             "Uma palavra-chave por busca: o LinkedIn não respeita OR nem aspas.",
    "origem": "",
    "janela_horas": 48,
    "grupos": [],
    "filtro_titulo": {"precisa_ter": [], "senioridade": [], "descartar_se_tiver": []},
    "corte": {
        "descartar_se": [
            "senioridade abaixo da mínima do config",
            "modelo de trabalho fora de config.trabalho",
            "mesma empresa e mesmo cargo já no Radar ou no arquivo",
            "vaga sem descrição real (link quebrado ou fechada)",
        ]
    },
}


def vazio() -> dict:
    return copy.deepcopy(VAZIO)


def ler() -> dict:
    return ler_json(caminhos.buscas(), None) or vazio()


def palavras(buscas: dict) -> list[str]:
    return [kw for g in buscas.get("grupos") or [] for kw in g.get("palavras_chave") or [] if str(kw).strip()]


def e_exemplo(buscas: dict) -> bool:
    """A cópia do exemplo de design que o init antigo punha nos dados de todo mundo."""
    if buscas.get("origem") == "exemplo":
        return True
    exemplo = ler_json(caminhos.EXEMPLOS / "buscas.json", {}) or {}
    return bool(palavras(buscas)) and buscas.get("grupos") == exemplo.get("grupos")


def pode_gerar(buscas: dict) -> bool:
    """A tela só escreve onde ninguém refinou: vazio, exemplo ou a versão que ela mesma fez."""
    return not palavras(buscas) or e_exemplo(buscas) or buscas.get("origem") == "posicoes"


def pais(perfil: dict) -> str:
    """'Recife, Pernambuco, Brazil' -> 'Brazil': a busca do LinkedIn aceita país ou região."""
    partes = [p.strip() for p in str(perfil.get("local") or "").split(",") if p.strip()]
    return partes[-1] if partes else ""


def _chave(texto: str) -> str:
    return " ".join(str(texto).split()).casefold()


def sugerir_posicoes(perfil: dict, limite: int = 6) -> list[str]:
    """Cargos da trajetória, do mais recente para o mais antigo, e o título do headline."""
    experiencias = sorted(
        perfil.get("experiencias") or [],
        key=lambda x: ("9999-99" if x.get("fim") == "atual" else str(x.get("fim") or ""), str(x.get("inicio") or "")),
        reverse=True,
    )
    candidatos = [x.get("cargo", "") for x in experiencias]
    # headline costuma ser "Cargo | tema | tema" ou "Cargo na Empresa": fica o primeiro trecho
    cabeca = re.split(r"\s+(?:\||·|•|—|-|@|at|na|no|em)\s+", str(perfil.get("headline") or ""), maxsplit=1)[0]
    if cabeca and len(cabeca.split()) <= 6:
        candidatos.insert(0, cabeca)
    vistos, saida = set(), []
    for c in candidatos:
        c = " ".join(str(c).split())
        if 2 <= len(c) <= 80 and _chave(c) not in vistos:
            vistos.add(_chave(c))
            saida.append(c)
    return saida[:limite]


def limpar_posicoes(posicoes) -> list[str]:
    if not isinstance(posicoes, list):
        raise ValueError("Mande as posições como lista.")
    vistos, saida = set(), []
    for p in posicoes:
        p = " ".join(str(p or "").split())
        if not p:
            continue
        if len(p) < 2 or len(p) > 80:
            raise ValueError(f"'{p[:40]}' não parece um cargo: use de 2 a 80 caracteres.")
        if _chave(p) not in vistos:
            vistos.add(_chave(p))
            saida.append(p)
    if len(saida) > MAX_POSICOES:
        raise ValueError(f"Até {MAX_POSICOES} posições. Mais que isso dilui a busca.")
    return saida


def atualizar_com_posicoes(posicoes: list[str], perfil: dict) -> bool:
    """Monta as buscas com as posições, se ninguém refinou ainda. Devolve se gravou."""
    with editar_json(caminhos.buscas(), vazio()) as buscas:
        if not pode_gerar(buscas):
            return False
        novo = vazio()
        novo["janela_horas"] = buscas.get("janela_horas") or novo["janela_horas"]
        if posicoes:
            novo["origem"] = "posicoes"
            novo["grupos"] = [{"local": pais(perfil), "palavras_chave": list(posicoes)}]
        buscas.clear()
        buscas.update(novo)
    return True


# ---------------------------------------------------------------- idioma do país da busca
# Num país que não fala inglês, a maioria das vagas pede a língua local fluente, e a
# triagem corta todas essas. Num teste na França, sem francês fluente, sobraram 3 vagas
# boas em 1.228. A pessoa precisa saber disso ANTES da primeira varredura, não depois.

IDIOMAS = {  # chave -> (nome para a frase, como aparece no perfil do LinkedIn, em en e pt)
    "fr": ("francês", {"french", "frances", "francais"}),
    "de": ("alemão", {"german", "alemao", "deutsch"}),
    "es": ("espanhol", {"spanish", "espanhol", "espanol", "castellano"}),
    "it": ("italiano", {"italian", "italiano"}),
    "pt": ("português", {"portuguese", "portugues"}),
    "nl": ("holandês", {"dutch", "holandes", "neerlandes", "nederlands"}),
    "ja": ("japonês", {"japanese", "japones"}),
    "ko": ("coreano", {"korean", "coreano"}),
    "zh": ("chinês", {"chinese", "mandarin", "chines", "mandarim"}),
    "pl": ("polonês", {"polish", "polones"}),
}
# países onde a vaga costuma exigir a língua local (os nórdicos e a Holanda contratam
# muito em inglês e ficam de fora para o aviso não virar ruído)
PAISES = {
    "france": ("fr",), "franca": ("fr",),
    "germany": ("de",), "alemanha": ("de",), "austria": ("de",),
    "switzerland": ("de", "fr", "it"), "suica": ("de", "fr", "it"),
    "belgium": ("fr", "nl"), "belgica": ("fr", "nl"),
    "spain": ("es",), "espanha": ("es",), "mexico": ("es",), "argentina": ("es",), "chile": ("es",),
    "colombia": ("es",), "peru": ("es",), "uruguay": ("es",), "uruguai": ("es",),
    "italy": ("it",), "italia": ("it",),
    "portugal": ("pt",), "brazil": ("pt",), "brasil": ("pt",),
    "japan": ("ja",), "japao": ("ja",),
    "south korea": ("ko",), "coreia do sul": ("ko",),
    "china": ("zh",), "taiwan": ("zh",),
    "poland": ("pl",), "polonia": ("pl",),
}
# nível que não sustenta uma entrevista no idioma (LinkedIn em inglês e em português)
NIVEL_FRACO = ("elementary", "limited", "elementar", "limitada", "basic", "basico", "iniciante")


def _norm(texto: str) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "").casefold()).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def _pais_da_busca(local: str) -> str:
    """'Paris, Île-de-France, France' -> 'france'; região ('EMEA', 'Europe') -> ''."""
    ultimo = _norm(str(local).split(",")[-1])
    return ultimo if ultimo in PAISES else ""


def _fala_fluente(perfil: dict, idioma: str) -> bool:
    nomes = IDIOMAS[idioma][1]
    for x in perfil.get("idiomas") or []:
        if _norm(x.get("idioma")) in nomes and not any(f in _norm(x.get("nivel")) for f in NIVEL_FRACO):
            return True
    return False


def avisos_idioma(buscas: dict, perfil: dict) -> list[str]:
    """Uma frase por local de busca cujo idioma de trabalho a pessoa não mostra ter fluente."""
    perfil = perfil or {}
    pais_da_pessoa = _pais_da_busca(pais(perfil))
    sabe_idiomas = bool(perfil.get("idiomas"))
    avisos, vistos = [], set()
    for g in buscas.get("grupos") or []:
        local = str(g.get("local") or "")
        chave = _pais_da_busca(local)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        idiomas = PAISES[chave]
        if any(_fala_fluente(perfil, i) for i in idiomas):
            continue
        if not sabe_idiomas and chave == pais_da_pessoa:
            continue  # sem idiomas no perfil, quem mora no país provavelmente fala a língua
        nome = " ou ".join(IDIOMAS[i][0] for i in idiomas)
        o_perfil = ("o seu perfil não mostra esse idioma em nível de trabalho" if sabe_idiomas
                    else "o seu perfil não lista idiomas para conferir")
        avisos.append(
            f"Busca em {local}: a maioria das vagas lá pede {nome} fluente, e {o_perfil}. "
            f"A triagem corta essas vagas, e a mesa tende a ficar pequena. Para ampliar, "
            f"some uma região que contrata em inglês (\"European Union\", \"EMEA\") ou "
            f"vagas remotas de empresas internacionais.")
    return avisos


def resumo(buscas: dict, perfil: dict | None = None) -> dict:
    """O que a tela mostra: de onde vieram as buscas, o que a varredura vai procurar e o
    aviso de idioma quando o país da busca pede uma língua que o perfil não mostra."""
    exemplo = e_exemplo(buscas)
    return {
        "origem": "exemplo" if exemplo else buscas.get("origem") or ("manual" if palavras(buscas) else ""),
        "palavras_chave": [] if exemplo else palavras(buscas),
        "locais": [] if exemplo else sorted({g.get("local", "") for g in buscas.get("grupos") or [] if g.get("local")}),
        "avisos": [] if exemplo else avisos_idioma(buscas, perfil or {}),
    }
