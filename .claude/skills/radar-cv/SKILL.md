---
name: radar-cv
description: Gera o CV sob medida em PDF (1 página, A4) e, quando o formulário pede, a carta de apresentação, a partir do perfil e dos fatos confirmados da pessoa e do ângulo da vaga. Use depois da análise de uma vaga, quando a pessoa pede para adaptar o currículo, fazer um CV para uma vaga, ajustar o CV ou escrever uma carta de apresentação.
---

# CV e carta

Padrões: `docs/padroes.md`, seções 1, 5, 6 e 8. Fatos só de `perfil.json` e `fatos.md`.

## CV

1. Parta do último CV da pessoa em `meus-dados/cvs/cv-*.json` (se não houver, de
   `exemplos/cv-exemplo.json` como ESTRUTURA, nunca como conteúdo) e salve como
   `meus-dados/cvs/cv-{empresa}.json`.
2. Edite pela receita de `docs/padroes.md`, seção 5:
   - `tagline_l1/l2` alinhadas ao domínio da vaga;
   - `hook_main` e `hook_accent`: duas partes, a segunda em linha nova, nada ligando as duas;
   - `positioning`: reescreva 20 a 40% mirando a vaga, com os mesmos fatos;
   - `why_label` = "Why {Empresa}" (ou "Por que a {Empresa}" em português) e as 4 linhas da
     receita, com a linha 2 vindo de `config.cv.diferencial`;
   - `experience`: mesma lista e mesmas datas de sempre; ajuste só a ênfase com keywords
     reais da vaga. Porta IC: liderança como prova de escopo.
   - Respeite `config.estilo.proibicoes` em todo texto novo.
3. Gere:

       bin/radar cv meus-dados/cvs/cv-{empresa}.json "meus-dados/cvs/{Nome}-CV-{Empresa}-{Cargo}.pdf"

4. Abra o PNG de preview e confira de verdade (quebras, viúvas, aperto). Densidade abaixo de
   0.92: corte texto e gere de novo.
5. Na vaga em `vagas.json`: `cv` e `cv_preview` com caminho começando em `/cvs/`, e
   `cv_racional` com 3 a 5 linhas do que mudou e por quê.

Idioma: `config.cv.idioma_padrao`. Vaga em outro idioma e `perguntar_antes_de_traduzir`:
pergunte.

## Carta (só quando o formulário pede, ver `config.carta.quando`)

1. Escreva `meus-dados/cvs/Carta-{Empresa}-{Cargo}.md`: cabeçalho de contexto (vaga, ângulo,
   data), uma linha `---`, o corpo. 120 a 200 palavras, 3 ou 4 parágrafos: por que esta
   empresa (1 ou 2 pontos reais da análise), a prova mais forte ligada ao problema deles, o
   ângulo, um fecho sem implorar. Sem assinatura: nome e contatos entram sozinhos.
2. Gere:

       bin/radar carta meus-dados/cvs/Carta-{Empresa}-{Cargo}.md "meus-dados/cvs/{Nome}-Carta-{Empresa}-{Cargo}.pdf"

3. Mostre a carta inteira na conversa junto com o PDF. Carta também passa pelo ok.
