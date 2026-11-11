# Mudanças

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
