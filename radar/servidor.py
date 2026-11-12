"""Servidor local do dashboard: transforma os botões em ações reais.

    bin/radar painel            (Ctrl+C para parar)

- GET  /                 o painel (regerado na hora se algum JSON mudou); na primeira vez,
                         redireciona para a tela de abertura
- GET  /boas-vindas      a tela de abertura e o passo a passo de contexto
- GET  /cvs/...          PDFs e previews de meus-dados/cvs
- GET  /api/vagas        o vagas.json atual
- GET  /api/contexto     o estado dos 6 passos (LinkedIn, CV, posições, e-mail, portfólio, anexos)
- POST /api/decisao      {"id": "vaga-1", "acao": "aprovar|aprofundar|ajustar|pular", "nota": ""}
                         {"id": "busca", "acao": "nova_busca"}
- POST /api/contexto     {"acao": "salvar", "campos": {...}} | {"acao": "pular", "passo": "cv"}
                         {"acao": "remover", "arquivo": "anexos/x.pdf"} | {"acao": "concluir"}
                         {"acao": "comentar", "arquivo": "anexos/x.pdf", "comentario": ""}
- POST /api/arquivo      corpo = o arquivo cru (application/octet-stream), com os cabeçalhos
                         X-Radar-Tipo (linkedin|cv|anexo), X-Radar-Nome

Cada decisão (1) muda o status do item em vagas.json, (2) entra na fila decisoes.json,
consumida pela sessão do Claude, e (3) regenera o painel. Aprovar no painel NUNCA envia
nada: a rotina ainda pede um ok final na conversa antes de qualquer ação pública.

Segurança, porque o servidor escreve em disco a partir de um POST:
- escuta só em 127.0.0.1;
- recusa Host diferente de localhost/127.0.0.1 na porta certa (DNS rebinding);
- recusa POST com Origin de outro site e com Content-Type "simples". Um site qualquer
  aberto no navegador consegue disparar um POST text/plain ou de formulário para
  localhost sem preflight; JSON e octet-stream (mais os cabeçalhos X-Radar-*) exigem
  preflight, que este servidor nunca autoriza;
- arquivo enviado só cai em meus-dados/anexos, com nome refeito e os primeiros bytes
  conferidos contra a extensão;
- não manda Access-Control-Allow-Origin: o painel é servido pelo próprio servidor.
"""

import json
import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from . import caminhos, config, contexto, gerar_dados
from .arquivos import gravar_json, ler_json, trava

FUSO = timezone(timedelta(hours=-3))
GRUPOS = {"vaga": "vagas", "pessoa": "pessoas"}
STATUS = {"aprovar": "aprovado", "aprofundar": "aprofundar", "ajustar": "ajuste", "pular": "recusado"}
LIMITE_CORPO = 64 * 1024
# a tela de abertura é servida direto do modelo: não leva dado nenhum dentro
ABERTURA = {"/boas-vindas": "boas-vindas.html", "/boas-vindas.html": "boas-vindas.html",
            "/boas-vindas.css": "boas-vindas.css", "/radar-3d.js": "radar-3d.js",
            "/vendor/three.module.min.js": "vendor/three.module.min.js"}


def agora() -> str:
    return datetime.now(FUSO).isoformat(timespec="seconds")


def _regerar() -> None:
    try:
        gerar_dados.gerar()
    except SystemExit:
        pass


