"""O contexto que a pessoa entrega na tela de abertura (bin/radar, primeira vez).

Cinco passos, todos opcionais e retomáveis:

1. LinkedIn   URL do perfil + export oficial (ZIP) ou "Salvar em PDF" do perfil
2. CV         o CV atual (PDF ou DOCX); o texto vira fonte de fatos A CONFIRMAR
3. E-mail     o que vai no cabeçalho do CV e nos formulários
4. Portfólio  o link principal e até 3 outros (GitHub, Behance, site)
5. Anexos     portfólio em PDF, estudos de caso, certificados, cartas

Onde cada coisa mora:
- `perfil.json > contatos` recebe e-mail, LinkedIn e portfólio (é de lá que o CV lê).
  Sem perfil ainda, nasce um perfil mínimo, que o import do LinkedIn completa depois.
- `contexto.json` guarda o estado dos passos e a lista de anexos.
- `anexos/` guarda os arquivos. O ZIP do LinkedIn NÃO fica: é lido e apagado, porque o
  export completo carrega conexões e mensagens, que são dados de terceiros.

Nada aqui sai do computador. Senha nunca entra: portfólio com senha é informado na hora,
quando um formulário pedir.
"""

import copy
import io
import os
import re
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

from . import caminhos
from .arquivos import editar_json, gravar_json, ler_json, trava

FUSO = timezone(timedelta(hours=-3))
PASSOS = ("linkedin", "cv", "email", "portfolio", "anexos")
LIMITE_ARQUIVO = 30 * 1024 * 1024  # o export "básico" do LinkedIn tem menos de 1 MB
MAX_ANEXOS = 20
CATEGORIAS = {
    "portfolio": "Portfólio em PDF",
    "case": "Estudo de caso",
    "certificado": "Certificado",
    "recomendacao": "Carta de recomendação",
    "outro": "Outro",
}

