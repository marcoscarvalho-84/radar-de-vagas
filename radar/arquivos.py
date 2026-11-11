"""Leitura e escrita dos JSONs com trava e gravação atômica.

Dois escritores disputam os mesmos arquivos: o servidor do dashboard (um clique) e a
sessão do Claude (a rotina). Sem trava, um sobrescreve o outro e a decisão some sem
aviso; sem gravação atômica, um processo pode ler um JSON pela metade. Toda escrita do
Radar passa por `editar_json`, que faz as duas coisas.
"""

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl  # macOS e Linux
except ImportError:  # Windows: cai na trava por arquivo exclusivo
    fcntl = None


@contextmanager
def trava(pasta: Path, espera: float = 15.0):
    """Trava exclusiva por pasta de dados. Reentrante não é: não aninhe."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / ".radar.lock"
    if fcntl:
        with open(caminho, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return
    limite = time.monotonic() + espera
    while True:
        try:
            fd = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() > limite:
                raise TimeoutError(f"trava presa em {caminho}; apague o arquivo se nenhum processo estiver rodando")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(fd)
        os.unlink(caminho)


def ler_json(caminho: Path, padrao=None):
    if not caminho.exists():
        return padrao
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_json(caminho: Path, dados) -> None:
    """Grava num temporário da mesma pasta e troca de uma vez (os.replace é atômico)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="." + caminho.name, dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, caminho)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


@contextmanager
def editar_json(caminho: Path, padrao):
    """Lê, entrega para edição e grava, tudo sob a trava da pasta.

        with editar_json(caminhos.vagas(), {"vagas": [], "pessoas": []}) as dados:
            dados["vagas"].append(...)
    """
    with trava(caminho.parent):
        dados = ler_json(caminho, padrao)
        yield dados
        gravar_json(caminho, dados)
