# Design system do painel

O painel usa o **design system da Cerol**, com uma exceção deliberada: a fonte.

## O que vem da Cerol

- **Base editorial:** papel branco `#FFFFFF`, tinta preta quente `#100F0D`, fios de 1px como
  estrutura.
- **Uma cor de ação:** o amarelo `#F7F00C` carrega todo botão primário e nada mais. Nunca
  como texto sobre branco (1,2:1).
- **Magenta `#EC008C` como interferência:** alertas (aprovação parada, triagem vencendo,
  follow-up). Nunca cor de botão.
- **Céu `#79AAC3` como pausa:** superfície de respiro, só com texto preto.
- **Rampa neutra quente** de `#F7F6F4` a `#100F0D`.
- **Flat absoluto:** nenhuma sombra, nenhum gradiente. Profundidade vem de fio, inversão e
  sobreposição.
- **Gramática de forma:** conteúdo é reto (raio 0), ação é pílula (999px), input tem 8px,
  avatar é círculo. Nenhum raio intermediário.
- **Botão primário:** pílula amarela com borda tinta; no hover inverte (fundo tinta, texto
  amarelo) com `scale(1.04)` e easing com overshoot.
- **Fita:** os links "Ver a vaga" e "Abrir o perfil" são a fita da Cerol (faixa tinta, texto
  amarelo, marquee). Param com `prefers-reduced-motion`.
- **Pesos 300, 400 e 700**, nada no meio.
- **Motion:** 150ms (hover), 240ms (padrão), 480ms (entradas), easing
  `cubic-bezier(0.2, 0.7, 0.2, 1)`.

Referência completa dos tokens e regras: o DESIGN.md da Cerol (tokens reproduzidos em
`dashboard/styles.css`, no `:root`).

## O que fica do projeto original

- **Fonte do painel:** a pilha `"Helvetica Now Display", "Neue Haas Grotesk Display",
  "Helvetica Neue", Helvetica, Arial, sans-serif`. Quem não tem as duas primeiras (comerciais)
  vê Helvetica Neue ou Arial. A Pacaembu da Cerol é comercial e não é distribuída aqui.
- **Fonte e layout do CV e da carta:** Figtree (SIL Open Font License, empacotada em
  `templates/fonts/`), no layout neutro do CV. O CV é um documento seu, não do painel: não
  leva as cores da Cerol.

## Contribuindo com o visual

Tokens novos entram no `:root` de `dashboard/styles.css`. Antes de abrir PR, confira: zero
`box-shadow`, zero gradiente, nenhum peso 500/600, nenhum raio fora de 0/8px/pílula/círculo,
contraste AA, e o painel a 375px de largura sem rolagem horizontal.
