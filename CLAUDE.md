# Radar de Vagas

Este projeto é uma rotina de busca de emprego que roda com o Claude Code: varre vagas,
dá nota de fit, aprofunda as melhores, gera CV e carta sob medida, mapeia quem contatar e
aplica, sempre com a pessoa aprovando cada ação pública. O painel local
(`bin/radar painel`, http://localhost:8322) é a interface de decisão.

Quem manda em quê:
- **Este CLAUDE.md** manda na ROTINA: ordem, arquivos, aprovação.
- **`docs/padroes.md`** manda na FORMA de todo conteúdo (fit, CV, carta, formulário, links).
- **As skills em `.claude/skills/`** mandam em cada função. Use-as pelo Skill tool.
- **`meus-dados/`** é o CONTEÚDO da pessoa: perfil, fatos, preferências, vagas, histórico.

## Primeira vez

Se `meus-dados/config.json` não existe ou está vazio: não rode a rotina. Ofereça
`bin/radar demo` (dados fictícios, 3 minutos) e então `/radar-configurar`.

## A rotina diária (ordem obrigatória)

1. **Preparar.** Ler `docs/padroes.md`, `meus-dados/perfil.json`, `meus-dados/fatos.md`,
   `meus-dados/config.json`, `meus-dados/contexto.json` (anexos disponíveis) e
   `meus-dados/registro.json`. Esvaziar decisões de dias
   anteriores em `meus-dados/decisoes.json`: decisão velha não vale para plano novo. Se
   `vagas.json` foi alterado há menos de 1 hora, outra sessão pode estar rodando: pergunte
   antes de continuar.
2. **Triagem** (`/radar-triagem`): coletar, cortar, dar nota, publicar.
3. **Análise** (`/radar-analise`) das `fit.vagas_trabalhadas_por_dia` melhores acima do mínimo,
   uma por vez. Menos vagas boas: trabalhar as que houver e dizer isso.
4. **CV** (`/radar-cv`) para cada vaga analisada, com o preview conferido.
5. **Pessoas** (`/radar-pessoas`) só para as vagas trabalhadas. Mapa, sem mensagem.
6. **Publicar.** `bin/radar validar`, `bin/radar gerar`, garantir o painel no ar e mandar um
   resumo curto: quantas vagas, quais trabalhadas, o que espera decisão.
7. **Prazos.** Listar o que venceu: candidaturas sem resposta há `rotina.follow_up_dias` dias
   (com sugestão de próximo passo), aprovações paradas há `rotina.aprovado_alerta_dias` dias, e
   triagem parada (`bin/radar expirar`, sem `--aplicar` até a pessoa concordar).
8. **Vigiar a fila** `meus-dados/decisoes.json` (o painel grava cada clique ali). Decisões
   escritas na conversa valem igual.
9. **Processar as decisões:**
   - `aprofundar`: `/radar-analise` + `/radar-cv` + `/radar-pessoas` e devolver ao painel;
   - `ajustar`: reescrever conforme `nota_ajuste`, voltar o status para `proposto` com o mesmo
     id, regenerar e avisar;
   - `pular` em vaga: registrar como Descartada no histórico, com o motivo se houver;
   - `pular` em pessoa: só confirmar;
   - `aprovar` em vaga: entra na fila de execução;
   - `aprovar` em pessoa: fica marcada para contato (o contato é da pessoa; nada é enviado);
   - `nova_busca`: a triagem do dia já foi descartada; rodar `/radar-triagem` de novo
     ampliando a janela ou variando as palavras-chave.
10. **Executar os aprovados** com `/radar-aplicar`: UMA confirmação final na conversa listando
    o que veio aprovado, e só então, uma vaga por vez, com o checkpoint do formulário.
11. **Fechar.** Histórico atualizado, `decisoes.json` vazio, `bin/radar validar`,
    `bin/radar gerar`, e o resumo do dia: feito, pendente, próximo passo com data.

## Regras invioláveis

- Nenhuma candidatura, mensagem ou convite sai sem aprovação da pessoa (painel + ok final na
  conversa, ou aprovação escrita na conversa). Sem resposta, o plano fica no painel e a
  rotina para.
- Senha, conta nova, captcha, verificação, campo de documento, dados bancários e
  autodeclaração de diversidade: sempre da pessoa.
- Fato em nome da pessoa só de `perfil.json`, `fatos.md` ou confirmação na conversa.
- Campo vazio no config significa perguntar, nunca chutar.
- Pedido de login, captcha ou aviso de comportamento incomum do LinkedIn ou de um ATS:
  parar, avisar, não insistir.

## Dados e comandos

Esquemas em `docs/esquemas.md`. Tudo da pessoa fica em `meus-dados/` (fora do git).

| Comando | Para quê |
|---|---|
| `bin/radar validar` | conferir esquemas e consistência (rode depois de editar JSON) |
| `bin/radar gerar` | regenerar o painel |
| `bin/radar painel` | subir o painel com botões ao vivo (confira antes com `lsof -ti tcp:8322`) |
| `bin/radar marcar <id> <status>` | mudar status com trava (use com o painel aberto) |
| `bin/radar proximo-id vaga\|pessoa` | próximo id livre (max+1, nunca o tamanho da lista) |
| `bin/radar expirar [--aplicar]` | triagem parada sai da mesa |
| `bin/radar arquivar` | fechar a leva corrente em `meus-dados/arquivo/leva-N` |

Painel aberto por duplo clique (`meus-dados/painel/index.html`) = modo leitura, decisões pela
barra "Copiar para o chat". Servido pelo `bin/radar painel` = botões ao vivo.

## Continuidade

- "Como está o pipeline": ler `registro.json`, resumir por status, apontar follow-ups vencidos.
- Atualizações da pessoa ("me chamaram", "recusaram", "sumiram"): atualizar o histórico e
  propor o próximo passo.
- Vaga mandada fora da rotina: `/radar-analise`, mesmo Radar, mesmo fluxo.
