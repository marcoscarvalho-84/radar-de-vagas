---
name: radar-analise
description: Aprofunda uma vaga do Radar (ou uma vaga que a pessoa mandar por link ou texto) com contexto da empresa, leitura de salário com fonte, mapa de fit com forças, adjacências e lacunas honestas, o ângulo da candidatura em uma frase e as melhorias de perfil que a vaga sugere. Use quando uma vaga é escolhida para aprofundar, quando a fila traz "aprofundar", ou quando a pessoa pergunta se vale a pena se candidatar a uma vaga específica.
---

# Análise completa de uma vaga

Padrões: `docs/padroes.md`, seções 1 e 3. Uma vaga por vez, do começo ao fim.

## 1. Ler a vaga

- Vaga do Radar: a descrição está em `meus-dados/varredura/.../descricoes/{id}.txt` ou via
  WebFetch no permalink. Vaga mandada pela pessoa: confira antes se já está no Radar
  (empresa + cargo, inclusive no arquivo). Já está: diga em que estado e pare.
- Link que redireciona para a página geral da empresa, dá erro ou vem sem texto: a vaga
  fechou. Avise antes de qualquer outra coisa.
- Extraia: senioridade real, porta, local e modelo, faixa publicada, requisitos obrigatórios
  e desejáveis, keywords que um ATS leria, sinais de cultura e red flags.

## 2. Empresa e salário

- 3 a 6 buscas curtas (WebSearch): produto e tese; estágio, funding, crescimento ou layoffs;
  notícias dos últimos 6 meses; cultura publicada; como a área da pessoa aparece em público.
- `empresa_contexto`: 3 a 5 pontos, cada um uma frase com fato verificável.
- `salario` + `salario_fonte`: publicada na vaga, ou estimativa com a fonte citada e a
  palavra "estimativa". Nunca chute como fato.

## 3. Fit e narrativa

Contra `perfil.json` e `fatos.md`, nada além:
- `forcas`: requisito da vaga ligado a uma prova com número;
- `lacunas`: o que falta de verdade, cada uma com a forma honesta de endereçar;
- adjacências honestas entram em forças, marcadas como adjacência;
- `angulo`: a tese em UMA frase;
- `melhorias`: 1 a 3 ações de perfil, portfólio ou conteúdo que a vaga sugere;
- nota de fit revista com a descrição completa, e o `fit_resumo` atualizado.

## 4. Fechar

- Grave na vaga (`profundidade: "completa"`, status `proposto`) e siga para `/radar-cv` e
  `/radar-pessoas`. O ângulo NÃO para a rotina para pedir ok no meio: ele vai para o painel
  junto com o CV, e a pessoa decide os dois de uma vez.
- Exceção: vaga mandada avulsa na conversa. Aí apresente o mapa e o ângulo primeiro e
  pergunte se segue para o CV, para não gastar um ciclo na direção errada.
- A cada 5 vagas registradas no histórico, consolide as `melhorias` repetidas em uma
  sugestão agregada para a pessoa.