def aplicar_decisao(decisao: dict) -> dict:
    id_ = str(decisao.get("id", ""))
    acao = str(decisao.get("acao", ""))
    nota = str(decisao.get("nota", "") or "").strip()[:2000]
    padrao = {"vagas": [], "pessoas": []}

    # Ação global: descarta a triagem do dia e pede uma varredura nova
    if acao == "nova_busca":
        # vagas.json e decisoes.json mudam juntos, sob a mesma trava da pasta
        with trava(caminhos.dados()):
            dados = ler_json(caminhos.vagas(), padrao) or padrao
            for vaga in dados.get("vagas", []):
                if vaga.get("profundidade") == "triagem" and vaga.get("status") in ("proposto", "ajuste"):
                    vaga["status"] = "recusado"
            gravar_json(caminhos.vagas(), dados)
            fila = ler_json(caminhos.decisoes(), {"decisoes": []}) or {"decisoes": []}
            fila["decisoes"].append({"id": "busca", "acao": "nova_busca", "nota": nota, "em": agora()})
            gravar_json(caminhos.decisoes(), fila)
        _regerar()
        return {"ok": True, "id": "busca", "status": "nova_busca"}

    if acao not in STATUS:
        return {"ok": False, "erro": f"ação desconhecida: {acao}"}
    grupo = GRUPOS.get(id_.rsplit("-", 1)[0])
    if not grupo:
        return {"ok": False, "erro": f"id desconhecido: {id_}"}
    if acao == "ajustar" and not nota:
        return {"ok": False, "erro": "ajuste sem nota"}

    with trava(caminhos.dados()):
        dados = ler_json(caminhos.vagas(), padrao) or padrao
        item = next((x for x in dados.get(grupo, []) if x.get("id") == id_), None)
        if item is None:
            return {"ok": False, "erro": f"item não encontrado: {id_}"}
        item["status"] = STATUS[acao]
        if acao == "ajustar":
            item["nota_ajuste"] = nota
        if acao == "aprovar":
            item["aprovado_em"] = agora()
        gravar_json(caminhos.vagas(), dados)
        fila = ler_json(caminhos.decisoes(), {"decisoes": []}) or {"decisoes": []}
        fila["decisoes"].append({"id": id_, "acao": acao, "nota": nota, "em": agora()})
        gravar_json(caminhos.decisoes(), fila)

    _regerar()
    return {"ok": True, "id": id_, "status": STATUS[acao]}


def aplicar_contexto(pedido: dict) -> dict:
    acao = str(pedido.get("acao", ""))
    try:
        if acao == "salvar":
            campos = pedido.get("campos")
            if not isinstance(campos, dict):
                return {"ok": False, "erro": "campos ausentes"}
            resultado = contexto.salvar(campos)
        elif acao == "pular":
            resultado = contexto.pular(str(pedido.get("passo", "")))
        elif acao == "remover":
            resultado = contexto.remover(str(pedido.get("arquivo", "")))
        elif acao == "comentar":
            resultado = contexto.comentar(str(pedido.get("arquivo", "")), str(pedido.get("comentario", "")))
        elif acao == "concluir":
            resultado = contexto.concluir()
        else:
            return {"ok": False, "erro": f"ação desconhecida: {acao}"}
    except contexto.ContextoInvalido as e:
        return {"ok": False, "erro": str(e)}
    _regerar()  # o rodapé do painel mostra os links do perfil
    return resultado


