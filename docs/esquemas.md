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

## contexto.json: a tela de abertura

O que a pessoa entregou no passo a passo de `bin/radar` (primeira vez). Gravado por
`radar/contexto.py`, nunca à mão.

```json
{
  "abertura": {"iniciada_em": "ISO", "concluida_em": "ISO ou vazio (vazio = abre a tela de novo)"},
  "linkedin": {"url": "https://www.linkedin.com/in/...", "fonte": "export|pdf|", "importado_em": "ISO"},
  "cv": {"arquivo": "anexos/cv-atual.pdf", "texto": "anexos/cv-atual.txt", "palavras": 412, "enviado_em": "ISO"},
  "posicoes": ["Analista de Dados Sênior", "Data Analyst"],
  "email": "voce@exemplo.com",
  "portfolio": {"url": "https://...", "outros": ["https://github.com/..."]},
  "anexos": [{"arquivo": "anexos/estudo-de-caso.pdf", "nome_original": "Estudo de caso.pdf",
              "comentario": "o que é e quando usar, escrito pela pessoa (até 280 caracteres)",
              "tamanho": 123456, "enviado_em": "ISO"}],
  "pulados": ["cv"],
  "sugestoes": {"email": "do export do LinkedIn, para a pessoa confirmar", "portfolio": "idem"}
}
```

E-mail, LinkedIn e portfólio também vão para `perfil.json > contatos`, sem `https://` (é de lá
que o CV lê). Sem perfil ainda, nasce um perfil mínimo que o import do export completa.
Texto lido do CV atual (`anexos/cv-atual.txt`) e do PDF do perfil (`perfil-bruto.txt`) é
RASCUNHO: só vira fato depois de confirmado no `/radar-perfil`.

## buscas.json

```json
{
  "origem": "|posicoes|questionario",
  "janela_horas": 48,
  "grupos": [{"local": "Brazil", "palavras_chave": ["Analista de Dados Sênior", "Data Analyst"]}],
  "filtro_titulo": {"precisa_ter": [], "senioridade": [], "descartar_se_tiver": []},
  "corte": {"descartar_se": ["..."]}
}
```

Nasce vazio no `bin/radar init`. O passo **Posições** da tela de abertura grava a primeira
versão (`origem: "posicoes"`: cada posição vira uma busca no país do perfil). O
`/radar-configurar` refina a partir do LinkedIn e do CV e marca `origem: "questionario"`;
daí em diante a tela não sobrescreve. Sem palavra-chave, ou com a cópia do
`exemplos/buscas.json` (que é só da demonstração), `bin/radar varrer coleta` recusa e diz
onde preencher. Filtro de título vazio não corta nada.

## config.json, perfil.json, fatos.md

Ver `exemplos/` e `docs/questionario.md` (cada pergunta diz o campo que preenche). Regra
geral do config: **campo vazio significa perguntar**.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `meus-dados/cvs/` | PDFs, previews PNG, JSONs de conteúdo dos CVs e cartas |
| `meus-dados/anexos/` | CV atual, PDF do perfil e anexos da tela de abertura (só o seu usuário lê) |
| `meus-dados/painel/` | o painel gerado (HTML com os dados dentro) |
| `meus-dados/varredura/AAAA-MM-DD/` | coleta, candidatas, descrições |
| `meus-dados/arquivo/leva-N/` | levas fechadas: valem para duplicata |
| `meus-dados/fontes/` | fonte licenciada opcional para o CV |
