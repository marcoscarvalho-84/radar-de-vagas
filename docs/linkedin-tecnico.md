# LinkedIn: o que aprendemos na prática

Notas técnicas de meses de uso real. O LinkedIn muda sem aviso; se algo aqui parou de valer,
abra uma issue ou um PR com a data e o que mudou.

## Coleta: o endpoint público

`https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=...&location=Brazil&f_TPR=r172800&start=0`

- Funciona sem login e devolve HTML com os cards: o id sai de `urn:li:jobPosting:(\d+)`,
  o título de `base-search-card__title`, a empresa de `base-search-card__subtitle`, o local de
  `job-search-card__location` e a data de `datetime="..."`.
- `f_TPR` (janela em segundos: `r86400` = 24h, `r172800` = 48h) e `location` funcionam aqui.
- **Pagina de 10 em 10 pelo `start`.** Um laço que anda de 25 em 25 corta tudo na primeira
  página. Se uma palavra-chave devolve exatamente 10, 20 ou 30, desconfie do passo.
- **Uma palavra-chave por busca.** A busca não respeita `OR` nem aspas; misturar termos faz o
  mais comum engolir os outros.
- **Parada por palavra-chave, não global.** Palavras se sobrepõem; parar quando a página não
  traz id novo para a coleta inteira mata a 2ª página de quase todas.
- **429 é normal.** Espera crescente (30s, 60s, 90s...) e 3 a 6 segundos entre chamadas. Se
  insistir, pare: a coleta registra a busca como incompleta.
- **macOS em repouso** estica cada `sleep` e cada conexão: rode sob `caffeinate -i`.

## Filtro de título

Sempre por palavra inteira (`\b...\b`). Por substring, "ux" casa com "a**ux**iliar" e "ui" com
"máq**ui**nas", e a lista enche de vagas de outra área, escondendo que a coleta veio magra.

## Ler a descrição

1. `bin/radar varrer descricao <id>` usa `jobs-guest/jobs/api/jobPosting/{id}`.
2. Se vier vazia, WebFetch no permalink `https://www.linkedin.com/jobs/view/{id}` costuma
   entregar a descrição completa e campos que a interface logada esconde (modelo, nível,
   contrato).
3. No navegador logado, o painel de descrição trava em "skeleton" com frequência: rolar o
   painel da direita depois de clicar no card destrava às vezes. Não martele: skeleton
   repetido cheira a limite de requisições.

Vaga fechada: o corpo traz "No longer accepting applications" (ou 404/410).

## Busca logada

A busca logada passou a ignorar filtros de URL (`geoId`, `f_WT`, `f_E`, `sortBy`) e não
oferece mais "Worldwide" como local. Para vagas internacionais, nomeie um país real. Muitas
vagas "United States (Remote)" exigem autorização de trabalho nos EUA: confira antes de
gastar análise.

## Formulários no navegador

- **Texto longo:** digitar caractere a caractere em `<textarea>` pode perder letras sem
  erro visível (o eco da ferramenta mostra o texto certo). Prefira preencher o campo
  diretamente (`form_input` no Claude in Chrome) e confira depois comparando o
  **comprimento** do valor com o texto original. Em campos `contenteditable`, clique dentro
  do texto, confirme o foco e só então digite.
- **"Salvar" nem sempre salva.** Recarregue e confira.
- **Anexo de arquivo:** o upload aceita caminho absoluto com espaços. No Easy Apply não há
  `input[type=file]` no DOM até o clique em "Upload resume", e o clique abre o seletor
  nativo do sistema. O que funcionou: interceptar `HTMLInputElement.prototype.click` para,
  quando `type === 'file'`, anexar o input ao `body` com um `aria-label` conhecido sem abrir
  o seletor; clicar em "Upload resume"; achar o input pelo `aria-label`; fazer o upload nele;
  restaurar o `click` original.
- **CV armazenado:** o Easy Apply usa o último CV enviado por padrão. Troque pelo da vaga.
- Alguns ATS derrubam o anexo depois que o resto é preenchido: confira o nome do arquivo
  logo antes de enviar.

## Ritmo

Uma ação por vez, ritmo de pessoa. Pedido de login, captcha ou aviso de comportamento
incomum: parar e devolver para a pessoa. O Radar não contorna nada disso.
