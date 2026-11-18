# Fontes de vaga

De onde a varredura lê vagas, como lê e por que as outras ficaram de fora. O código mora em
`radar/varredura.py` (LinkedIn) e `radar/fontes.py` (Gupy, Sólides e o leitor de JSON-LD).

## As três fontes

| Fonte | Quando entra | Como lê | Link da vaga |
|---|---|---|---|
| LinkedIn | toda busca | endpoint público `jobs-guest`, HTML (detalhes em `linkedin-tecnico.md`) | `linkedin.com/jobs/view/{id}` |
| Gupy | buscas no Brasil | JSON da busca do portal: `portal.gupy.io/api/job-search/jobs?jobName=…&limit=50&offset=…` | `{empresa}.gupy.io/jobs/{id}` |
| Sólides | buscas no Brasil | JSON da busca do portal: `vagas.solides.com.br/api/vacancies?title=…&take=20&page=…` | `{empresa}.vagas.solides.com.br/vaga/{id}` |

As três ficam ligadas por padrão. Para desligar uma, liste só as que quer em
`config.json > rotina > fontes`, por exemplo `["linkedin", "gupy"]`. Para uma coleta
avulsa: `bin/radar varrer coleta --fontes gupy,solides`.

Gupy e Sólides são portais de ATS: a vaga já vem com o link de candidatura da empresa, que
vai para `url` e `url_candidatura`, e o `bin/radar ats` não é necessário. Na coleta eles
rodam antes do LinkedIn, então a mesma vaga publicada nos dois fica com o link do ATS e a do
LinkedIn sai como repetida no `varrer filtra`.

### Ids

O id da coleta diz de onde a vaga veio e basta para montar o link:

- LinkedIn: o número da vaga (`4471678311`);
- Gupy: `gupy-{empresa}-{id}` (`gupy-asaas-12836874`);
- Sólides: `solides-{empresa}-{id}` (`solides-inchurch-940811`).

`varrer descricao` e `varrer checa` aceitam qualquer um desses ids e também o link de uma
vaga em qualquer site.

### Regras da coleta nos portais

- Só buscas cujo local é no Brasil (`Brazil`, `Brasil` ou `Cidade, Estado, Brazil`): os
  dois portais só têm vaga brasileira. Região ("Latin America") e outros países ficam só no
  LinkedIn.
- Busca por cidade fica com as vagas daquela cidade e as remotas.
- Os dois devolvem do mais novo para o mais velho. A página que passa da janela de horas
  encerra a palavra-chave; o que veio fora da janela o `varrer filtra` corta, como no
  LinkedIn.
- A mesma palavra-chave na mesma cidade roda uma vez por fonte.
- Ficam de fora: o "banco de talentos" da Gupy (não é vaga) e, na Sólides, vaga desativada
  ou que parou de receber currículo.
- Salário só quando a empresa escolheu mostrar a faixa (Sólides), com `salario_fonte:
  "publicada na vaga"`.
- Pausa de 2 a 4 segundos entre chamadas. Portal que não responde marca a busca como
  incompleta, igual ao LinkedIn.

### A vaga ainda está aberta?

Para vaga fora do LinkedIn, `varrer checa` lê o `JobPosting` em JSON-LD da página, o dado
estruturado que os sites de vaga publicam para o Google:

- `fechada: true`: a página deu 404/410, mandou para outro endereço (a Gupy manda a vaga que
  sumiu para a tela de login) ou o `validThrough` já passou;
- `fechada: false`: a página tem a vaga e o prazo não venceu;
- `fechada: null`: a página está no ar mas sem `JobPosting`. Abra e confira.

O mesmo leitor serve para o link de uma vaga em outros sites que publicam `JobPosting`
(Catho, InfoJobs, Vagas.com.br, Empregos.com.br, Trabalha Brasil): uma página, quando você
pede, nunca uma varredura.

### Cuidados

Os dois JSONs não são API documentada: são a chamada que a própria página de busca faz.
Podem mudar sem aviso. Os testes (`TestFontes`) guardam o formato de novembro de 2026; se a
coleta de uma fonte zerar de repente, o formato mudou.

Os termos de uso da Gupy para candidatos proíbem "agregar, copiar ou duplicar" partes da
plataforma; o robots.txt dela libera tudo. A Sólides não publica termos para candidatos e o
robots.txt libera tudo. O Radar lê para uma pessoa decidir onde se candidatar, em ritmo de
pessoa, e não republica nada. Se isso não serve para você, tire a fonte de
`rotina.fontes`.

## Por que não as outras

Pesquisa de 18/11/2026 com os dez maiores sites de vaga do Brasil (audiência pela
Similarweb e pela Semrush). Nenhum tem API pública para ler vagas: as APIs que existem são
para a empresa publicar.

| Site | Por que não entrou |
|---|---|
| Indeed | busca responde 403 com captcha; a API de busca (Publisher) foi encerrada; repete o que já está nos ATS |
| Glassdoor | 403 com desafio; a API antiga responde 410; hoje faz parte do Indeed |
| InfoJobs e Catho | do mesmo grupo e com o mesmo estoque; dá para ler pela página, mas os termos dos dois proíbem robôs. Candidatos a uma fonte opcional, desligada por padrão |
| Vagas.com.br | termos proíbem reproduzir o conteúdo; busca literal, pouca vaga de produto e tecnologia |
| Rio Vagas | fácil de ler (WordPress, com RSS), mas só Rio de Janeiro e perfil operacional |
| Empregos.com.br | candidatura provavelmente paga e pouco de tecnologia |
| Jooble | tem API oficial com chave pedida por formulário; não testada |
| Emprega Brasil (Sine) | exige login gov.br |
