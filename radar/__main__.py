"""Linha de comando do Radar de Vagas. Use pelo wrapper: bin/radar <comando>.

Comandos:
  (nenhum) ou abrir [--porta N] abre o Radar no navegador; na primeira vez, a tela de
                                abertura com o passo a passo de contexto
  init                          cria meus-dados/ (rode uma vez)
  demo [--porta 8323]           painel com dados fictícios, sem configurar nada
  perfil importar <zip|pasta>   importa o export oficial do LinkedIn
  perfil pdf <arquivo.pdf>      extrai o texto do "Salvar em PDF" do seu perfil
  varrer coleta [--horas N]     coleta vagas pelo endpoint público
  varrer filtra [--entrada F]   corta título, janela e duplicatas -> candidatas.json
  varrer descricao <id>...      baixa a descrição de cada vaga
  varrer checa <id>...          confere se a vaga ainda aceita candidaturas
  validar                       confere esquemas e consistência dos dados
  marcar <id> <status>          muda status com trava (proposto, aprovado, executado...)
  proximo-id vaga|pessoa        próximo id livre
  expirar [--dias N] [--aplicar]  tira da mesa a triagem parada
  arquivar                      fecha a leva corrente
  gerar                         regenera o painel (meus-dados/painel/index.html)
  painel [--porta N]            sobe o painel com botões ao vivo
  cv <conteudo.json> <saida.pdf>
  carta <carta.md> <saida.pdf>

Variável RADAR_DADOS: aponta para outra pasta de dados (padrão: meus-dados/).
"""

import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar", description="Radar de Vagas",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="cmd")

    ab = sub.add_parser("abrir")
    ab.add_argument("--porta", type=int)
    ab.add_argument("--sem-navegador", action="store_true")
    sub.add_parser("init")
    d = sub.add_parser("demo")
    d.add_argument("--porta", type=int, default=8323)

    pf = sub.add_parser("perfil").add_subparsers(dest="acao", required=True)
    imp = pf.add_parser("importar")
    imp.add_argument("origem", type=Path)
    imp.add_argument("--sobrescrever", action="store_true")
    pf.add_parser("pdf").add_argument("arquivo", type=Path)

    vr = sub.add_parser("varrer").add_subparsers(dest="acao", required=True)
    co = vr.add_parser("coleta")
    co.add_argument("--horas", type=int)
    co.add_argument("--saida", type=Path)
    fi = vr.add_parser("filtra")
    fi.add_argument("--entrada", type=Path)
    fi.add_argument("--saida", type=Path)
    de = vr.add_parser("descricao")
    de.add_argument("ids", nargs="+")
    de.add_argument("--pasta", type=Path)
    ch = vr.add_parser("checa")
    ch.add_argument("ids", nargs="+")
    ch.add_argument("--saida", type=Path)

    sub.add_parser("validar")
    m = sub.add_parser("marcar")
    m.add_argument("id")
    m.add_argument("status")
    m.add_argument("--nota", default="")
    sub.add_parser("proximo-id").add_argument("grupo", choices=["vaga", "pessoa"])
    ex = sub.add_parser("expirar")
    ex.add_argument("--dias", type=int)
    ex.add_argument("--aplicar", action="store_true")
    sub.add_parser("arquivar")
    sub.add_parser("gerar")
    pn = sub.add_parser("painel")
    pn.add_argument("--porta", type=int)
    for nome in ("cv", "carta"):
        c = sub.add_parser(nome)
        c.add_argument("entrada", type=Path)
        c.add_argument("saida", type=Path)

    a = p.parse_args(argv)

    if a.cmd in (None, "abrir"):
        from . import caminhos, config, contexto
        from .inicio import abertura_terminal, init
        if not caminhos.config().exists():
            init(silencioso=True)
        porta = getattr(a, "porta", None) or config.carregar()["painel"]["porta"]
        if contexto.primeira_vez():
            abertura_terminal(porta)
        from .servidor import servir
        servir(porta, abrir=not getattr(a, "sem_navegador", False))
    elif a.cmd == "init":
        from .inicio import init
        init()
    elif a.cmd == "demo":
        from .inicio import preparar_demo
        pasta = preparar_demo()
        print(f"Demo em {pasta} (dados fictícios, datas trazidas para hoje)")
        from .servidor import servir
        servir(a.porta)
    elif a.cmd == "perfil":
        from . import perfil
        perfil.importar(a.origem, a.sobrescrever) if a.acao == "importar" else perfil.pdf(a.arquivo)
    elif a.cmd == "varrer":
        from . import config, varredura
        pasta = varredura.pasta_do_dia()
        if a.acao == "coleta":
            horas = a.horas or config.carregar()["rotina"]["janela_horas"]
            varredura.coleta(horas, a.saida or pasta / "coleta.json")
        elif a.acao == "filtra":
            varredura.filtra(a.entrada or pasta / "coleta.json", a.saida or pasta / "candidatas.json")
        elif a.acao == "descricao":
            varredura.descricao(a.ids, a.pasta or pasta / "descricoes")
        else:
            varredura.checa(a.ids, a.saida or pasta / "checa.json")
    elif a.cmd == "validar":
        from . import validar
        return validar.main()
    elif a.cmd == "marcar":
        from .manutencao import marcar
        marcar(a.id, a.status, a.nota)
    elif a.cmd == "proximo-id":
        from .manutencao import proximo
        print(proximo(a.grupo))
    elif a.cmd == "expirar":
        from .manutencao import expirar
        expirar(a.dias, a.aplicar)
    elif a.cmd == "arquivar":
        from .manutencao import arquivar
        arquivar()
    elif a.cmd == "gerar":
        from . import gerar_dados
        gerar_dados.main()
    elif a.cmd == "painel":
        from .servidor import servir
        servir(a.porta)
    elif a.cmd == "cv":
        from . import cv
        return cv.gerar(a.entrada, a.saida)
    elif a.cmd == "carta":
        from . import carta
        return carta.gerar(a.entrada, a.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
