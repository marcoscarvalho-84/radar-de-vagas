---
name: radar-configurar
description: Conduz o questionário de configuração do Radar de Vagas, um bloco por vez, e grava as respostas em meus-dados (config.json, buscas.json, fatos.md, perfil.json). Use na primeira vez que alguém abre o projeto, quando meus-dados/config.json está vazio, quando a pessoa pede para configurar, ajustar preferências, mudar pretensão, palavras-chave, pesos de fit ou prazos, ou chama /radar-configurar com o nome de um bloco.
---

# Configurar o Radar

As perguntas, a ordem, o porquê de cada uma e o campo onde cada resposta é gravada estão em
`docs/questionario.md`. Leia o arquivo inteiro antes de começar. Este SKILL.md diz COMO
conduzir.

## Antes da primeira pergunta

1. Se `meus-dados/` não existe, rode `bin/radar init`.
2. Leia `meus-dados/config.json`, `meus-dados/buscas.json`, `meus-dados/perfil.json`,
   `meus-dados/fatos.md` e `meus-dados/contexto.json` (o que a tela de abertura já trouxe:
   LinkedIn, CV atual, e-mail, portfólio, anexos). Não pergunte de novo o que já está lá;
   passo pulado na tela vira pergunta aqui. Descubra o primeiro bloco ainda vazio e comece por ele (ou pelo
   bloco que a pessoa pediu no argumento).
3. Diga em uma linha quantos blocos faltam e quanto tempo leva, e que dá para parar a
   qualquer momento.

## Como conduzir

- **Um bloco por vez.** Mostre as perguntas do bloco juntas, numeradas, e espere a resposta.
  Pergunta com opções claras (sim ou não, remoto ou híbrido, 24 ou 48 horas): use a
  ferramenta de pergunta com botões quando existir. Pergunta aberta: texto.
- **Sugira, não imponha.** Onde houver padrão (*padrão* no questionário), mostre o padrão e
  pergunte se vale. Onde der para inferir do perfil (palavras-chave a partir das portas,
  idioma do CV a partir dos idiomas), traga a sugestão pronta para a pessoa só confirmar.
- **Nunca invente uma resposta.** Pergunta pessoal sem resposta (pretensão, piso,
  disponibilidade, autorização de trabalho) fica VAZIA. Vazio é uma resposta válida: faz a
  rotina perguntar na hora certa.
- **Grave ao fim de cada bloco**, não no fim de tudo, editando só os campos do bloco e
  preservando o resto do arquivo. Fatos vão para `fatos.md` com a data de hoje
  ("Confirmado em AAAA-MM-DD"). Depois de gravar, mostre em 2 a 4 linhas o que mudou.
- **Bloco 1 (perfil)** é conduzido pela skill `radar-perfil`: chame-a e volte daqui.
- **Bloco 8 (busca):** monte as palavras-chave a partir das portas do Bloco 3 (cada cargo em
  inglês e, quando fizer sentido, em português), uma por linha. Lembre que o LinkedIn não
  respeita OR nem aspas: uma palavra-chave por busca.
- Ritmo de conversa: frases curtas, sem jargão. A pessoa pode estar ansiosa com a busca;
  seja objetivo e gentil.

## No fim

1. Rode `bin/radar validar` e resolva o que for erro.
2. Mostre um resumo de uma tela: portas, restrições, regra de pretensão (sem valores se a
   pessoa preferir), nota mínima, palavras-chave, prazos.
3. Sugira o próximo passo: `/radar-triagem` para a primeira varredura, e `bin/radar painel`
   para abrir o painel.
