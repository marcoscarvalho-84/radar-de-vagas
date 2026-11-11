"""Coleta do seu perfil do LinkedIn, pelos caminhos que não violam os termos do site.

    bin/radar perfil importar <export.zip | pasta>   # "Obter uma cópia dos seus dados"
    bin/radar perfil pdf <Profile.pdf>                # "Salvar em PDF" do seu perfil

1. Export oficial (recomendado): LinkedIn > Configurações > Privacidade dos dados >
   Obter uma cópia dos seus dados. O ZIP traz CSVs; daqui só se leem os do PERFIL
   (Profile, Positions, Education, Skills, Languages, Certifications, Email Addresses).
   Conexões, mensagens e convites nunca são abertos: não servem ao CV e são dados de
   terceiros.
2. PDF do perfil: extrai o texto bruto para meus-dados/perfil-bruto.txt; a skill
   /radar-perfil estrutura com você, item a item.

O resultado é um RASCUNHO. Fato só vira prova citável no CV depois que você confirma
(campo `provas` e o arquivo fatos.md), e o questionário completa o resto.
"""

import csv
import io
import re
import zipfile
from datetime import date
from pathlib import Path

from . import caminhos
from .arquivos import gravar_json, ler_json

ARQUIVOS = {
    "Profile.csv", "Positions.csv", "Education.csv", "Skills.csv",
    "Languages.csv", "Certifications.csv", "Email Addresses.csv",
}
MESES = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MESES.update({"fev": 2, "abr": 4, "mai": 5, "ago": 8, "set": 9, "out": 10, "dez": 12})


def _ler_csvs(origem: Path) -> dict[str, list[dict]]:
    """Lê só os CSVs de perfil, de um ZIP ou de uma pasta já extraída."""
    textos = {}
    if origem.is_file() and zipfile.is_zipfile(origem):
        with zipfile.ZipFile(origem) as z:
            for nome in z.namelist():
                base = nome.rsplit("/", 1)[-1]
                if base in ARQUIVOS:
                    textos[base] = z.read(nome).decode("utf-8-sig", "replace")
    elif origem.is_dir():
        for f in origem.rglob("*.csv"):
            if f.name in ARQUIVOS:
                textos[f.name] = f.read_text(encoding="utf-8-sig", errors="replace")
    else:
        raise SystemExit(f"Não achei um ZIP nem uma pasta em {origem}")
    if not textos:
        raise SystemExit("Nenhum CSV de perfil encontrado. Confira se é o export de dados do LinkedIn.")
    return {nome: _linhas(texto) for nome, texto in textos.items()}


def _linhas(texto: str) -> list[dict]:
    """Alguns CSVs do export começam com parágrafos de 'Notes:' antes do cabeçalho."""
    linhas = texto.splitlines()
    inicio = next((i for i, l in enumerate(linhas) if "," in l and not l.lower().startswith("notes")), 0)
    return list(csv.DictReader(io.StringIO("\n".join(linhas[inicio:]))))


def _data(valor: str) -> str:
    """'Mar 2021' -> '2021-03'; '2021' -> '2021'; vazio -> ''."""
    valor = (valor or "").strip()
    m = re.match(r"([A-Za-zç]{3})\w*\.?\s+(\d{4})", valor)
    if m and m.group(1).lower()[:3] in MESES:
        return f"{m.group(2)}-{MESES[m.group(1).lower()[:3]]:02d}"
    m = re.search(r"(\d{4})", valor)
    return m.group(1) if m else ""


def montar(csvs: dict[str, list[dict]]) -> dict:
    p = (csvs.get("Profile.csv") or [{}])[0]
    nome = " ".join(x for x in (p.get("First Name", "").strip(), p.get("Last Name", "").strip()) if x)
    emails = csvs.get("Email Addresses.csv", [])
    principal = next((e for e in emails if (e.get("Primary") or "").lower() == "yes"), emails[0] if emails else {})
    sites = [s.strip() for s in re.split(r"[,\n]", p.get("Websites", "")) if s.strip()]

    experiencias = [{
        "empresa": x.get("Company Name", "").strip(),
        "cargo": x.get("Title", "").strip(),
        "inicio": _data(x.get("Started On")),
        "fim": _data(x.get("Finished On")) or "atual",
        "local": x.get("Location", "").strip(),
        "descricao": x.get("Description", "").strip(),
    } for x in csvs.get("Positions.csv", [])]

    return {
        "_leia": "Rascunho importado do export do LinkedIn. Confirme com /radar-perfil antes de usar como fato.",
        "nome": nome,
        "nome_cv": nome.split(" ", 1) if " " in nome else [nome],
        "headline": p.get("Headline", "").strip(),
        "resumo": p.get("Summary", "").strip(),
        "local": p.get("Geo Location", "").strip(),
        "contatos": {
            "email": (principal or {}).get("Email Address", "").strip(),
            "telefone": "",
            "linkedin": "",
            "portfolio": sites[0] if sites else "",
        },
        "idiomas": [{"idioma": x.get("Name", "").strip(), "nivel": x.get("Proficiency", "").strip()}
                    for x in csvs.get("Languages.csv", [])],
        "formacao": [{
            "instituicao": x.get("School Name", "").strip(),
            "curso": " · ".join(y for y in (x.get("Degree Name", "").strip(), x.get("Notes", "").strip()) if y),
            "inicio": _data(x.get("Start Date")),
            "fim": _data(x.get("End Date")),
        } for x in csvs.get("Education.csv", [])],
        "experiencias": experiencias,
        "competencias": [x.get("Name", "").strip() for x in csvs.get("Skills.csv", []) if x.get("Name")],
        "certificacoes": [{"nome": x.get("Name", "").strip(), "emissor": x.get("Authority", "").strip(),
                           "inicio": _data(x.get("Started On"))} for x in csvs.get("Certifications.csv", [])],
        "provas": [],
        "fonte": {"importado_de": "linkedin-export", "em": date.today().isoformat()},
    }


def importar(origem: Path, sobrescrever: bool = False) -> Path:
    perfil = montar(_ler_csvs(origem))
    destino = caminhos.perfil()
    if destino.exists() and not sobrescrever:
        destino = destino.with_name("perfil.importado.json")
        print(f"Já existe um perfil.json; o import foi para {destino.name} para você comparar.")
    gravar_json(destino, perfil)
    print(f"{len(perfil['experiencias'])} experiências, {len(perfil['formacao'])} formações, "
          f"{len(perfil['competencias'])} competências -> {destino}")
    faltando = [c for c in ("nome", "headline", "resumo") if not perfil[c]]
    if faltando:
        print("Vazio no export (o questionário pergunta):", ", ".join(faltando))
    return destino


def pdf(arquivo: Path) -> Path:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("Falta o pypdf: rode bin/instalar")
    texto = "\n".join((pagina.extract_text() or "") for pagina in PdfReader(str(arquivo)).pages)
    destino = caminhos.dados() / "perfil-bruto.txt"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(f"{len(texto)} caracteres -> {destino}. Agora rode /radar-perfil para estruturar.")
    return destino


def resumo() -> str:
    p = ler_json(caminhos.perfil(), {}) or {}
    if not p:
        return "Sem perfil ainda."
    return (f"{p.get('nome') or '(sem nome)'} · {len(p.get('experiencias', []))} experiências · "
            f"{len(p.get('provas', []))} provas confirmadas")