# assinatura dos primeiros bytes: a extensão sozinha não prova o que o arquivo é
ASSINATURAS = {
    "pdf": (b"%PDF",),
    "zip": (b"PK\x03\x04",),
    "docx": (b"PK\x03\x04",),
    "pptx": (b"PK\x03\x04",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
}
ACEITOS = {
    "linkedin": {"zip", "pdf"},
    "cv": {"pdf", "docx"},
    "anexo": {"pdf", "docx", "pptx", "png", "jpg", "jpeg", "webp", "txt", "md"},
}

URL_LINKEDIN = re.compile(r"^(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/([A-Za-z0-9\-_%]+)/?(?:[?#].*)?$", re.I)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
URL = re.compile(r"^(?:https?://)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:[/?#]\S*)?$", re.I)


class ContextoInvalido(ValueError):
    """Entrada recusada; a mensagem vai direto para a tela."""


def agora() -> str:
    return datetime.now(FUSO).isoformat(timespec="seconds")


def caminho() -> Path:
    return caminhos.dados() / "contexto.json"


def anexos() -> Path:
    return caminhos.dados() / "anexos"


def _gravar_privado(alvo: Path, conteudo) -> None:
    """CV e anexos são documentos pessoais: só o seu usuário lê (os JSONs já nascem assim)."""
    alvo.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(conteudo, str):
        alvo.write_text(conteudo, encoding="utf-8")
    else:
        alvo.write_bytes(conteudo)
    os.chmod(alvo, 0o600)


VAZIO = {
    "abertura": {"iniciada_em": "", "concluida_em": ""},
    "linkedin": {"url": "", "fonte": "", "importado_em": ""},
    "cv": {"arquivo": "", "texto": "", "enviado_em": ""},
    "email": "",
    "portfolio": {"url": "", "outros": []},
    "anexos": [],
    "pulados": [],
    "sugestoes": {},
}


def ler() -> dict:
    dados = ler_json(caminho(), None) or {}
    # cópia profunda: VAZIO é o molde, e lista compartilhada faria um anexo "vazar" de
    # uma leitura para a outra
    return {**copy.deepcopy(VAZIO), **dados}


def primeira_vez() -> bool:
    """A tela de abertura aparece até a pessoa concluir (ou pular) o passo a passo."""
    return not ler()["abertura"].get("concluida_em")


# ---------- normalização ----------

def _sem_protocolo(url: str) -> str:
    """O CV mostra 'linkedin.com/in/ana', não 'https://www.linkedin.com/in/ana/'."""
    url = re.sub(r"^https?://", "", url.strip(), flags=re.I)
    url = re.sub(r"^www\.", "", url, flags=re.I)
    return url.rstrip("/")


def _com_protocolo(url: str) -> str:
    url = url.strip()
    return url if re.match(r"^https?://", url, re.I) else f"https://{url}"


def normalizar_linkedin(url: str) -> str:
    m = URL_LINKEDIN.match((url or "").strip())
    if not m:
        raise ContextoInvalido("Use o endereço do SEU perfil, no formato linkedin.com/in/seu-nome.")
    return f"https://www.linkedin.com/in/{m.group(1)}"


def normalizar_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not EMAIL.match(email):
        raise ContextoInvalido("Esse e-mail parece incompleto. Confira o @ e o domínio.")
    return email


def normalizar_url(url: str) -> str:
    url = (url or "").strip()
    if not URL.match(url):
        raise ContextoInvalido(f"Não reconheci um endereço em “{url[:60]}”.")
    if re.search(r"linkedin\.com", url, re.I):
        raise ContextoInvalido("O LinkedIn já tem lugar no passo 1. Aqui vai o portfólio.")
    return _com_protocolo(url)


# ---------- perfil.json: contatos ----------

def _perfil_minimo() -> dict:
    return {
        "_leia": "Perfil mínimo criado na tela de abertura. O import do LinkedIn completa; /radar-perfil confirma.",
        "nome": "", "nome_cv": [], "headline": "", "resumo": "", "local": "",
        "contatos": {"email": "", "telefone": "", "linkedin": "", "portfolio": ""},
        "idiomas": [], "formacao": [], "experiencias": [], "competencias": [], "certificacoes": [],
        "provas": [], "fonte": {"importado_de": "tela-de-abertura", "em": agora()[:10]},
    }


def _gravar_contatos(**contatos) -> None:
    with editar_json(caminhos.perfil(), {}) as perfil:
        if not perfil:
            perfil.update(_perfil_minimo())
        perfil.setdefault("contatos", {}).update(contatos)


def _perfil_e_minimo() -> bool:
    p = ler_json(caminhos.perfil(), {}) or {}
    return not p or (not p.get("experiencias") and p.get("fonte", {}).get("importado_de") != "linkedin-export")


# ---------- campos de texto ----------

def salvar(campos: dict) -> dict:
    """Grava os campos enviados (só os presentes). Recusa o lote inteiro se um for inválido."""
    novos = {}
    if "linkedin_url" in campos:
        novos["linkedin_url"] = normalizar_linkedin(campos["linkedin_url"]) if str(campos["linkedin_url"]).strip() else ""
    if "email" in campos:
        novos["email"] = normalizar_email(campos["email"]) if str(campos["email"]).strip() else ""
    if "portfolio" in campos:
        novos["portfolio"] = normalizar_url(campos["portfolio"]) if str(campos["portfolio"]).strip() else ""
    if "outros_links" in campos:
        outros = [str(x) for x in (campos["outros_links"] or []) if str(x).strip()]
        if len(outros) > 3:
            raise ContextoInvalido("Até 3 links além do portfólio. O resto cabe no próprio portfólio.")
        novos["outros_links"] = [normalizar_url(x) for x in outros]

    with editar_json(caminho(), {}) as ctx:
        _completar(ctx)
        if "linkedin_url" in novos:
            ctx["linkedin"]["url"] = novos["linkedin_url"]
        if "email" in novos:
            ctx["email"] = novos["email"]
        if "portfolio" in novos:
            ctx["portfolio"]["url"] = novos["portfolio"]
        if "outros_links" in novos:
            ctx["portfolio"]["outros"] = novos["outros_links"]
        for passo in _passos_de(novos):
            if passo in ctx["pulados"]:
                ctx["pulados"].remove(passo)

    contatos = {}
    if "linkedin_url" in novos:
        contatos["linkedin"] = _sem_protocolo(novos["linkedin_url"])
    if "email" in novos:
        contatos["email"] = novos["email"]
    if "portfolio" in novos:
        contatos["portfolio"] = _sem_protocolo(novos["portfolio"])
    if contatos:
        _gravar_contatos(**contatos)
    return estado()


def _passos_de(novos: dict) -> list[str]:
    mapa = {"linkedin_url": "linkedin", "email": "email", "portfolio": "portfolio", "outros_links": "portfolio"}
    return [mapa[k] for k, v in novos.items() if v]


def _completar(ctx: dict) -> None:
    for chave, valor in VAZIO.items():
        if chave not in ctx:
            ctx[chave] = copy.deepcopy(valor)
    if not ctx["abertura"].get("iniciada_em"):
        ctx["abertura"]["iniciada_em"] = agora()


def pular(passo: str) -> dict:
    if passo not in PASSOS:
        raise ContextoInvalido(f"passo desconhecido: {passo}")
    with editar_json(caminho(), {}) as ctx:
        _completar(ctx)
        if passo not in ctx["pulados"]:
            ctx["pulados"].append(passo)
    return estado()


def concluir() -> dict:
    with editar_json(caminho(), {}) as ctx:
        _completar(ctx)
        ctx["abertura"]["concluida_em"] = agora()
    return estado()


# ---------- arquivos ----------

def nome_seguro(nome: str, padrao: str = "arquivo") -> tuple[str, str]:
    """('Meu CV (final).PDF') -> ('meu-cv-final', 'pdf'). Nada de pasta, ponto ou barra."""
    nome = Path(str(nome or "").replace("\\", "/")).name
    base, _, ext = nome.rpartition(".")
    if not base:
        base, ext = ext, ""
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:60] or padrao
    return base, re.sub(r"[^a-z0-9]", "", ext.lower())[:5]


