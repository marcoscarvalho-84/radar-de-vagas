"""Onde cada coisa mora.

Tudo que é seu (perfil, vagas, histórico, CVs) fica numa pasta só, `meus-dados/`, que o
.gitignore já exclui. A variável RADAR_DADOS aponta para outra pasta quando preciso
(é assim que o `bin/radar demo` roda em cima de uma cópia dos exemplos).
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DASHBOARD = RAIZ / "dashboard"
TEMPLATES = RAIZ / "templates"
FONTES = TEMPLATES / "fonts"
EXEMPLOS = RAIZ / "exemplos"


def dados() -> Path:
    return Path(os.environ.get("RADAR_DADOS") or RAIZ / "meus-dados").resolve()


def vagas() -> Path:
    return dados() / "vagas.json"


def registro() -> Path:
    return dados() / "registro.json"


def config() -> Path:
    return dados() / "config.json"


def buscas() -> Path:
    return dados() / "buscas.json"


def perfil() -> Path:
    return dados() / "perfil.json"


def fatos() -> Path:
    return dados() / "fatos.md"


def decisoes() -> Path:
    return dados() / "decisoes.json"


def cvs() -> Path:
    return dados() / "cvs"


def arquivo() -> Path:
    return dados() / "arquivo"


def varredura() -> Path:
    return dados() / "varredura"


def painel() -> Path:
    """O dashboard gerado (com os seus dados dentro) vive aqui, nunca em dashboard/."""
    return dados() / "painel"
