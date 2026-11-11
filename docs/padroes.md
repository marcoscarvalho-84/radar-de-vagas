# Padrões de conteúdo

Regras de FORMA que valem para qualquer pessoa usando o Radar. O CONTEÚDO (seus fatos, suas
provas, sua voz, suas preferências) vem de `meus-dados/perfil.json`, `meus-dados/fatos.md` e
`meus-dados/config.json`, preenchidos pelo questionário. Onde um padrão daqui tem um número
configurável, o nome do campo do config aparece entre parênteses.

Cada padrão existe porque a alternativa deu errado pelo menos uma vez.

## 1. Princípios inegociáveis

1. **Verdade documental.** Fato em seu nome sai só do perfil confirmado, do `fatos.md` ou do
   que você confirmar na conversa. Reordenar, enfatizar e reescrever: sim. Inventar, inflar ou
   arredondar para cima: nunca. Um número inflado derruba a candidatura inteira na entrevista.
2. **Aprovação explícita, item a item, antes de qualquer ação pública.** Candidatura, mensagem,
   convite, post: só depois de mostrar exatamente o que vai sair e receber o seu ok. Aprovar um
   item não aprova outro. Sessão nova pede aprovação nova. Item não mencionado é item não
   aprovado. Aprovar no painel põe na fila; o envio ainda pede um ok final na conversa.
3. **Limites do navegador.** Senha, conta nova, captcha, verificação: sempre seus. Campos de
   documento, dados bancários e autodeclarações seguem `config.formulario`.
4. **Radar primeiro.** Antes de trabalhar uma vaga, conferir se ela já passou pelo Radar
   (vagas, histórico e levas arquivadas). Nunca aplicar duas vezes na mesma vaga.
5. **O idioma espelha a vaga e o formulário.**
6. **Ritmo humano** no navegador, uma ação por vez. Qualquer aviso de restrição, comportamento
   incomum ou captcha: parar tudo e avisar. Não insistir.

## 2. Triagem e nota de fit

- **Nota de 0 a 100** contra o perfil, ponderada em cinco dimensões (`fit.pesos`): domínio,
  senioridade, porta (a trilha de carreira da vaga), escopo e modelo de trabalho.
- **Uma frase de justificativa honesta** (`fit_resumo`): o que puxa a nota para cima e o que
  puxa para baixo. Nada de "ótimo encaixe" sem dizer por quê.
- **Red flags** em lista curta, uma frase cada: escopo confuso, senioridade rebaixada,
  acúmulo de funções (design mais marketing mais social media), modelo fora do aceito,
  empresa onde você já tem candidaturas sem resposta.
- **Leitura da nota:** 85 ou mais é encaixe raro; 70 a 84, bom; 60 a 69, vale com um ângulo
  forte; abaixo de 60, só se você pedir.
- **Corte automático** pelas regras de `buscas.json > corte`. Cortada não vai para a mesa:
  entra só na contagem do `resumo_busca` ("212 vagas, 9 lidas, 3 cortadas").
- **Triagem larga, trabalho estreito.** Vaga plausível vai para a mesa como triagem (com fit);
  só as melhores acima do mínimo (`fit.fit_minimo_para_aprofundar`) viram vaga trabalhada, no
  máximo `fit.vagas_trabalhadas_por_dia` por dia. Nunca completar a cota com vaga ruim.
- **Desempate:** entre notas parecidas (até 5 pontos), a vaga mais recente ganha.
- **Uma frente por empresa.** No máximo uma vaga da mesma empresa trabalhada por vez.
  Concentrar várias candidaturas na mesma empresa não aumenta a chance; dilui a mensagem.

## 3. Análise completa de uma vaga

- **Contexto da empresa:** 3 a 6 buscas curtas (produto e tese, estágio e funding, notícias
  dos últimos 6 meses, cultura publicada, como design ou a sua área aparece em público).
  Saída: 3 a 5 pontos que viram gancho de narrativa.
- **Salário:** a faixa publicada vale mais que qualquer benchmark. Sem faixa, estimar com
  fonte citada (Glassdoor, Levels.fyi, pesquisas salariais recentes) e escrever "estimativa".
  `salario` sem `salario_fonte` é erro de padrão. Chute nunca aparece como fato.
- **Mapa de fit:** forças diretas (requisito ligado a uma prova com número), adjacências
  honestas (o que você cobre por analogia real) e lacunas verdadeiras, cada uma com a forma
  honesta de endereçá-la (o fato adjacente mais forte, sem fingir).
- **Ângulo em 1 frase:** a tese da candidatura, que CV, carta e respostas vão repetir.
- **Melhorias que a vaga sugere:** 1 a 3 ações concretas de perfil, portfólio ou conteúdo.
  Padrão entre vagas vale mais que observação isolada: a cada 5 vagas registradas,
  consolidar os requisitos que se repetem e você cobre mal.