def _conferir(conteudo: bytes, ext: str, tipo: str) -> None:
    if tipo not in ACEITOS:
        raise ContextoInvalido(f"tipo desconhecido: {tipo}")
    if ext not in ACEITOS[tipo]:
        aceitos = ", ".join(sorted(x.upper() for x in ACEITOS[tipo]))
        raise ContextoInvalido(f"Formato .{ext or '?'} não entra aqui. Aceitos: {aceitos}.")
    if not conteudo:
        raise ContextoInvalido("O arquivo chegou vazio.")
    if len(conteudo) > LIMITE_ARQUIVO:
        raise ContextoInvalido("Arquivo acima de 30 MB. Do LinkedIn, peça o export só do perfil.")
    assinaturas = ASSINATURAS.get(ext)
    if assinaturas and not conteudo.startswith(assinaturas):
        raise ContextoInvalido(f"O conteúdo não é de um .{ext} de verdade. Exporte de novo e tente outra vez.")
    if ext == "webp" and conteudo[8:12] != b"WEBP":
        raise ContextoInvalido("O conteúdo não é de um .webp de verdade.")
    if ext in ("txt", "md"):
        try:
            conteudo.decode("utf-8")
        except UnicodeDecodeError:
            raise ContextoInvalido("Texto fora de UTF-8. Salve de novo como UTF-8.")


def _livre(pasta: Path, base: str, ext: str) -> Path:
    alvo = pasta / f"{base}.{ext}"
    n = 2
    while alvo.exists():
        alvo = pasta / f"{base}-{n}.{ext}"
        n += 1
    return alvo


def _texto_docx(arquivo: Path) -> str:
    with zipfile.ZipFile(arquivo) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    return unescape(re.sub(r"<[^>]+>", "", xml)).strip()


