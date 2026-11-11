# Contribuindo

Obrigado por querer melhorar o Radar. Algumas combinações para a gente andar junto.

## Antes de abrir um PR

1. **Nunca suba dados reais.** Nem os seus, nem de recrutadores, nem de empresas com vaga
   real. Exemplos são sempre fictícios (`exemplos/`), com links `linkedin.com/in/exemplo-...`.
2. Rode os testes: `python3 -m unittest discover tests` (sem weasyprint, o teste de PDF pula).
3. Rode a demo (`bin/radar demo`) e confira o painel a 1280px e a 375px.
4. Mudou regra de conteúdo? Atualize `docs/padroes.md`. Mudou formato de dado? Atualize
   `docs/esquemas.md`, `radar/validar.py` e os exemplos.

## O que mantém o projeto coerente

- **Aprovação humana não é opcional.** PR que cria envio automático sem checkpoint não entra.
- **Biblioteca padrão primeiro.** Dependência nova só para o que não dá para fazer sem ela
  (hoje: weasyprint e pypdf, para PDF).
- **Português do Brasil** em código, comentários e docs, no tom dos arquivos existentes:
  comentário explica o PORQUÊ, não o quê.
- **Toda escrita em `meus-dados/` passa por `radar/arquivos.py`** (trava e gravação atômica).
- **Visual:** as regras de `docs/design-system.md` (zero sombra, zero gradiente, pesos 300,
  400 e 700, raio 0/8px/pílula).

## Boas primeiras contribuições

- Coleta em outros sites de vagas (Gupy, Greenhouse, Lever, Ashby) com o mesmo contrato de
  `radar/varredura.py`.
- Módulo de rascunho de mensagens para as pessoas mapeadas, com o mesmo fluxo de aprovação.
- Tradução dos docs para inglês e espanhol.
- Leitura de vagas a partir de alertas de e-mail.
- Mais testes para o painel (hoje o JS é conferido à mão).

## Reportando um problema com o LinkedIn

O LinkedIn muda sem aviso. Ao reportar, inclua a data, o comando, o trecho do erro e o que
mudou. Sem cookies, sem tokens, sem dados pessoais no relato.
