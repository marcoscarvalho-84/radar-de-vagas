# Design system do painel

O painel e a tela de abertura usam a **base do design system do portfólio do autor**, com os
acentos de cor da Cerol e uma fonte escolhida pela leitura.

## Base (do portfólio)

- **Papel quente `#F5F4F0` e tinta `#050505`.** Rampa neutra quente de `#EFEEE9` a `#050505`.
- **Linha fina como estrutura:** `1px` de tinta a 16% (`--linha`, `--fio`) em seções, cards e
  listas. Campo, botão, pílula e marcador levam o fio de tinta cheio (`--fio-forte`), porque
  componente de interface precisa de 3:1.
- **Tipo grande em caixa baixa,** peso 600, espaçamento `-0.02em`, entrelinha 1.06. Rótulos
  pequenos em caixa-alta com espaçamento `0.09em`, no cinza `#6A6A66` (4,9:1 no papel).
- **Pílula de ação** em caixa-alta espaçada (`0.08em`), 13px.
- **Números finos** (peso 200) nos contadores e na numeração dos passos.
- **Grão de filme** a 5% por cima de tudo, sem pegar clique.
- **Motion:** curva `cubic-bezier(0.16, 0.84, 0.36, 1)` nas entradas, `cubic-bezier(0.4, 0, 0.2, 1)`
  nas trocas de cor. Tudo respeita `prefers-reduced-motion`.

## Acentos

- **Amarelo `#F7F00C`, a única cor de ação:** botão primário, passo atual, barras de fit, estado
  aprovado, o bloco atrás de "Aplicar bem / é raro." e a vaga certa no radar. Nunca como texto
  sobre papel (1,1:1): é sempre o fundo atrás da tinta. No hover, o primário inverte para tinta
  com texto amarelo.
- **Magenta `#EC008C`, interferência:** alertas (aprovação parada, triagem vencendo, erro de
  campo). Nunca cor de botão. Texto em tinta por cima passa AA (4,8:1).
- **Azul vibrante `#263AF5`, pausa:** a faixa de números, "Já aplicada", a zona de arquivo
  quando você arrasta, a varredura do radar e, na abertura, os títulos dos combinados e do
  "Como funciona". Como fundo, **só texto em papel por cima** (6,3:1); tinta no azul não passa
  (2,9:1). Como texto no papel, passa (6,3:1).
- **Fita:** faixa de tinta com texto amarelo em marquee. Para no hover e com movimento reduzido.
- **A marca é só texto:** "Radar de Vagas", sem caixa atrás de nenhuma palavra.

## Fonte

**Atkinson Hyperlegible Next**, do Braille Institute, desenhada para a máxima distinção entre
letras parecidas (I, l, 1; O, 0). Vem com o projeto em `dashboard/fonts/` (SIL Open Font
License, ver `dashboard/fonts/OFL.txt`), variável de 200 a 800: o painel abre sem internet e
não pede nada a servidor de fonte. O `bin/radar gerar` copia a pasta para junto do painel
gerado.

O CV e a carta continuam na **Figtree** (`templates/fonts/`, OFL), no layout neutro: o CV é um
documento seu, não do painel.

## Forma

Conteúdo e campo são retos (0), ação é pílula (999px), avatar e marcador são círculo. Zero
sombra e zero gradiente: o que precisa subir ganha fio, inverte de cor ou troca de superfície.

## Radar 3D

A tela de abertura troca o radar em SVG por um radar em Three.js (`dashboard/radar-3d.js`,
biblioteca em `dashboard/vendor/`, MIT). Continua chapado: só `MeshBasicMaterial`, sem luz e
sem sombra; as cores são lidas dos tokens do `:root`. Sem WebGL, ou com o painel aberto por
duplo clique, o SVG fica.

## Contribuindo com o visual

Tokens novos entram no `:root` de `dashboard/styles.css`. Antes de abrir PR, confira: zero
`box-shadow`, zero gradiente, pesos só 200/400/500/600/700, nenhum raio fora de
0/8px/pílula/círculo, amarelo nunca como texto sobre papel, nada em tinta sobre o azul,
contraste AA, e o painel e a abertura a 375px de largura sem rolagem horizontal.
