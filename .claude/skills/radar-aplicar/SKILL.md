---
name: radar-aplicar
description: Executa a candidatura de uma vaga aprovada no Radar pelo navegador (Claude in Chrome), preenchendo o formulário com o CV aprovado e respostas no padrão do projeto, com checkpoint obrigatório de todas as perguntas e respostas antes de enviar. Use somente para vagas com status aprovado e depois do ok final na conversa, quando a pessoa diz "pode aplicar", "manda a candidatura" ou aprova a fila de execução.
---

# Aplicar

Padrões: `docs/padroes.md`, seções 1, 7 e 8. Guia técnico do navegador:
`docs/linkedin-tecnico.md`. Esta é a única etapa que age em público: cada regra aqui existe
para que nada saia sem a pessoa ver.

## Antes de abrir o navegador

1. Liste o que está aprovado (`status: "aprovado"` em `vagas.json`) e peça UM ok final curto
   na conversa. Aprovar no painel não basta, e aprovação de sessão antiga não vale.
2. Confira de novo que a vaga não está no histórico como aplicada (`bin/radar validar`).
3. Confira que a vaga ainda está aberta (`bin/radar varrer checa <id>`). Fechou: marque
   `recusado` com o motivo, registre como Encerrada e siga para a próxima.

## No formulário (uma vaga por vez, uma ação por vez)

1. Abra o link real da vaga. Login, conta nova, captcha ou verificação: pare e peça para a
   pessoa fazer essa parte; continue depois.
2. Preencha:
   - contatos do `perfil.json`;
   - o PDF aprovado (caminho absoluto em `meus-dados/cvs/`). No LinkedIn, troque o CV
     armazenado pelo CV da vaga: o Easy Apply usa o último enviado por padrão;
   - respostas abertas pelas estruturas da seção 7, amarradas ao ângulo da vaga, no idioma
     do formulário;
   - pretensão, disponibilidade, autorização de trabalho: do `config`. Campo vazio no
     config: PERGUNTE, nunca chute;
   - `config.formulario.nunca_preencher`: deixe para a pessoa;
   - texto longo: prefira preencher o campo diretamente em vez de digitar caractere a
     caractere, e confira o comprimento depois (ver docs/linkedin-tecnico.md).
3. **Checkpoint obrigatório:** liste na conversa TODAS as perguntas com as respostas
   exatamente como estão no formulário, mais um screenshot da revisão. Espere o ok. Ajuste
   pedido: edite, reapresente, espere de novo. Easy Apply: checkpoint na última tela.
4. Logo antes de enviar, confira que o anexo ainda é o CV certo.
   Formulário pedindo outro arquivo (portfólio em PDF, estudo de caso, certificado): use os
   anexos de `meus-dados/contexto.json`, pela categoria, e diga no checkpoint qual arquivo
   vai em qual campo. Nenhum anexo sem o ok; sem anexo adequado, pergunte.
5. Envie. Screenshot da confirmação.

## Depois

1. `bin/radar marcar <id> executado`.
2. Registre em `meus-dados/registro.json`, no dia de hoje: empresa, cargo, url, local, modelo,
   salário e fonte, `status: "Aplicada"`, ângulo, cv, `data_candidatura`, `proximo_passo`
   ("Follow-up em DD/MM/AAAA se não houver retorno", com `config.rotina.follow_up_dias`) e
   notas (o valor de pretensão declarado, se houve).
3. `bin/radar validar` e `bin/radar gerar`.
4. Resumo: o que saiu (com link), o que ficou pendente, próximo passo com data.
