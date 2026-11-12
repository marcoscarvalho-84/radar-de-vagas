# Questionário de configuração

O passo a passo que põe o Radar no SEU contexto. A skill `/radar-configurar` conduz estas
perguntas na conversa, um bloco por vez, e grava as respostas nos arquivos de
`meus-dados/`. Dá para parar no meio e continuar depois: ela retoma do primeiro bloco vazio.
Para refazer um bloco só: `/radar-configurar remuneração` (ou o nome do bloco).

Tempo total: 25 a 40 minutos na primeira vez. Os blocos 1 a 3 são os que mais pesam na
qualidade de tudo que vem depois; não pule.

Legenda: **→** onde a resposta é gravada · *padrão* o que vale se você não mudar.

---

## Bloco 0 · Antes de começar (2 min)

1. Você já viu a demonstração (`bin/radar demo`)? Se não, vale 3 minutos: fica mais fácil
   responder sabendo o que cada resposta muda no painel.
2. Você tem o Claude in Chrome conectado ao seu navegador, logado no LinkedIn?
   Sem ele o Radar ainda coleta, analisa e gera CV; só não aplica nem mapeia pessoas por você.
3. Quanto tempo por dia você consegue dedicar a DECIDIR (aprovar, descartar, ajustar)?
   15 minutos por dia rendem mais que 2 horas por semana: aprovação parada morre na fila.
   → `fit.vagas_trabalhadas_por_dia` (15 min ≈ 2 vagas) · *padrão 2*

## Bloco 1 · Perfil: a sua fonte de fatos (5 a 10 min)

Ver `/radar-perfil`. Se você passou pela tela de abertura (`bin/radar`, primeira vez), o
LinkedIn, o CV atual, o e-mail e o portfólio já estão lá: este bloco só confirma. As
perguntas de confirmação:

1. Como importar: export oficial do LinkedIn (recomendado), "Salvar em PDF" do perfil, ou
   leitura do perfil pelo navegador?
2. Seu nome como deve aparecer no CV, e em quantas linhas (ex.: "Ana" / "Souza").
   → `perfil.nome`, `perfil.nome_cv`
3. Quais contatos vão no CV: e-mail, LinkedIn, portfólio, telefone? (Telefone só se você quiser.)
   → `perfil.contatos`
4. Para cada experiência importada: o cargo e as datas estão certos? Alguma deve sair do CV?
   → `perfil.experiencias`

## Bloco 2 · Provas: o que você pode afirmar (10 min)

O bloco que mais muda a qualidade do CV. Fato sem número vira adjetivo.

1. Quais são as 5 a 10 conquistas com número que você pode defender numa entrevista?
   (métrica de negócio, tamanho de time, produtos, usuários, prazo)
   → `perfil.provas` e `fatos.md` (cada uma com data de confirmação)
2. Para cada experiência: qual era o escopo REAL? (o que era seu, tamanho do time, produtos,
   público). → `fatos.md`
3. O que você NÃO tem e costuma aparecer em vagas? (ferramenta, domínio, idioma, tipo de time)
   Saber isso evita resposta inflada. → `fatos.md`, seção "O que você não tem"
4. Qual é o seu diferencial central, aquilo que quase ninguém combina com o resto do seu
   perfil? Vira a linha 2 da seção "Why" de todo CV. → `config.cv.diferencial`

## Bloco 3 · Objetivo: o que você procura (5 min)

1. Quais **portas** você quer abrir? Uma porta é uma trilha de carreira com seus cargos.
   Parta das **posições desejadas** que você escreveu na tela de abertura
   (`contexto.json > posicoes`) e da sua trajetória: a rotina agrupa as posições em portas e
   pergunta se faltou alguma. Exemplo de uma pessoa de dados: "Análise" (Analista de Dados
   Sênior, Data Analyst) e "Liderança" (Coordenador de BI, Analytics Manager).
   Uma, duas, no máximo três. → `config.objetivo.portas`
2. Qual a senioridade mínima que faz sentido? (ex.: sênior) → `config.objetivo.senioridade_minima`
3. Em uma frase: o que você busca no próximo trabalho? → `config.objetivo.o_que_busca`
4. Domínios onde você é forte (ex.: fintech B2B, saúde, SaaS). → `config.objetivo.dominios_fortes`
5. Domínios ou empresas que você NÃO quer (ex.: tabaco, ex-empregador). → `config.objetivo.dominios_evitar`

## Bloco 4 · Onde e como trabalhar (3 min)

1. Cidade base. → `config.trabalho.cidade_base`
2. Modelos aceitos: remoto, híbrido, presencial? → `config.trabalho.modelos_aceitos`
3. Híbrido ou presencial só em quais cidades? → `config.trabalho.hibrido_ou_presencial_so_em`
4. Vagas internacionais entram? Em que regime (contractor, empresa local)?
   → `config.trabalho.aceita_internacional`, `config.trabalho.autorizacao_trabalho`
5. Vaga que exige visto ou relocation: descartar, considerar, ou perguntar caso a caso?
   → `config.trabalho.exige_visto_ou_relocation` · *padrão perguntar*

## Bloco 5 · Remuneração (3 min)

Nada aqui tem padrão. Campo vazio faz a rotina PERGUNTAR na hora do formulário.

