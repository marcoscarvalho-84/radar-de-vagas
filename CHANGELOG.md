# Mudanças

## Ainda não lançado

- Tela de abertura: `bin/radar` na primeira vez abre no navegador uma apresentação do projeto
  e um passo a passo de contexto em 5 passos (LinkedIn, CV, e-mail, portfólio, anexos),
  todos opcionais e retomáveis pelo link "Seu contexto" do painel.
- `bin/radar` sem argumento (ou `bin/radar abrir`) sobe o painel e abre o navegador.
- Upload pelo servidor local com as mesmas travas das decisões (Origin, Host, Content-Type),
  nome de arquivo refeito, assinatura dos bytes conferida e arquivos gravados só para o
  seu usuário. O ZIP do LinkedIn é lido e apagado: conexões e mensagens nunca ficam.
- A abertura tem duas telas: a apresentação (manchete, três ações, os combinados em tom de
  nota logo abaixo, como funciona em linha do tempo horizontal) e "Seu contexto", aberta por
  "Montar meu contexto".
- Radar 3D em Three.js na abertura (pinos na altura do fit, varredura que acende cada vaga,
  arrastar para girar), com o SVG de reserva sem WebGL.
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
