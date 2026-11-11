"""Servidor local do dashboard: transforma os botões em ações reais.

    bin/radar painel            (Ctrl+C para parar)

- GET  /                 o painel (regerado na hora se algum JSON mudou)
- GET  /cvs/...          PDFs e previews de meus-dados/cvs
- GET  /api/vagas        o vagas.json atual
- POST /api/decisao      {"id": "vaga-1", "acao": "aprovar|aprofundar|ajustar|pular", "nota": ""}
                         {"id": "busca", "acao": "nova_busca"}

Cada decisão (1) muda o status do item em vagas.json, (2) entra na fila decisoes.json,
consumida pela sessão do Claude, e (3) regenera o painel. Aprovar no painel NUNCA envia
nada: a rotina ainda pede um ok final na conversa antes de qualquer ação pública.

Segurança, porque o servidor escreve em disco a partir de um POST:
- escuta só em 127.0.0.1;
- recusa Host diferente de localhost/127.0.0.1 na porta certa (DNS rebinding);
- recusa POST sem Content-Type application/json e com Origin de outro site. Um site
  qualquer aberto no navegador consegue disparar um POST "simples" (text/plain) para
  localhost sem preflight; com estas duas checagens, não consegue;
- não manda Access-Control-Allow-Origin: o painel é servido pelo próprio servidor.
"""

import json
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import caminhos, config, gerar_dados
from .arquivos import gravar_json, ler_json, trava

FUSO = timezone(timedelta(hours=-3))
GRUPOS = {"vaga": "vagas", "pessoa": "pessoas"}
STATUS = {"aprovar": "aprovado", "aprofundar": "aprofundar", "ajustar": "ajuste", "pular": "recusado"}
LIMITE_CORPO = 64 * 1024


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
        if self.path == "/api/vagas":
            self._json(ler_json(caminhos.vagas(), {}) or {})
            return
        if self.path.split("?", 1)[0] in ("/", "/index.html") and gerar_dados.desatualizado():
            _regerar()
        super().do_GET()

    def do_POST(self):
        if not self._host_ok() or not self._origem_ok():
            self._json({"ok": False, "erro": "origem recusada"}, 403)
            return
        if self.path != "/api/decisao":
            self._json({"ok": False, "erro": "rota desconhecida"}, 404)
            return
        if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
            self._json({"ok": False, "erro": "Content-Type precisa ser application/json"}, 415)
            return
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0 or tamanho > LIMITE_CORPO:
            self._json({"ok": False, "erro": "corpo vazio ou grande demais"}, 400)
            return
        try:
            resultado = aplicar_decisao(json.loads(self.rfile.read(tamanho).decode("utf-8")))
        except Exception as e:  # nunca derrubar o servidor por um clique
            resultado = {"ok": False, "erro": str(e)}
        self._json(resultado, 200 if resultado.get("ok") else 400)


def servir(porta: int | None = None) -> None:
    porta = porta or config.carregar()["painel"]["porta"]
    _regerar()
    Handler.porta = porta
    handler = partial(Handler, directory=str(caminhos.painel()))
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), handler)
    print(f"Radar de Vagas em http://localhost:{porta}  (dados: {caminhos.dados()})  Ctrl+C para parar")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