class Handler(SimpleHTTPRequestHandler):
    porta = 8322

    def log_message(self, *args):  # silencioso
        pass

    def end_headers(self):
        # o painel é regerado o tempo todo; cache aqui só faz olhar uma versão velha
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def _hosts_validos(self):
        return {f"localhost:{self.porta}", f"127.0.0.1:{self.porta}"}

    def _host_ok(self) -> bool:
        return (self.headers.get("Host") or "").lower() in self._hosts_validos()

    def _origem_ok(self) -> bool:
        origem = self.headers.get("Origin")
        if origem is None:
            return True  # navegadores mandam Origin em POST cross-site; curl local não manda
        return origem.lower() in {f"http://{h}" for h in self._hosts_validos()}

    def translate_path(self, path):
        limpo = path.split("?", 1)[0].split("#", 1)[0]
        if limpo in ABERTURA:
            return str(caminhos.DASHBOARD / ABERTURA[limpo])
        if limpo.startswith("/cvs/"):
            base = caminhos.cvs().resolve()
            alvo = (base / limpo[len("/cvs/"):].lstrip("/")).resolve()
            if base in alvo.parents:
                return str(alvo)
            return str(base / "__fora__")  # tentativa de escapar da pasta: 404
        return super().translate_path(path)

    def list_directory(self, path):
        self.send_error(404)  # nunca listar pastas
        return None

    def _json(self, corpo: dict, status: int = 200) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if not self._host_ok():
            self.send_error(403)
            return
        rota = self.path.split("?", 1)[0]
        if rota == "/api/vagas":
            self._json(ler_json(caminhos.vagas(), {}) or {})
            return
        if rota == "/api/contexto":
            self._json(contexto.estado())
            return
        if rota in ("/", "/index.html"):
            if contexto.primeira_vez():
                self.send_response(302)
                self.send_header("Location", "/boas-vindas")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if gerar_dados.desatualizado():
                _regerar()
        super().do_GET()

    def _tipo(self) -> str:
        return (self.headers.get("Content-Type") or "").lower().split(";", 1)[0].strip()

    def _tamanho(self, limite: int) -> int | None:
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            tamanho = 0
        if tamanho <= 0 or tamanho > limite:
            self._json({"ok": False, "erro": "corpo vazio ou grande demais"}, 413 if tamanho > limite else 400)
            return None
        return tamanho

    def do_POST(self):
        if not self._host_ok() or not self._origem_ok():
            self._json({"ok": False, "erro": "origem recusada"}, 403)
            return
        if self.path == "/api/arquivo":
            self._receber_arquivo()
            return
        if self.path not in ("/api/decisao", "/api/contexto"):
            self._json({"ok": False, "erro": "rota desconhecida"}, 404)
            return
        if self._tipo() != "application/json":
            self._json({"ok": False, "erro": "Content-Type precisa ser application/json"}, 415)
            return
        tamanho = self._tamanho(LIMITE_CORPO)
        if tamanho is None:
            return
        try:
            pedido = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            if self.path == "/api/decisao":
                resultado = aplicar_decisao(pedido)
            else:
                resultado = aplicar_contexto(pedido)
        except Exception as e:  # nunca derrubar o servidor por um clique
            resultado = {"ok": False, "erro": str(e)}
        self._json(resultado, 200 if resultado.get("ok") else 400)

    def _drenar(self) -> None:
        """Recusa antes de ler o corpo: lê e descarta o que couber, senão o navegador vê
        a conexão cortada no meio do envio em vez da mensagem de erro."""
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return
        if 0 < tamanho <= contexto.LIMITE_ARQUIVO:
            self.rfile.read(tamanho)

    def _receber_arquivo(self):
        if self._tipo() != "application/octet-stream":
            self._drenar()
            self._json({"ok": False, "erro": "Content-Type precisa ser application/octet-stream"}, 415)
            return
        tipo = self.headers.get("X-Radar-Tipo") or ""
        if tipo not in contexto.ACEITOS:
            self._drenar()
            self._json({"ok": False, "erro": "X-Radar-Tipo precisa ser linkedin, cv ou anexo"}, 400)
            return
        tamanho = self._tamanho(contexto.LIMITE_ARQUIVO)
        if tamanho is None:
            return
        conteudo = self.rfile.read(tamanho)
        try:
            resultado = contexto.receber(
                tipo,
                unquote(self.headers.get("X-Radar-Nome") or ""),
                conteudo,
            )
        except contexto.ContextoInvalido as e:
            resultado = {"ok": False, "erro": str(e)}
        except Exception as e:
            resultado = {"ok": False, "erro": f"não consegui guardar o arquivo: {e}"}
        if resultado.get("ok"):
            _regerar()
        self._json(resultado, 200 if resultado.get("ok") else 400)


def servir(porta: int | None = None, abrir: bool = False) -> None:
    porta = porta or config.carregar()["painel"]["porta"]
    _regerar()
    Handler.porta = porta
    handler = partial(Handler, directory=str(caminhos.painel()))
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), handler)
    print(f"Radar de Vagas em http://localhost:{porta}  (dados: {caminhos.dados()})  Ctrl+C para parar", flush=True)
    if abrir:
        rota = "/boas-vindas" if contexto.primeira_vez() else "/"
        # o navegador abre com um atraso curto: o servidor já está escutando quando a página pede
        threading.Timer(0.4, webbrowser.open, args=(f"http://localhost:{porta}{rota}",)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
