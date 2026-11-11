"""Configuração do usuário, com padrões para o que ele ainda não respondeu.

Os padrões aqui cobrem só a mecânica (prazos, porta do painel, pesos de fit). Nada que
seja decisão pessoal tem padrão: pretensão, disponibilidade e autorização de trabalho
vazias significam PERGUNTAR, nunca chutar.
"""

import copy

from . import caminhos
from .arquivos import ler_json

PADRAO = {
    "fit": {
        "pesos": {"dominio": 25, "senioridade": 20, "porta": 20, "escopo": 20, "modelo": 15},
        "fit_minimo_para_aprofundar": 60,
        "vagas_trabalhadas_por_dia": 2,
    },
    "pessoas": {"por_vaga": 3},
    "rotina": {
        "janela_horas": 48,
        "follow_up_dias": 7,
        "triagem_expira_dias": 14,
        "aprovado_alerta_dias": 3,
    },
    "painel": {"porta": 8322},
}


def _mesclar(base: dict, por_cima: dict) -> dict:
    saida = copy.deepcopy(base)
    for k, v in (por_cima or {}).items():
        if isinstance(v, dict) and isinstance(saida.get(k), dict):
            saida[k] = _mesclar(saida[k], v)
        else:
            saida[k] = v
    return saida


def carregar() -> dict:
    return _mesclar(PADRAO, ler_json(caminhos.config(), {}) or {})


def para_painel(cfg: dict, perfil: dict) -> dict:
    """O pedaço do config que o dashboard precisa ver.

    O dashboard vira um HTML com os dados embutidos; pretensão, telefone e o resto do
    config não têm por que ir parar lá dentro.
    """
    rem = cfg.get("remuneracao", {})
    contatos = (perfil or {}).get("contatos", {})
    return {
        "nome": (perfil or {}).get("nome", ""),
        "links": {"linkedin": contatos.get("linkedin", ""), "portfolio": contatos.get("portfolio", "")},
        "follow_up_dias": cfg["rotina"]["follow_up_dias"],
        "aprovado_alerta_dias": cfg["rotina"]["aprovado_alerta_dias"],
        "triagem_expira_dias": cfg["rotina"]["triagem_expira_dias"],
        "pretensao_definida": any(rem.get(k) for k in ("clt_mensal", "pj_mensal", "usd_anual", "regra")),
    }
