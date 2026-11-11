"""Operações de manutenção do Radar, todas sob trava e gravação atômica.

    bin/radar marcar <id> <status> [--nota "..."]   muda o status de uma vaga ou pessoa
    bin/radar proximo-id vaga|pessoa                o próximo id livre (max+1)
    bin/radar expirar [--dias N] [--aplicar]        triagem parada há N dias sai da mesa
    bin/radar arquivar                              fecha a leva corrente em arquivo/leva-N

A sessão do Claude usa estes comandos em vez de editar os JSONs à mão quando o painel
pode estar aberto: é o que evita que um clique e uma edição se atropelem.
"""

import shutil
from datetime import date, datetime, timedelta

from . import caminhos, config
from .arquivos import editar_json, gravar_json, ler_json, trava
from .ids import numero, proximo_id
from .servidor import FUSO, STATUS
from .validar import STATUS_VAGA

PADRAO = {"vagas": [], "pessoas": []}


def marcar(id_: str, status: str, nota: str = "") -> dict:
    if status not in STATUS_VAGA:
        raise SystemExit(f"status inválido: {status} (use {', '.join(sorted(STATUS_VAGA))})")
    grupo = "vagas" if id_.startswith("vaga-") else "pessoas" if id_.startswith("pessoa-") else None
    if not grupo:
        raise SystemExit(f"id desconhecido: {id_}")
    with editar_json(caminhos.vagas(), PADRAO) as dados:
        item = next((x for x in dados.get(grupo, []) if x.get("id") == id_), None)
        if item is None:
            raise SystemExit(f"{id_} não está em {caminhos.vagas()}")
        item["status"] = status
        if status == "aprovado":
            item["aprovado_em"] = datetime.now(FUSO).isoformat(timespec="seconds")
        if status == "ajuste" and nota:
            item["nota_ajuste"] = nota
        if status == "recusado" and nota:
            item["motivo"] = nota
    print(f"{id_} -> {status}")
    return item


def proximo(grupo: str) -> str:
    """Considera também as levas arquivadas, para um id nunca voltar a existir."""
    dados = ler_json(caminhos.vagas(), PADRAO) or PADRAO
    lista = dados.get("vagas" if grupo == "vaga" else "pessoas", [])
    piso = 0
    for pasta in caminhos.arquivo().glob("leva-*"):
        antigos = (ler_json(pasta / "vagas.json", PADRAO) or PADRAO).get("vagas" if grupo == "vaga" else "pessoas", [])
        piso = max([piso] + [numero(x.get("id")) for x in antigos])
    return proximo_id(lista, grupo, piso)


def expirar(dias: int | None = None, aplicar: bool = False) -> list:
    dias = dias or config.carregar()["rotina"]["triagem_expira_dias"]
    limite = (date.today() - timedelta(days=dias)).isoformat()
    vencidas = []
    with editar_json(caminhos.vagas(), PADRAO) as dados:
        for v in dados.get("vagas", []):
            if (v.get("profundidade") == "triagem" and v.get("status") == "proposto"
                    and v.get("adicionada_em") and v["adicionada_em"] <= limite):
                vencidas.append(v)
                if aplicar:
                    v["status"] = "recusado"
                    v["motivo"] = f"expirou na triagem ({dias} dias sem decisão)"
    for v in vencidas:
        print(f"{v['id']}  entrou {v['adicionada_em']}  {v['empresa']} · {v['cargo']}")
    if vencidas and not aplicar:
        print(f"{len(vencidas)} vaga(s) de triagem com {dias}+ dias. Nada mudou: rode com --aplicar para tirar da mesa.")
    elif not vencidas:
        print("Nenhuma triagem vencida.")
    return vencidas


def arquivar() -> str:
    """Fecha a leva: copia registro e vagas para arquivo/leva-N e recomeça vazio.

    O arquivo continua valendo para checagem de duplicata e para reabrir uma vaga se a
    empresa responder depois.
    """
    with trava(caminhos.dados()):
        existentes = [numero(p.name) for p in caminhos.arquivo().glob("leva-*")]
        n = max(existentes + [0]) + 1
        destino = caminhos.arquivo() / f"leva-{n}"
        destino.mkdir(parents=True)
        for f in (caminhos.vagas(), caminhos.registro()):
            if f.exists():
                shutil.copy2(f, destino / f.name)
        registro = ler_json(caminhos.registro(), {}) or {}
        vagas = sum(len(d.get("vagas", [])) for d in registro.get("dias", []))
        (destino / "RELATORIO.md").write_text(
            f"# Leva {n}, arquivada em {date.today().isoformat()}\n\n"
            f"- {vagas} vagas registradas no histórico\n"
            f"- Escreva aqui a leitura honesta da leva: o que funcionou, o que travou, o que muda.\n",
            encoding="utf-8")
        gravar_json(caminhos.vagas(), {"data": "", "vagas": [], "pessoas": []})
        gravar_json(caminhos.registro(), {"leva": n + 1, "leva_inicio": date.today().isoformat(), "dias": []})
        gravar_json(caminhos.decisoes(), {"decisoes": []})
    print(f"Leva {n} arquivada em {destino}. A leva {n + 1} começa vazia.")
    return str(destino)


# o servidor e a manutenção falam o mesmo vocabulário de ação -> status
assert set(STATUS.values()) <= STATUS_VAGA
