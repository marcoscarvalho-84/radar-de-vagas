"""Gera o CV em PDF (1 página, A4) a partir de um JSON de conteúdo.

    bin/radar cv meus-dados/cvs/cv-empresa.json meus-dados/cvs/Nome-CV-Empresa-Cargo.pdf

O JSON de conteúdo (exemplo completo em exemplos/cv-exemplo.json):
    doc_title, idioma ("en"|"pt-BR")
    tagline_l1, tagline_l2      duas linhas do topo direito
    location_line               ex.: "Recife, PE · remote-first"
    hook_main, hook_accent      frase-gancho em duas partes (a segunda em cinza, linha nova)
    positioning_label, positioning
    why_label, why_rows         4 linhas {"label", "text"} (ver docs/padroes.md, seção CV)
    experience_label, experience  [{"role_line", "meta", "desc"}]
    tools_line, languages_line

Nome e contatos NÃO vão no JSON: saem de meus-dados/perfil.json, para nenhum CV sair
com contato velho ou de outra pessoa.

Fonte: Figtree (SIL OFL, empacotada em templates/fonts). Para usar outra fonte licenciada
por você, coloque os arquivos em meus-dados/fontes/ como Familia-Peso.ttf|otf|woff2
(Regular, Medium, SemiBold, Bold, Black) e ela passa a valer sozinha.

O script aperta a densidade até caber em 1 página, avisa quando aperta, gera um PNG de
preview ao lado (precisa do pdftoppm, do poppler) e FALHA se nem no mínimo couber.
"""

import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import caminhos
from .arquivos import ler_json

TEMPLATE = caminhos.TEMPLATES / "cv.html"
PESOS = {"Black": 900, "Bold": 700, "SemiBold": 600, "Medium": 500, "Regular": 400}

# Piso do auto-ajuste: abaixo disso o corpo fica pequeno demais para ler em tela.
DENSIDADE_MIN = 0.86
DENSIDADE_AVISO = 0.92

# Valores do template que encolhem junto com a densidade: corpos de texto e respiros
# VERTICAIS. Larguras ficam de fora, senão a grade se desmancha. O WeasyPrint ignora
# calc() em font-size, então os valores saem daqui já calculados.
ESCALAVEIS = [
    (".name", "font-size", 27.5, "pt"),
    (".head-right", "font-size", 8.6, "pt"),
    (".head-right .loc", "margin-bottom", 1.6, "mm"),
    (".hook", "margin-top", 7.5, "mm"),
    (".hook", "font-size", 17, "pt"),
    (".rule", "margin-top", 5.5, "mm"),
    (".section", "margin-top", 6, "mm"),
    (".rail", "font-size", 6.8, "pt"),
    (".positioning", "font-size", 9.3, "pt"),
    (".why-row", "padding-top", 2.6, "mm"),
    (".why-row", "padding-bottom", 2.6, "mm"),
    (".why-label", "font-size", 8.8, "pt"),
    (".why-text", "font-size", 8.8, "pt"),
    (".xp", "margin-bottom", 4.2, "mm"),
    (".xp-role", "font-size", 9.3, "pt"),
    (".xp-meta", "font-size", 6.6, "pt"),
    (".xp-desc", "font-size", 8.6, "pt"),
    (".footer", "padding-top", 3.2, "mm"),
    (".footer", "font-size", 6.6, "pt"),
    (".page", "padding-top", 13, "mm"),
    (".page", "padding-bottom", 12, "mm"),
]

# Rótulos do "Why" ocupam coluna estreita e quebram sozinhos em lugar feio. A quebra é
# escolhida: vírgula primeiro, senão antes da preposição mais próxima do meio, senão a
# fronteira de palavra mais próxima do meio.
LABEL_QUEBRA_MIN = 21
LIGACOES = {"with", "to", "for", "across", "in", "on", "at", "from", "of", "into", "and", "that",
            "not", "as", "without", "over", "under",
            "com", "para", "por", "de", "da", "do", "em", "no", "na", "e", "que"}


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def esc_br(s) -> str:
    return esc(s).replace("\n", "<br>")


def quebrar_label(label) -> str:
    texto = " ".join(str(label).split())
    if len(texto) <= LABEL_QUEBRA_MIN or "\n" in str(label):
        return str(label)
    meio = len(texto) / 2
    palavras = texto.split(" ")
    inicios, pos = [], 0
    for p in palavras:
        inicios.append(pos)
        pos += len(p) + 1
    candidatos = []
    for i, p in enumerate(palavras):
        if i == 0:
            continue
        if min(inicios[i] - 1, len(texto) - inicios[i]) < 6:
            continue  # linha órfã de uma palavrinha é pior que a quebra natural
        dist = abs(inicios[i] - meio)
        if palavras[i - 1].endswith(","):
            candidatos.append((0, dist, i))
        elif p.strip(",.").lower() in LIGACOES:
            candidatos.append((1, dist, i))
        else:
            candidatos.append((2, dist, i))
    if not candidatos:
        return texto
    _, _, corte = min(candidatos)
    return " ".join(palavras[:corte]) + "\n" + " ".join(palavras[corte:])


def densidade_css(densidade: float) -> str:
    if densidade >= 0.999:
        return ""
    regras = [f"{sel}{{{prop}:{valor * densidade:.3f}{unidade};}}" for sel, prop, valor, unidade in ESCALAVEIS]
    regras += [".why-row:first-child{padding-top:0;}", ".xp:last-child{margin-bottom:0;}"]
    return "\n  ".join(regras)


