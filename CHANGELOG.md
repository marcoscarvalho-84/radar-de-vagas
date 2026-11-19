# Mudanças

## Ainda não lançado

Fontes novas de vaga:

- Nas buscas no Brasil, a varredura também lê os portais da Gupy e da Sólides, pelo JSON
  que a página de busca deles usa, sem login. A vaga já vem com o link de candidatura da
  empresa, e a mesma vaga no LinkedIn sai como repetida. Busca por cidade fica com as vagas
  da cidade e as remotas. Cada fonte pode ser desligada em `config.json > rotina > fontes`,
  e `bin/radar varrer coleta --fontes` escolhe para uma coleta avulsa.
- `varrer descricao` e `varrer checa` aceitam os ids novos (`gupy-…`, `solides-…`) e o link
  de uma vaga em qualquer site: a página é lida pelo JobPosting em JSON-LD, que diz se a
  vaga ainda vale (`validThrough`).
- No LinkedIn, pausa também entre uma palavra-chave e outra: na pesquisa de fontes, a
  segunda chamada seguida já voltou com 429.
- `docs/fontes-de-vagas.md`: como cada fonte é lida, e por que Indeed, Glassdoor, Catho,
  InfoJobs e os outros sites grandes ficaram de fora.
- Os textos acompanham: a abertura diz onde cada busca roda ("no LinkedIn, na Gupy e na
  Sólides"), o painel mostra a origem de cada vaga ("via Gupy") e, na vaga de portal, um
  link só ("Ver a vaga na Gupy"), já que ele é também o da candidatura. A demonstração tem
  uma vaga de cada portal.
- Acesso: a busca nos portais não pede conta; a candidatura pede a conta de candidato da
  pessoa em cada um. README, questionário (blocos 0 e 8), `/radar-configurar` e
  `/radar-aplicar` dizem isso. No formulário desses portais, o `/radar-aplicar` troca o
  currículo salvo pelo CV da vaga, confere os campos pré-preenchidos e deixa para a pessoa
  qualquer teste da candidatura.

O radar da abertura:

- O mesmo desenho (papel, tinta, varredura azul), com um pouco de volume e luz: o prato tem
  espessura e deixa uma sombra macia na página, os pinos são esferas com brilho e sombra no
  tampo, e a varredura virou lanterna, nítida no ponteiro e cada vez mais difusa para trás.
  A luz fixa anda com quem olha, então a sombra cai sempre para trás e para a direita, e o
  pino que o facho alcança fica azul do lado do centro, na força do facho ali.
- Saíram as bolinhas cinzas deitadas no prato (as vagas cortadas), no 3D e no SVG.
- Ficou maior e sangra pela borda direita da tela, com 25% do prato de fora. A vaga certa e
  o selo FIT 86 ficam sempre no que aparece, em qualquer giro.

Do retorno do primeiro teste de ponta a ponta feito por outra pessoa:

- Correção: no Mac, o `bin/radar cv` falhava com erro de `libgobject` quando a glib estava
  instalada no Homebrew mas desligada do `lib/`, e o `bin/instalar` não percebia. O
  `bin/radar` agora também procura em `<brew>/opt/{glib,pango,harfbuzz,fontconfig}/lib`, o
  instalador termina gerando um PDF de teste de verdade, e o comando novo
  `bin/radar ambiente` diz qual biblioteca falta e o comando que resolve.
- `/radar-analise` confere se a vaga ainda está aberta antes de qualquer pesquisa: vaga boa
  fecha em dias, e o "aprofundar" do painel chega depois da triagem.
- Candidatura no site da empresa: o `bin/radar varrer checa` diz se a vaga é Easy Apply ou
  externa, e o comando novo `bin/radar ats "<empresa>" "<cargo>"` acha a vaga nos quadros
  públicos do Greenhouse, Lever e Ashby. O link vai para o campo novo `url_candidatura`, o
  painel mostra "Candidatar no site da empresa" e o `/radar-aplicar` vai direto por ele.
- Aviso de idioma: busca num país que pede uma língua que o perfil não mostra em nível de
  trabalho (França sem francês, por exemplo) aparece no passo Posições, no
  `bin/radar validar` e no questionário, antes da primeira varredura.
- Termo que pega outra área ("Revenue" traz revenue management de hotel; sigla curta casa
  com nome de empresa): o `bin/radar varrer filtra` mostra quanto cada palavra-chave trouxe e
  quanto passou, a `/radar-triagem` propõe os descartes, e o `/radar-configurar` já pensa
  nos homônimos ao montar o filtro de título.

- Correção: os filtros da Pipeline e a etiqueta de porta dos cards estavam fixos em
  "Liderança" e "IC sênior", as portas do autor. Agora saem de `config.objetivo.portas` de
  cada pessoa: um filtro por porta, com o título que ela deu.
- Rodando por um assistente, a pessoa usa vendo a tela: o `CLAUDE.md`, o novo `AGENTS.md`
  e as skills `/radar-configurar` e `/radar-perfil` mandam subir `bin/radar` e abrir a tela
  de abertura ou o painel no navegador, em vez de perguntar pelo chat. Sem terminal, o
  servidor imprime esse lembrete para o assistente junto com o link.
- Correção: o `bin/radar init` copiava o `exemplos/buscas.json` (cargos de design) para os
  dados de quem instalava, e a varredura procurava cargos que não eram os da pessoa. Agora o
  `buscas.json` nasce vazio, a coleta recusa sem palavra-chave ou com a cópia do exemplo, e
  o `bin/radar validar` avisa.
- Passo novo **Posições desejadas** na tela de abertura, com sugestões tiradas da trajetória
  do LinkedIn: cada posição vira uma busca no país do perfil. O `/radar-configurar` refina
  a partir das posições, do LinkedIn e do CV (português e inglês, títulos equivalentes,
  filtro de título) e a tela não sobrescreve mais.
- Tela de abertura: `bin/radar` na primeira vez abre no navegador uma apresentação do projeto
  e um passo a passo de contexto em 6 passos (LinkedIn, CV, posições, e-mail, portfólio, anexos),
  todos opcionais e retomáveis pelo link "Seu contexto" do painel.
- `bin/radar` sem argumento (ou `bin/radar abrir`) sobe o painel e abre o navegador.
- Upload pelo servidor local com as mesmas travas das decisões (Origin, Host, Content-Type),
  nome de arquivo refeito, assinatura dos bytes conferida e arquivos gravados só para o
  seu usuário. O ZIP do LinkedIn é lido e apagado: conexões e mensagens nunca ficam.
- A abertura tem duas telas: a apresentação (manchete, três ações, os combinados em tom de
  nota logo abaixo, como funciona em linha do tempo horizontal) e "Criando contexto", aberta
  por "Montar meu contexto". Cada passo dessa tela cabe sem rolar numa tela de notebook
  (1280x720), e o número do passo fica parado: só o algarismo troca. Passo feito ganha um
  check amarelo na trilha e no resumo do "Pronto".
- Anexos sem tipo de arquivo: cada arquivo da lista ganha um comentário (o que é e quando
  usar), que o `/radar-aplicar` usa para escolher o anexo certo.
- Radar 3D em Three.js na abertura (pinos na altura do fit, varredura que acende cada vaga,
  arrastar para girar), com o SVG de reserva sem WebGL. O painel ganha o mesmo radar, menor,
  ao lado da manchete em duas linhas; o aviso de config incompleta vai em amarelo embaixo de
  "Hoje".
- Visual: base do DS do portfólio do autor (papel quente, linha fina, caixa baixa, grão),
  acentos mantidos, azul vibrante `#263AF5` no lugar do céu e fonte Atkinson Hyperlegible
  Next empacotada (OFL).

## 0.1.0 · primeira versão pública

- Questionário de configuração em 12 blocos (`/radar-configurar`, `docs/questionario.md`).
- Importador do export oficial do LinkedIn (`bin/radar perfil importar`).
- Padrões de conteúdo documentados (`docs/padroes.md`).
- Pessoas a contactar viram mapa, sem rascunho de mensagem.
- Painel com o design system da Cerol, mantendo a fonte original.
- Correções vindas do uso real:
  - servidor recusa POST de outros sites (Origin, Content-Type, Host) e não manda CORS aberto;
  - trava e gravação atômica em todo JSON: cliques simultâneos não se perdem mais;
  - deduplicação e filtro de título viraram código (`bin/radar varrer filtra`), incluindo as
    levas arquivadas;
  - busca bloqueada pelo LinkedIn aparece como incompleta em vez de "zero vagas";
  - CV e carta usam o mesmo Python (venv fora de pastas sincronizadas);
  - painel gerado fora do código versionado e regerado sozinho quando os dados mudam;
  - `bin/radar validar` acusa vaga já aplicada que ainda aparece para aprovar;
  - triagem não oferece mais "aplicar" sem análise e CV;
  - alertas de aprovação parada e de triagem vencendo; `bin/radar expirar`.
