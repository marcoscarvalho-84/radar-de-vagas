---
name: radar-pessoas
description: Mapeia as pessoas-chave a contactar em cada vaga trabalhada do Radar (recruiter da vaga, hiring manager provável, head da área ou par sênior), com cargo, link do perfil, grau de conexão e o porquê de cada uma, SEM escrever nota, convite ou mensagem. Use depois da análise de uma vaga, quando a pessoa pergunta quem procurar numa empresa, ou quer saber quem é o recruiter ou o hiring manager de uma vaga.
---

# Pessoas a contactar

Padrões: `docs/padroes.md`, seção 4. Nesta versão o Radar entrega o MAPA; não escreve
mensagem nem envia convite. Se a pessoa pedir um rascunho, diga que o módulo de mensagens
ainda não faz parte do projeto e que o contato é dela.

## Como mapear

Com o Claude in Chrome logado no LinkedIn da pessoa, em ritmo humano, uma ação por vez:

1. **Recruiter da vaga:** o anúncio às vezes mostra o hiring team ("Conheça a equipe de
   contratação"). Senão, aba People da empresa com "recruiter" ou "talent".
2. **Hiring manager provável:** quem lidera o time para o qual a vaga reporta (head, director,
   manager da área). Aba People com o nome da área.
3. **Terceiro nome:** head ou director da área acima, ou um par sênior do time (quem mantém o
   produto ou o sistema citado na vaga). Em empresa pequena, o founder.

Quantidade: `config.pessoas.por_vaga` (padrão 3). Papéis: `config.pessoas.papeis`.

## Para cada pessoa

- `nome`, `cargo`, `empresa`, `url` (sempre `linkedin.com/in/...`), `papel`, `grau` ("1º",
  "2º", "3º") e `porque`: uma linha com fato verificável ("aparece no hiring team", "lidera
  o time de plataforma").
- Conferir: ainda está na empresa (perfil atualizado), sem convite pendente, e o grau.
  1º grau é marcado: é caminho de indicação.
- Id com `bin/radar proximo-id pessoa`, `vaga_id` da vaga, `status: "proposto"`.

## Limites

- Nunca abrir mensagens, nunca enviar convite, nunca seguir ou curtir em nome da pessoa.
- Nada de raspagem em lote: só os perfis necessários, abertos um a um.
- Pessoa que aparece em restrição da pessoa (ex.: ex-chefe que ela não quer contatar,
  registrado em `fatos.md`) nunca é proposta.
- Pedido de login, captcha ou aviso de comportamento incomum: parar e avisar.