- **Checkpoint:** ângulo e CV vão juntos para o painel. Você decide os dois de uma vez.

## 4. Pessoas a contactar

- Por vaga trabalhada, `pessoas.por_vaga` pessoas (padrão 3): o recruiter da vaga, o hiring
  manager provável e um head ou director da área ou um par sênior. Em empresa pequena, o
  founder entra no lugar de um deles.
- Para cada pessoa: nome, cargo, empresa, link `linkedin.com/in/...`, papel, grau de conexão e
  **uma linha do porquê** com fato verificável ("aparece no hiring team do anúncio", "lidera o
  time para o qual a vaga reporta").
- Conferir antes de propor: ainda está na empresa, não há convite pendente, e o grau. Conexão
  de 1º grau é marcada como tal: é caminho de indicação, outro tipo de conversa.
- **Nesta versão o Radar não escreve nota, convite nem mensagem.** Ele entrega o mapa de quem
  contatar e por quê; a abordagem é sua. (Rascunho de mensagem é um módulo futuro e, quando
  existir, segue o mesmo fluxo de aprovação.)
- Regra de convivência que vale desde já: quem não respondeu a uma mensagem não recebe uma
  segunda. Uma mensagem sem resposta é resposta.

## 5. CV

- **1 página A4**, gerado por `bin/radar cv`. O script aperta a densidade até caber; abaixo de
  0.92 é sinal de cortar texto de verdade; abaixo de 0.86 ele falha.
- **Preview conferido antes de mostrar:** quebras feias, viúvas, aperto.
- **Estrutura fixa:** nome, tagline em 2 linhas, local, contatos (do perfil), gancho em 2
  partes, positioning, "Why {Empresa}", experiência, ferramentas, idiomas.
- **O gancho** tem duas partes; a segunda (em cinza) começa sempre uma linha nova. Nada liga as
  duas: o template quebra a linha sozinho.
- **Muda por vaga:** tagline, a segunda parte do gancho quando render, positioning (reescrever
  20 a 40% mirando a vaga, com os mesmos fatos), a seção Why inteira e a ênfase das descrições
  (keywords reais da vaga, sem copiar frases do anúncio).
- **Nunca muda:** a lista de experiências, as datas e os fatos. Entrada antiga pode encurtar.
- **Receita do "Why {Empresa}":** 4 linhas, cada uma com um mini-rótulo de 3 a 6 palavras e 1
  a 2 frases de prova:
  1. o domínio ou problema da empresa onde você já operou;
  2. o seu diferencial central (definido no questionário);
  3. sistema, escala ou coerência;
  4. liderança ou senioridade IC, conforme a porta da vaga.
  Vaga com pedido muito específico: uma das linhas ataca isso com o fato real mais próximo.
- **Porta IC:** liderança aparece como prova de escopo, não de gestão.
- **Idioma:** `cv.idioma_padrao`; vaga só em outro idioma, perguntar antes de traduzir.
- **Arquivo:** `{Nome}-CV-{Empresa}-{Cargo}.pdf` com hífens, sem acento nem espaço, em
  `meus-dados/cvs/`, com o JSON de conteúdo ao lado (`cv-{empresa}.json`) para reajuste.
- **Racional:** 3 a 5 linhas do que mudou e por quê (`cv_racional`), sempre junto do CV.

## 6. Carta de apresentação

- Só quando o formulário pedir (`carta.quando`).
- 120 a 200 palavras (`carta.palavras_min/max`), 3 ou 4 parágrafos curtos, 1 página.
  Recrutador lê em 30 segundos.
- Arquivo `.md`: cabeçalho de contexto (vaga, ângulo, data), uma linha `---`, o corpo. Só o
  corpo vira PDF; nome e contatos vêm do perfil.
- Estrutura: por que esta empresa (1 ou 2 pontos reais da pesquisa), a prova mais forte ligada
  ao problema deles, o ângulo, um fecho sem implorar.

## 7. Formulário e candidatura

**Comprimento por tipo de campo**

| Campo | Tamanho |
|---|---|
| Curto (headline, pitch, 1 linha) | 1 frase com a prova mais forte para esta vaga |
| Médio ("why us", "about you") | 60 a 120 palavras, 2 a 3 parágrafos curtos |
| Longo (carta, "anything else") | 120 a 200 palavras, nunca mais |
| Com limite de caracteres | respeitar com folga de 10% |

**Estruturas de resposta** (adaptar por vaga, nunca colar cru)

- *Fale sobre você:* posicionamento em 1 frase, a prova mais relevante para ESTA vaga (com
  número), o que você faz hoje, e 1 frase do que busca (na porta da vaga).
- *Por que aqui:* 1 ou 2 pontos reais da pesquisa da empresa, cada um ligado a uma prova sua.
  Se a pesquisa não achou nada específico, perguntar o ângulo; nunca inventar admiração.
- *Por que você:* o ângulo, apoiado em 2 provas com número. Exigência que você não cobre:
  mostrar o adjacente real, sem fingir.
- *Pretensão:* do `config.remuneracao`. Vazio ou caso atípico (exterior, regime diferente,
  equity): perguntar. Texto livre: faixa, moeda e regime explícitos. Registrar o valor
  declarado.
- *Senioridade declarada:* `formulario.senioridade_declarada` ("nivel_da_vaga" declara o nível
  da própria vaga, a régua em que vão te avaliar).
- *Disponibilidade:* do config; nunca prometer data que não está lá.
- *Anos de experiência com X:* a conta honesta pelas datas do perfil. Não tem: responder o real.
- *Autorização de trabalho e visto:* do config; relocation ou visto: perguntar.
- *Por que está buscando:* honesto e neutro, uma frase, sem falar mal de ninguém.
- *Maior conquista:* um caso, em três tempos (contexto, o que você fez, resultado com número).
  Rodar os casos entre candidaturas.

**Nunca preencher sozinho:** a lista de `formulario.nunca_preencher` (documentos, dados
bancários, endereço completo, autodeclarações, senha, conta, captcha). **Sempre perguntar:**
`formulario.sempre_perguntar`.

**Checkpoint obrigatório antes de enviar:** listar na conversa TODAS as perguntas com as
respostas exatamente como estão no formulário, mais um screenshot da revisão, e esperar o ok.
Pediu ajuste: editar, reapresentar, esperar de novo. No Easy Apply do LinkedIn o checkpoint é
na última tela, antes do botão final (não tem volta).

**Depois de enviar:** screenshot da confirmação, registro no histórico com a data, e o
`bin/radar marcar <id> executado`. Conferir o nome do arquivo anexado logo antes do envio:
alguns ATS derrubam o anexo quando o resto do formulário é preenchido.

## 8. Estilo de escrita em seu nome

- Específico ganha de genérico: um fato com número vale mais que três adjetivos.
- Confiante, sem implorar e sem arrogância. Você mostra por que o problema deles e a sua
  prática se encaixam.
- História real antes de frase bonita.
- Nunca copiar frases do anúncio. Espelhar keywords com naturalidade: o ATS lê, mas quem decide
  é gente.
- No máximo uma frase de efeito por resposta longa (`estilo.max_frases_de_efeito_por_resposta`).
- As proibições pessoais de `estilo.proibicoes` (por exemplo travessão ou emoji) valem para
  todo texto novo escrito em seu nome.
- Nunca prometer resposta, prazo ou call em seu nome.

## 9. Dados e links

- `url` de vaga: o permalink `linkedin.com/jobs/view/{id}` ou a URL direta do ATS. Nunca a
  busca genérica nem a raiz do site. Sem permalink capturado, vazio (o painel esconde o link
  em vez de apontar para o lugar errado).
- `url` de pessoa: sempre `linkedin.com/in/...`.
- `cv` e `cv_preview` começam com `/cvs/` (é assim que o painel os serve).
- Ids sequenciais `vaga-N` e `pessoa-N`, sempre pelo `bin/radar proximo-id` (max+1, nunca o
  tamanho da lista).
- `adicionada_em` é o dia em que a vaga entrou no Radar. Datas em ISO; horários com fuso.
- O histórico (`registro.json`) recebe SOMENTE o que foi aprovado e executado.
- Item resolvido não sai do `vagas.json`: vira `executado` ou `recusado` e some da seção
  "Hoje", mas a análise continua visível no Pipeline.
- Com o painel aberto, status muda pelo `bin/radar marcar`, não à mão. Depois de qualquer
  edição manual: `bin/radar validar` e `bin/radar gerar`.

## 10. Ritmo e prazos

- **Follow-up:** candidatura sem resposta há `rotina.follow_up_dias` dias (padrão 7) aparece
  marcada no Pipeline com sugestão de próximo passo.
- **Aprovada parada:** depois de `rotina.aprovado_alerta_dias` (padrão 3) o painel alerta.
  Aprovação que não vira envio morre na fila, porque a vaga fecha. Um ritual curto de
  execução vale mais que outra varredura.
- **Triagem parada:** vaga de triagem sem decisão há `rotina.triagem_expira_dias` dias (padrão
  14) é sinalizada e sai da mesa com `bin/radar expirar --aplicar`.
- **Levas:** quando a busca muda de fase, `bin/radar arquivar` fecha a leva com um relatório
  honesto. O arquivo continua valendo para duplicata.
