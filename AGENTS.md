# Radar de Vagas · para assistentes

As instruções completas estão em [CLAUDE.md](CLAUDE.md) (rotina, regras, comandos) e cada
função em `.claude/skills/`. Vale para qualquer assistente (Claude Code, Codex, Cursor):

- **A pessoa usa vendo a tela.** Suba `bin/radar` em segundo plano (ele não termina sozinho)
  e abra a tela no navegador para ela, ou mande o link e peça para abrir:
  http://localhost:8322/boas-vindas na primeira vez ou com o contexto incompleto,
  http://localhost:8322 para as decisões do dia. LinkedIn, CV, posições desejadas, anexos e
  decisões passam pela tela, não pelo chat.
- **Nada sai sem aprovação.** Candidatura, mensagem ou convite só com o ok dela.
- **Os dados são dela.** Tudo fica em `meus-dados/` (fora do git). Campo vazio no config
  significa perguntar, nunca chutar.
