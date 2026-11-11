"""Gera a carta de apresentação em PDF, na mesma identidade visual do CV.

    bin/radar carta meus-dados/cvs/Carta-Empresa-Cargo.md meus-dados/cvs/Nome-Carta-Empresa-Cargo.pdf

Formato do .md: um cabeçalho de contexto (anotação interna: vaga, ângulo, data), uma linha
com --- e então o corpo. Só o corpo depois do PRIMEIRO --- vira PDF. O nome e o rodapé de
contatos saem de meus-dados/perfil.json; o corpo não precisa assinar.
"""

import re
import sys
from pathlib import Path

from . import caminhos
from .arquivos import ler_json
from .cv import esc, fontes_css


def corpo_da_carta(md: str) -> list[str]:
    partes = md.split("\n---\n", 1)
    corpo = partes[1] if len(partes) > 1 else partes[0]
    corpo = re.sub(r"^#.*$", "", corpo, flags=re.MULTILINE)
    blocos = [b for b in corpo.split("\n\n") if b.strip()]
    return [" ".join(l.strip() for l in b.splitlines() if l.strip()) for b in blocos]


def montar_html(paragrafos: list[str], perfil: dict, titulo: str, faces: str) -> str:
    linhas_nome = "<br>".join(esc(x) for x in (perfil.get("nome_cv") or [perfil.get("nome", "")]) if x)
    c = perfil.get("contatos", {})
    rodape = " · ".join(esc(c[k]) for k in ("email", "telefone", "linkedin", "portfolio") if c.get(k))
    corpo = "".join(f"<p>{esc(p)}</p>" for p in paragrafos)
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<title>{esc(titulo)}</title><style>
{faces}
:root{{--bg:#F5F4F0;--ink:#050505;--body:#3C3C3A;--muted:#8B8B88;--hair:#DCDBD6;}}
@page{{size:A4;margin:0;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:210mm;min-height:297mm;background:var(--bg);
  font-family:"CVFont","Figtree","Helvetica Neue",Arial,sans-serif;color:var(--body);-weasy-hyphens:none;}}
.page{{width:210mm;min-height:297mm;padding:20mm 22mm 16mm 22mm;display:flex;flex-direction:column;}}
.name{{font-weight:900;color:var(--ink);font-size:24pt;line-height:1.04;letter-spacing:-0.01em;}}
.rule{{border:none;border-top:0.35mm solid var(--hair);margin:7mm 0 9mm 0;}}
p{{font-size:10.6pt;line-height:1.72;margin-bottom:5.2mm;max-width:150mm;}}
.sign{{margin-top:4mm;font-weight:600;color:var(--ink);font-size:10.6pt;}}
.foot{{margin-top:auto;padding-top:10mm;color:var(--muted);font-size:8.6pt;}}
</style></head><body><div class="page">
<div class="name">{linhas_nome}</div>
<hr class="rule">
{corpo}
<div class="sign">{esc(perfil.get("nome", ""))}</div>
<div class="foot">{rodape}</div>
</div></body></html>"""


def gerar(entrada: Path, saida: Path) -> int:
    try:
        from weasyprint import HTML
    except ImportError:
        raise SystemExit("Falta o weasyprint: rode bin/instalar")
    perfil = ler_json(caminhos.perfil(), None)
    if not perfil or not perfil.get("nome"):
        raise SystemExit(f"Sem perfil com nome em {caminhos.perfil()}: rode /radar-perfil primeiro")
    paragrafos = corpo_da_carta(entrada.read_text(encoding="utf-8"))
    if not paragrafos:
        print("ERRO: não achei corpo de carta no arquivo (falta a linha ---?)")
        return 1
    palavras = sum(len(p.split()) for p in paragrafos)
    faces, _ = fontes_css()
    doc = HTML(string=montar_html(paragrafos, perfil, entrada.stem, faces)).render()
    saida.parent.mkdir(parents=True, exist_ok=True)
    doc.write_pdf(str(saida))
    print(f"OK: {saida} ({len(doc.pages)} página{'s' if len(doc.pages) > 1 else ''}, {palavras} palavras)")
    if len(doc.pages) > 1:
        print("AVISO: a carta passou de 1 página. Encurte antes de enviar.")
    return 0


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    return gerar(Path(argv[0]), Path(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
