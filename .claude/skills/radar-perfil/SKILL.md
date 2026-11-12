---
name: radar-perfil
description: Coleta e estrutura o perfil profissional da pessoa a partir do LinkedIn (export oficial de dados, PDF do perfil ou leitura do próprio perfil no navegador) e confirma os fatos que podem ser usados em CV, carta e formulários. Use quando a pessoa quer importar o perfil, atualizar experiências, registrar uma conquista nova, ou quando meus-dados/perfil.json não existe.
---

# Perfil: a fonte de fatos

Tudo que o Radar escreve em nome da pessoa sai daqui. Por isso o perfil tem duas camadas:
`perfil.json` (estrutura: nome, contatos, experiências, formação) e `fatos.md` (as provas
confirmadas, com data). Importado não é confirmado: nada vira fato citável sem o ok dela.

## 0. O que a tela de abertura já trouxe

Antes de pedir qualquer coisa, leia `meus-dados/contexto.json`. A tela de abertura
(`bin/radar`, primeira vez) pode já ter:

- importado o export do LinkedIn para `perfil.json` (`linkedin.fonte: "export"`);
- guardado o PDF do perfil, com o texto em `meus-dados/perfil-bruto.txt` (`fonte: "pdf"`);
- guardado o CV atual em `meus-dados/anexos/`, com o texto em `anexos/cv-atual.txt`;
- gravado e-mail, LinkedIn e portfólio em `perfil.json > contatos`.

Se faltar o LinkedIn ou o CV, o caminho é a tela, não o chat: suba `bin/radar` em segundo
plano e abra http://localhost:8322/boas-vindas para a pessoa (ou mande o link), no passo
que falta. Use o que existir e pule o passo correspondente abaixo. O texto do CV atual é a melhor fonte
para as perguntas de prova (seção 2): traga cada número que aparece nele e pergunte se a
pessoa sustenta numa entrevista. Nada do CV antigo vira fato sem esse ok.

## 1. Importar (escolher UM caminho, nesta ordem de preferência)

**a) Export oficial do LinkedIn (recomendado).** Explique o passo a passo:
LinkedIn > Eu > Configurações e privacidade > Privacidade dos dados > Obter uma cópia dos
seus dados > marcar "Perfil", "Cargos", "Formação acadêmica", "Competências" e "Idiomas" (ou o
arquivo completo) > solicitar. O LinkedIn manda o ZIP por e-mail em minutos (o completo pode
levar até 24h). Com o arquivo baixado:

    bin/radar perfil importar ~/Downloads/Basic_LinkedInDataExport_....zip

O importador lê só os CSVs de perfil. Conexões, mensagens e convites nunca são abertos.

**b) PDF do perfil.** No próprio perfil: botão "Mais" > "Salvar em PDF". Então:

    bin/radar perfil pdf ~/Downloads/Profile.pdf

O texto bruto vai para `meus-dados/perfil-bruto.txt`; estruture você mesmo no formato de
`exemplos/perfil.json`, mostrando o resultado para a pessoa conferir.

**c) Navegador.** Com o Claude in Chrome conectado e logado, abrir o PRÓPRIO perfil da pessoa
(nunca o de terceiros) e ler headline, sobre, experiências e formação, uma seção por vez, em
ritmo humano. Estruturar como em (b).

Se já existe `perfil.json`, o import vai para `perfil.importado.json`: compare os dois com a
pessoa e mescle só o que ela aprovar.

## 2. Confirmar, bloco a bloco

1. Nome como deve sair no CV e em quantas linhas (`nome_cv`), e quais contatos aparecem.
2. Cada experiência: empresa, cargo, datas (AAAA-MM), se entra no CV. Datas nunca são
   estimadas: na dúvida, pergunte.
3. Provas com número: para cada experiência, pergunte o que ela pode defender numa entrevista
   (métrica, tamanho de time, produtos, público). Grave em `perfil.json > provas` com
   `origem` e `confirmado_em`, e em `fatos.md`.
4. O que ela NÃO tem e costuma aparecer em vagas: `fatos.md`, seção própria. É o que evita
   resposta inflada.

## 3. Regras

- Verdade documental (docs/padroes.md, seção 1): reformular sim, inventar ou arredondar para
  cima nunca. Número sem origem não entra.
- O perfil evolui: quando a pessoa contar uma conquista nova na conversa, ofereça registrá-la
  aqui com a data.
- Ao terminar, rode `bin/radar validar` e mostre o resumo (`nome`, número de experiências,
  número de provas confirmadas).