def fontes_css() -> tuple[str, str]:
    """(@font-face, nome da família). Fonte do usuário em meus-dados/fontes vence a Figtree."""
    for pasta in (caminhos.dados() / "fontes", caminhos.FONTES):
        arquivos = sorted(f for f in pasta.glob("*-*.*") if f.suffix.lower() in (".ttf", ".otf", ".woff2"))
        familias = sorted({f.stem.split("-", 1)[0] for f in arquivos})
        for familia in familias:
            css = []
            for f in arquivos:
                fam, peso = f.stem.split("-", 1)
                if fam == familia and peso in PESOS:
                    css.append('@font-face{font-family:"CVFont";src:url("%s");font-weight:%d;font-style:normal;}'
                               % (f.resolve().as_uri(), PESOS[peso]))
            if css:
                return "\n  ".join(css), familia
    return "", "genérica"


def cabecalho(perfil: dict) -> tuple[str, str]:
    linhas = perfil.get("nome_cv") or [perfil.get("nome", "")]
    nome = "<br>".join(esc(x) for x in linhas if x)
    c = perfil.get("contatos", {})
    contatos = "<br>".join(esc(c[k]) for k in ("email", "telefone", "linkedin", "portfolio") if c.get(k))
    return nome, contatos


def montar_html(dados: dict, perfil: dict, densidade: float = 1.0, faces: str = "") -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    nome, contatos = cabecalho(perfil)
    why = "".join(
        '<div class="why-row"><div class="why-label">%s</div><div class="why-text">%s</div></div>'
        % (esc_br(quebrar_label(r["label"])), esc(r["text"])) for r in dados.get("why_rows", []))
    xp = "".join(
        '<div class="xp"><div class="xp-head"><div class="xp-role">%s</div><div class="xp-meta">%s</div></div>'
        '<div class="xp-desc">%s</div></div>' % (esc(x["role_line"]), esc(x["meta"]), esc(x["desc"]))
        for x in dados.get("experience", []))
    troca = {
        "{{IDIOMA}}": esc(dados.get("idioma", "en")),
        "{{DOC_TITLE}}": esc(dados.get("doc_title", f"{perfil.get('nome', '')} · CV")),
        "{{FONT_FACES}}": faces,
        "{{DENSITY_OVERRIDES}}": densidade_css(densidade),
        "{{NOME}}": nome,
        "{{CONTATOS}}": contatos,
        "{{TAGLINE_L1}}": esc(dados.get("tagline_l1", "")),
        "{{TAGLINE_L2}}": esc(dados.get("tagline_l2", "")),
        "{{LOCATION_LINE}}": esc(dados.get("location_line", perfil.get("local", ""))),
        "{{HOOK_MAIN}}": esc(dados.get("hook_main", "")),
        "{{HOOK_ACCENT}}": esc(dados.get("hook_accent", "")),
        "{{POSITIONING_LABEL}}": esc(dados.get("positioning_label", "Positioning")),
        "{{POSITIONING}}": esc(dados.get("positioning", "")),
        "{{WHY_LABEL}}": esc(dados.get("why_label", "Why this role")),
        "{{WHY_ROWS}}": why,
        "{{EXPERIENCE_LABEL}}": esc(dados.get("experience_label", "Experience")),
        "{{EXPERIENCE}}": xp,
        "{{TOOLS_LINE}}": esc(dados.get("tools_line", "")),
        "{{LANGUAGES_LINE}}": esc(dados.get("languages_line", "")),
    }
    for k, v in troca.items():
        tpl = tpl.replace(k, v)
    return tpl


def _paginas(pdf: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except ImportError:
        print("AVISO: sem pypdf não dá para conferir o número de páginas (rode bin/instalar)")
        return 1


def preview(pdf: Path) -> Path | None:
    if not shutil.which("pdftoppm"):
        print("AVISO: sem pdftoppm (poppler) o preview PNG não é gerado: brew install poppler")
        return None
    prefixo = pdf.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(pdf), str(prefixo)], check=False)
    return prefixo.with_suffix(".png")


def gerar(entrada: Path, saida: Path) -> int:
    try:
        from weasyprint import HTML
    except ImportError:
        raise SystemExit("Falta o weasyprint: rode bin/instalar")
    perfil = ler_json(caminhos.perfil(), None)
    if not perfil or not perfil.get("nome"):
        raise SystemExit(f"Sem perfil com nome em {caminhos.perfil()}: rode /radar-perfil primeiro")
    dados = json.loads(entrada.read_text(encoding="utf-8"))
    faces, familia = fontes_css()
    print(f"Fonte em uso: {familia}")

    saida.parent.mkdir(parents=True, exist_ok=True)
    densidade = 1.0
    while True:
        html_str = montar_html(dados, perfil, densidade, faces)
        HTML(string=html_str, base_url=str(caminhos.TEMPLATES)).write_pdf(str(saida))
        n = _paginas(saida)
        if n == 1 or densidade <= DENSIDADE_MIN + 1e-9:
            break
        densidade = round(densidade - 0.02, 3)

    png = preview(saida)
    if n > 1:
        print(f"ERRO: o CV estourou para {n} páginas mesmo na densidade mínima ({DENSIDADE_MIN:.2f}). "
              "Encurte positioning, why_rows ou as descrições e gere de novo.")
        return 1
    aviso = ""
    if densidade < 0.995:
        aviso = f" · densidade {densidade:.2f}"
        if densidade < DENSIDADE_AVISO:
            aviso += " (apertado demais: corte texto de verdade)"
    print(f"OK: {saida} (1 página){aviso}" + (f" · preview: {png}" if png else ""))
    return 0


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    return gerar(Path(argv[0]), Path(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
