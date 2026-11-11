# Esquemas de dados

Todos os arquivos ficam em `meus-dados/` (ou na pasta de `RADAR_DADOS`). Exemplos completos e
fictícios em `exemplos/`. `bin/radar validar` confere estas regras.

## vagas.json: a mesa, o que aguarda decisão

```json
{
  "data": "AAAA-MM-DD",
  "gerado_em": "ISO com fuso",
  "resumo_busca": "6 palavras-chave, 212 vagas em 48h, 9 lidas, 3 cortadas na triagem",
  "vagas": [{
    "id": "vaga-1",
    "empresa": "", "cargo": "", "url": "https://www.linkedin.com/jobs/view/{id}",
    "local": "", "modelo": "remoto|híbrido|presencial",
    "porta": "id de config.objetivo.portas",
    "profundidade": "triagem|completa",
    "adicionada_em": "AAAA-MM-DD",
    "fit": 84, "fit_resumo": "uma frase honesta", "red_flags": [],
    "salario": "", "salario_fonte": "publicada na vaga | estimativa <fonte>",
    "forcas": [], "lacunas": [], "empresa_contexto": [], "melhorias": [],
    "angulo": "a tese em 1 frase",
    "cv": "/cvs/Nome-CV-Empresa-Cargo.pdf", "cv_preview": "/cvs/Nome-CV-Empresa-Cargo.png",
    "cv_racional": "3 a 5 linhas",
    "status": "proposto",
    "aprovado_em": "ISO, gravado ao aprovar",
    "nota_ajuste": "gravado ao pedir ajuste",
    "motivo": "gravado ao descartar ou expirar"
  }],
  "pessoas": [{
    "id": "pessoa-1", "vaga_id": "vaga-1",
    "nome": "", "cargo": "", "empresa": "", "url": "https://www.linkedin.com/in/...",
    "papel": "recruiter da vaga | hiring manager provável | par sênior",
    "grau": "1º|2º|3º", "porque": "uma linha com fato verificável",
    "status": "proposto"
  }]
}
```

Vaga de **triagem** leva só: id, empresa, cargo, url, local, modelo, porta, profundidade,
adicionada_em, fit, fit_resumo, red_flags, status.

**Status** (vaga e pessoa): `proposto` (aguarda você), `aprofundar` (vai para análise),
`aprovado` (na fila de execução; em pessoa, marcada para contato), `ajuste` (reescrever
conforme a nota), `recusado` (descartado ou expirado), `executado` (feito; sai de "Hoje" mas
a análise segue visível no Pipeline).

## registro.json: o histórico do que foi executado

```json
{
  "atualizado_em": "ISO com fuso", "leva": 1, "leva_inicio": "AAAA-MM-DD",
  "dias": [{
    "data": "AAAA-MM-DD",
    "vagas": [{"empresa": "", "cargo": "", "url": "", "local": "", "modelo": "",
               "salario": "", "salario_fonte": "", "status": "Aplicada", "angulo": "", "cv": "",
               "data_candidatura": "AAAA-MM-DD", "proximo_passo": "", "notas": ""}],
    "pessoas": [{"nome": "", "cargo": "", "empresa": "", "url": "", "papel": "", "status": "enviado"}],
    "observacoes": ["estado para a próxima sessão"]
  }]
}
```

Status de vaga: Analisada, CV pronto, Aplicada, Networking, Entrevista, Oferta, Recusada,
Encerrada, Descartada. Status de pessoa: mapeada, enviado, aceito, respondeu. Só entra aqui o
que foi aprovado E executado.

## decisoes.json: a fila de cliques do painel

`{"decisoes": [{"id": "vaga-1", "acao": "aprovar|aprofundar|ajustar|pular|nova_busca", "nota": "", "em": "ISO"}]}`.
Consumida e esvaziada pela rotina.

## config.json, buscas.json, perfil.json, fatos.md

Ver `exemplos/` e `docs/questionario.md` (cada pergunta diz o campo que preenche). Regra
geral do config: **campo vazio significa perguntar**.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `meus-dados/cvs/` | PDFs, previews PNG, JSONs de conteúdo dos CVs e cartas |
| `meus-dados/painel/` | o painel gerado (HTML com os dados dentro) |
| `meus-dados/varredura/AAAA-MM-DD/` | coleta, candidatas, descrições |
| `meus-dados/arquivo/leva-N/` | levas fechadas: valem para duplicata |
| `meus-dados/fontes/` | fonte licenciada opcional para o CV |