1. Qual a regra da sua pretensão? (ex.: "a faixa publicada; sem faixa, o ponto médio da
   estimativa com fonte") → `config.remuneracao.regra`
2. Valores por regime, se quiser fixar: CLT mensal, PJ mensal, USD anual. → `config.remuneracao.*`
3. Abaixo de quanto você não aceita conversar? (fica só com você e com a rotina, nunca vai
   para formulário) → `config.remuneracao.piso`
4. Quando um formulário pergunta a última remuneração: responder (qual valor) ou perguntar
   antes? → `config.remuneracao.ultima_remuneracao` · *padrão perguntar*

## Bloco 6 · Formulários (3 min)

1. Disponibilidade para começar (imediata, 15 dias, 30 dias...). → `config.disponibilidade`
2. Quando o formulário pede o seu nível: declarar o nível da própria vaga, ou um nível fixo?
   → `config.formulario.senioridade_declarada` (`nivel_da_vaga` ou o nível fixo)
3. Além da lista padrão (documentos, banco, endereço, autodeclarações, senha), algum campo
   que nunca deve ser preenchido sem você? → `config.formulario.nunca_preencher`
4. Algum tema que sempre deve vir para você decidir? → `config.formulario.sempre_perguntar`

## Bloco 7 · Nota de fit (2 min)

1. Os pesos padrão são domínio 25, senioridade 20, porta 20, escopo 20, modelo 15. Algum pesa
   mais para você? (ex.: modelo remoto inegociável → modelo 30) → `config.fit.pesos`
2. A partir de qual nota uma vaga merece pesquisa completa e CV? → `config.fit.fit_minimo_para_aprofundar` · *padrão 60*

## Bloco 8 · Busca (5 min)

A primeira versão das buscas já existe se você respondeu **Posições** na tela de abertura:
cada posição virou uma busca no país do seu perfil. Aqui a rotina a deixa sob medida, lendo
as suas posições, o seu LinkedIn (`perfil.json`: cargos, headline, competências) e o texto
do seu CV (`anexos/cv-atual.txt`). Nada de cargo genérico ou de outra área: cada termo
proposto diz de onde veio.

1. Palavras-chave: cada posição em português e em inglês, os títulos equivalentes que o
   mercado usa para o mesmo trabalho e os níveis vizinhos que a sua trajetória sustenta.
   Quer tirar ou incluir alguma? → `buscas.json > grupos[].palavras_chave`
2. Locais da busca (país ou região: "Brazil", "Latin America", "Portugal"...). *padrão: o
   país do seu perfil* → `buscas.json > grupos[].local`
3. Janela: vagas das últimas 24 ou 48 horas? → `buscas.json > janela_horas` · *padrão 48*
4. Filtro de título: os termos que uma vaga da sua área tem que ter no título, os que
   marcam o seu nível e os que descartam na hora (funções vizinhas que não são a sua,
   níveis abaixo). A rotina propõe os três a partir das posições e do CV.
   → `buscas.json > filtro_titulo`

## Bloco 9 · CV e carta (3 min)

1. Idioma padrão do CV. → `config.cv.idioma_padrao`
2. Vaga em outro idioma: traduzir direto ou perguntar? → `config.cv.perguntar_antes_de_traduzir` · *padrão perguntar*
3. Carta: só quando o formulário pede, ou sempre que houver campo aberto? → `config.carta.quando`
4. Você tem uma fonte licenciada que quer no CV? (Se sim, os arquivos vão para
   `meus-dados/fontes/`; senão vale a Figtree, livre.)

## Bloco 10 · Voz e estilo (3 min)

1. O seu tom em três palavras (ex.: direto, caloroso, sem hype). → `config.estilo.tom`
2. O que nunca deve aparecer em texto seu? (ex.: travessão, emoji, "apaixonado por")
   → `config.estilo.proibicoes`
3. Tem um texto seu que soa como você (post, carta antiga)? Cole ou mande o link: serve de
   régua para as respostas de formulário. → `fatos.md`, seção "Voz"

## Bloco 11 · Pessoas (1 min)

1. Quantas pessoas mapear por vaga trabalhada? → `config.pessoas.por_vaga` · *padrão 3*
2. Os papéis padrão são recruiter da vaga, hiring manager provável e head ou par sênior.
   Quer trocar algum? → `config.pessoas.papeis`

## Bloco 12 · Rotina e prazos (2 min)

1. Horário da rotina diária (se for agendar). → `config.rotina.horario`
2. Depois de quantos dias sem resposta uma candidatura pede follow-up? → `config.rotina.follow_up_dias` · *padrão 7*
3. Depois de quantos dias uma aprovação parada vira alerta? → `config.rotina.aprovado_alerta_dias` · *padrão 3*
4. Depois de quantos dias a triagem sem decisão sai da mesa? → `config.rotina.triagem_expira_dias` · *padrão 14*
5. Prefere decidir pelo painel (cliques) ou pela conversa (texto)? As duas valem; a resposta
   só muda o que a rotina sugere no fim de cada dia.

---

## No fim

A skill mostra um resumo de uma tela com tudo que foi gravado, roda `bin/radar validar`,
e sugere o primeiro passo: `/radar-triagem` para a primeira varredura.