def _texto_pdf(arquivo: Path) -> str:
    from pypdf import PdfReader  # só aqui: sem pypdf a tela ainda guarda o arquivo
    return "\n".join((p.extract_text() or "") for p in PdfReader(str(arquivo)).pages).strip()


def receber(tipo: str, nome: str, conteudo: bytes, categoria: str = "outro", descricao: str = "") -> dict:
    """Recebe um arquivo da tela de abertura e devolve o estado atualizado (+ aviso)."""
    base, ext = nome_seguro(nome)
    _conferir(conteudo, ext, tipo)
    pasta = anexos()
    pasta.mkdir(mode=0o700, parents=True, exist_ok=True)
    aviso = ""

    if tipo == "linkedin" and ext == "zip":
        aviso = _importar_export(conteudo)
    elif tipo == "linkedin":
        aviso = _guardar_pdf_linkedin(conteudo)
    elif tipo == "cv":
        aviso = _guardar_cv(conteudo, ext)
    else:
        if categoria not in CATEGORIAS:
            categoria = "outro"
        with trava(caminhos.dados()):
            ctx = ler()
            if len(ctx["anexos"]) >= MAX_ANEXOS:
                raise ContextoInvalido(f"Já são {MAX_ANEXOS} anexos. Tire algum antes de pôr outro.")
            alvo = _livre(pasta, base, ext)
            _gravar_privado(alvo, conteudo)
            ctx["anexos"].append({
                "arquivo": f"anexos/{alvo.name}",
                "nome_original": Path(str(nome).replace("\\", "/")).name[:120],
                "categoria": categoria,
                "descricao": str(descricao or "").strip()[:200],
                "tamanho": len(conteudo),
                "enviado_em": agora(),
            })
            _completar(ctx)
            if "anexos" in ctx["pulados"]:
                ctx["pulados"].remove("anexos")
            gravar_json(caminho(), ctx)
    return {**estado(), "aviso": aviso}


def _importar_export(conteudo: bytes) -> str:
    from . import perfil
    if not zipfile.is_zipfile(io.BytesIO(conteudo)):
        raise ContextoInvalido("O ZIP veio corrompido. Baixe o export de novo.")
    salvo = ler()
    with tempfile.TemporaryDirectory(dir=caminhos.dados()) as tmp:
        zip_ = Path(tmp) / "export.zip"
        zip_.write_bytes(conteudo)
        try:
            # perfil mínimo (só contatos da tela) é sobrescrito; perfil de verdade nunca
            destino = perfil.importar(zip_, sobrescrever=_perfil_e_minimo())
        except SystemExit as e:
            raise ContextoInvalido(str(e))
    # o export raramente traz o link do perfil; o que a pessoa digitou na tela vence o vazio
    if destino == caminhos.perfil():
        contatos = {}
        if salvo["linkedin"]["url"]:
            contatos["linkedin"] = _sem_protocolo(salvo["linkedin"]["url"])
        if salvo["email"]:
            contatos["email"] = salvo["email"]
        if salvo["portfolio"]["url"]:
            contatos["portfolio"] = _sem_protocolo(salvo["portfolio"]["url"])
        if contatos:
            _gravar_contatos(**contatos)
    with editar_json(caminho(), {}) as ctx:
        _completar(ctx)
        ctx["linkedin"].update({"fonte": "export", "importado_em": agora()})
        if "linkedin" in ctx["pulados"]:
            ctx["pulados"].remove("linkedin")
        # e-mail e site do export viram SUGESTÃO: a tela pré-preenche e a pessoa confirma
        importados = (ler_json(destino, {}) or {}).get("contatos", {})
        if importados.get("email"):
            ctx["sugestoes"]["email"] = importados["email"].strip().lower()
        if importados.get("portfolio"):
            ctx["sugestoes"]["portfolio"] = _com_protocolo(importados["portfolio"])
    if destino != caminhos.perfil():
        return "Você já tinha um perfil: o import foi para perfil.importado.json, para comparar com calma."
    return ""


