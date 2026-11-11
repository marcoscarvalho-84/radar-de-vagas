"""Monta o dashboard com os seus dados dentro.

O modelo (`dashboard/index.html` + `styles.css`) é versionado e nunca recebe dados. O
resultado vai para `meus-dados/painel/`, fora do git: um HTML único e auto-contido que
abre por duplo clique (file://, modo leitura) ou servido pelo `bin/radar painel`
(botões ao vivo).

O bloco entre os marcadores DADOS:INICIO / DADOS:FIM recebe:
- registro.json -> window.REGISTRO  (histórico executado)
- vagas.json    -> window.VAGAS     (o que aguarda decisão)
- config        -> window.CONFIG    (só o recorte que o painel usa, ver config.para_painel)
"""

import json
import os
import re
import shutil
import tempfile

from . import caminhos, config
from .arquivos import ler_json

INICIO = "<!-- DADOS:INICIO (gerado por radar/gerar_dados.py, não editar à mão) -->"
FIM = "<!-- DADOS:FIM -->"


def _js(dados) -> str:
    if "dias" in dados:
        dados = {**dados, "dias": sorted(dados["dias"], key=lambda d: d.get("data", ""), reverse=True)}
    # "</script>" dentro de string JSON quebraria o parser de HTML
    return json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")


def desatualizado() -> bool:
    """True quando algum JSON mudou depois do último painel gerado."""
    alvo = caminhos.painel() / "index.html"
    if not alvo.exists():
        return True
    fontes = [caminhos.vagas(), caminhos.registro(), caminhos.config(), caminhos.perfil(),
              caminhos.DASHBOARD / "index.html", caminhos.DASHBOARD / "styles.css"]
    return any(f.exists() and f.stat().st_mtime > alvo.stat().st_mtime for f in fontes)


def gerar() -> str:
    cfg = config.carregar()
    perfil = ler_json(caminhos.perfil(), {}) or {}
    registro = ler_json(caminhos.registro(), {"dias": []}) or {"dias": []}
    vagas = ler_json(caminhos.vagas(), {"vagas": [], "pessoas": []}) or {"vagas": [], "pessoas": []}

    html = (caminhos.DASHBOARD / "index.html").read_text(encoding="utf-8")
    bloco = (
        f"{INICIO}\n"
        f"  <script>\n"
        f"  window.REGISTRO = {_js(registro)};\n"
        f"  window.VAGAS = {_js(vagas)};\n"
        f"  window.CONFIG = {_js(config.para_painel(cfg, perfil))};\n"
        f"  </script>\n"
        f"  {FIM}"
    )
    # replacement como função: evita que re interprete "\n" do JSON como escape
    novo, n = re.subn(re.escape(INICIO) + r".*?" + re.escape(FIM), lambda _: bloco, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("Marcadores DADOS:INICIO/DADOS:FIM não encontrados em dashboard/index.html")

    destino = caminhos.painel()
    destino.mkdir(parents=True, exist_ok=True)
    estilos = caminhos.DASHBOARD / "styles.css"
    shutil.copyfile(estilos, destino / "styles.css")
    # cache-busting do CSS: sem isso o navegador segura a folha antiga e um ajuste de
    # estilo simplesmente não aparece, o que engana na conferência
    versao = int(estilos.stat().st_mtime)
    novo = re.sub(r'href="styles\.css(\?v=\d+)?"', f'href="styles.css?v={versao}"', novo, count=1)
    # dois cliques seguidos regeram ao mesmo tempo: grava num temporário e troca de uma
    # vez, para o navegador nunca receber um HTML pela metade
    fd, tmp = tempfile.mkstemp(prefix=".index", suffix=".html", dir=destino)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(novo)
    os.replace(tmp, destino / "index.html")
    return str(destino / "index.html")


def main() -> None:
    print("Painel atualizado:", gerar())
