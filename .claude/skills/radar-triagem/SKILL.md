---
name: radar-triagem
description: Varre vagas novas no LinkedIn pelo endpoint público e, nas buscas no Brasil, nos portais da Gupy e da Sólides, corta o que não serve, dá nota de fit de 0 a 100 com justificativa e red flags, e publica a triagem no painel do Radar. Use para a varredura diária, quando a pessoa pede "busca vagas", "o que saiu hoje", "nova varredura", ou quando a fila de decisões traz nova_busca.
---

# Triagem: da coleta à nota de fit

Padrões que mandam aqui: `docs/padroes.md`, seções 1, 2 e 9. Detalhes técnicos do LinkedIn:
`docs/linkedin-tecnico.md`. As outras fontes (Gupy, Sólides) e os ids de cada uma:
`docs/fontes-de-vagas.md`.

## 1. Coletar

    caffeinate -i bin/radar varrer coleta      # macOS; em outro sistema, sem o caffeinate
    bin/radar varrer filtra

A coleta usa as palavras-chave e locais de `meus-dados/buscas.json` e grava em
`meus-dados/varredura/AAAA-MM-DD/`. Nas buscas no Brasil ela também lê os portais da Gupy e
da Sólides (as fontes ligadas estão em `config.json > rotina > fontes`); cada vaga da coleta
tem `fonte`, e o resumo da coleta diz quantas vieram de cada uma. Se aparecer "ATENÇÃO ... resultado incompleto", a busca
foi bloqueada no meio (ou o portal não respondeu): diga isso no resumo, não finja que o
mercado está fraco. Se a coleta
recusar por falta de palavra-chave, ou porque o `buscas.json` ainda é o exemplo, não invente
termos: rode o bloco Busca do `/radar-configurar`, que monta as buscas a partir das posições,
do LinkedIn e do CV da pessoa. Se o LinkedIn devolver bloqueio em sequência, pare e avise;
não insista.

O `filtra` já corta título fora da área, júnior, fora da janela e duplicata contra o Radar,
o histórico e as levas arquivadas. O que sobra está em `candidatas.json`.

Antes de ler descrição, olhe `candidatas.json > por_palavra`: quanto cada palavra-chave
trouxe, quanto passou e os títulos que passaram. Termo que pega outra área aparece ali.
"Revenue" traz revenue management de hotel. Uma sigla curta ("GTM", "CRM") casa com o nome
de uma empresa. Quando uma palavra traz uma família de títulos que não são da pessoa:
- corte essas vagas nesta triagem, sem nota;
- proponha no resumo os termos para `buscas.json > filtro_titulo > descartar_se_tiver`
  ("hotel", "hospitality", "revenue manager"), com quantas vagas de hoje cada um cortaria;
- grave só com o ok da pessoa.

## 2. Ler e cortar

Para as candidatas, em ordem de data (mais recentes primeiro):

    bin/radar varrer descricao <id> <id> ...

O id é o da coleta: o número do LinkedIn ou `gupy-…`/`solides-…`. Leia cada descrição (se
vier vazia, use WebFetch no `url` da candidata). Vaga marcada FECHADA sai. Aplique `buscas.json > corte.descartar_se` e as restrições de
`config.trabalho` (modelo, cidade, internacional). Vaga internacional: confira na descrição se
aceita contratação no país da pessoa antes de gastar análise.

## 3. Dar a nota

Para cada vaga que passou, contra `perfil.json` e `fatos.md`:
- nota de 0 a 100 ponderada pelos pesos de `config.fit.pesos` (domínio, senioridade, porta,
  escopo, modelo);
- `fit_resumo`: UMA frase honesta, com o que puxa para cima e o que puxa para baixo;
- `red_flags`: lista curta, uma frase cada;
- `porta`: o id da porta da vaga em `config.objetivo.portas`.

## 4. Publicar

1. Ids novos com `bin/radar proximo-id vaga` (um por vez, ou max+1 em sequência a partir dele).
2. Cada vaga entra em `meus-dados/vagas.json` com `profundidade: "triagem"`, `status:
   "proposto"`, `adicionada_em` de hoje e só os campos de triagem: empresa, cargo, url
   (o `url` da candidata: permalink do LinkedIn ou link da vaga no portal), local, modelo,
   fit, fit_resumo, red_flags, porta. Vaga da Gupy ou da Sólides leva também
   `url_candidatura` igual ao `url` (a candidatura é ali mesmo) e, se a coleta trouxe,
   `salario` e `salario_fonte`.
3. Atualize `data`, `gerado_em` e `resumo_busca` ("6 palavras-chave, 212 vagas em 48h
   (LinkedIn 170, Gupy 31, Sólides 11), 9 lidas, 3 cortadas na triagem").
4. As `fit.vagas_trabalhadas_por_dia` melhores acima de `fit.fit_minimo_para_aprofundar`
   (respeitando uma frente por empresa) seguem para `/radar-analise`. Se sobrarem menos,
   trabalhe as que houver e diga isso; nunca complete a cota com vaga ruim.
5. `bin/radar validar`, `bin/radar gerar`, e o resumo curto na conversa com o link do painel.
