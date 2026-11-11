"""Ids sequenciais por grupo (vaga-N, pessoa-N).

Sempre max+1 sobre os ids existentes, nunca len(lista)+1: quando itens são apagados ou
arquivados, o tamanho da lista volta a um número já usado e nascem dois `vaga-12`. As
decisões do dashboard apontam para o id, então id duplicado é decisão no item errado.
O piso serve para uma leva nova nunca colidir com ids de levas arquivadas.
"""

import re


def numero(id_: str) -> int:
    m = re.search(r"(\d+)$", str(id_ or ""))
    return int(m.group(1)) if m else 0


def proximo_id(itens, prefixo: str, piso: int = 0) -> str:
    maior = max([numero(x.get("id")) for x in itens if str(x.get("id", "")).startswith(prefixo + "-")] + [piso])
    return f"{prefixo}-{maior + 1}"