def _guardar_pdf_linkedin(conteudo: bytes) -> str:
    alvo = anexos() / "linkedin-perfil.pdf"
    _gravar_privado(alvo, conteudo)
    aviso = ""
    try:
        texto = _texto_pdf(alvo)
        _gravar_privado(caminhos.dados() / "perfil-bruto.txt", texto)
    except ImportError:
        aviso = "PDF guardado. O texto sai quando o pypdf estiver instalado (bin/instalar)."
    with editar_json(caminho(), {}) as ctx:
        _completar(ctx)
        ctx["linkedin"].update({"fonte": "pdf", "importado_em": agora()})
        if "linkedin" in ctx["pulados"]:
            ctx["pulados"].remove("linkedin")
    return aviso


def _guardar_cv(conteudo: bytes, ext: str) -> str:
    pasta = anexos()
    for velho in pasta.glob("cv-atual.*"):  # um CV atual só: o novo substitui
        velho.unlink()
    alvo = pasta / f"cv-atual.{ext}"
    _gravar_privado(alvo, conteudo)
    texto, aviso = "", ""
    try:
        texto = _texto_docx(alvo) if ext == "docx" else _texto_pdf(alvo)
    except ImportError:
        aviso = "CV guardado. O texto sai quando o pypdf estiver instalado (bin/instalar)."
    except Exception:
        aviso = "CV guardado, mas não consegui ler o texto dele (PDF de imagem?). Tudo bem: o questionário cobre."
    if texto:
        _gravar_privado(pasta / "cv-atual.txt", texto)
    with editar_json(caminho(), {}) as ctx:
        _completar(ctx)
        ctx["cv"] = {"arquivo": f"anexos/{alvo.name}", "texto": "anexos/cv-atual.txt" if texto else "",
                     "palavras": len(texto.split()), "enviado_em": agora()}
        if "cv" in ctx["pulados"]:
            ctx["pulados"].remove("cv")
    return aviso


def remover(arquivo: str) -> dict:
    """Tira um anexo da lista e do disco. Só mexe dentro de anexos/."""
    with trava(caminhos.dados()):
        ctx = ler()
        item = next((a for a in ctx["anexos"] if a.get("arquivo") == arquivo), None)
        if item is None:
            raise ContextoInvalido("Esse anexo não está na lista.")
        base = anexos().resolve()
        alvo = (caminhos.dados() / item["arquivo"]).resolve()
        if base in alvo.parents and alvo.exists():
            alvo.unlink()
        ctx["anexos"].remove(item)
        gravar_json(caminho(), ctx)
    return estado()


# ---------- estado para a tela ----------

def estado() -> dict:
    ctx = ler()
    perfil = ler_json(caminhos.perfil(), {}) or {}
    feitos = {
        "linkedin": bool(ctx["linkedin"]["url"] or ctx["linkedin"]["importado_em"]),
        "cv": bool(ctx["cv"].get("arquivo")),
        "email": bool(ctx["email"]),
        "portfolio": bool(ctx["portfolio"]["url"]),
        "anexos": bool(ctx["anexos"]),
    }
    return {
        "ok": True,
        "primeira_vez": not ctx["abertura"].get("concluida_em"),
        "feitos": feitos,
        "pulados": [p for p in ctx["pulados"] if not feitos.get(p)],
        "linkedin": {
            **ctx["linkedin"],
            "nome": perfil.get("nome", ""),
            "experiencias": len(perfil.get("experiencias", [])),
            "competencias": len(perfil.get("competencias", [])),
        },
        "cv": ctx["cv"],
        "email": ctx["email"],
        "portfolio": ctx["portfolio"],
        "anexos": ctx["anexos"],
        "sugestoes": ctx["sugestoes"],
        "categorias": CATEGORIAS,
        "aceitos": {k: sorted(v) for k, v in ACEITOS.items()},
    }
