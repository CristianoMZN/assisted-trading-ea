# Tasks

## 1. Persistir e atualizar o contexto macro fora da API

- [x] 1.1 Criar migração Alembic e modelo de execuções macro por instrumento, com conteúdo, fontes/RSS, horários, estado e versões; verificar que a migração preserva análises anteriores e que os campos podem ser consultados no SQLite.
- [x] 1.2 Implementar gravação transacional e leitura da última execução utilizável por `WIN`/`WDO`, com validade configurável de 15 minutos; verificar por testes os casos de sucesso, `no_relevant_news`, falha posterior, vencimento, isolamento de instrumentos e gravação concorrente.
- [x] 1.3 Adicionar `python -m backend refresh-macro --instrument WIN|WDO` sem mudar o comando que inicia o servidor; verificar código de saída, saída sem segredos e persistência usando provedor simulado.
- [x] 1.4 Documentar migração, configuração de validade e comando em `backend/README.md`/`.env.example`; verificar que os exemplos usam a mesma base do servidor e funcionam sem iniciar o Uvicorn.

## 2. Tornar a pesquisa macro válida e apropriada para cada instrumento

- [x] 2.1 Ajustar prompts e formato estruturado para WDO e WIN, preservando fonte HTTPS consultada, fato e efeito relativo ao instrumento; verificar em testes que saída WDO não é aplicada como direção de WIN e que `no_relevant_news` continua válido.
- [x] 2.2 Tratar com diagnóstico seguro os desvios `invalid_model_output` de resumo e itens, com no máximo uma nova tentativa no comando e sem fabricar fonte/fato; verificar testes para campos ausentes/extras, URL não permitida, texto inválido, falha web e resultado recuperado.
- [x] 2.3 Mover a coleta RSS para o comando e armazenar seus estados/evidências junto ao contexto macro; verificar que falha de feed é distinguida de ausência de notícia e que a rota HTTP não consulta feeds.
- [x] 2.4 Atualizar a documentação dos modelos, prompts e limites de pesquisa e verificar por teste de integração com respostas gravadas que o comando persiste o resultado completo e suas versões sem credencial.

## 3. Usar cache, técnica e decisão na rota online

- [x] 3.1 Trocar `analyze_news`/RSS da rota por leitura do cache do mesmo instrumento e manter interpretação técnica seguida de decisão; verificar em testes a ordem das chamadas, a reutilização do cache e a ausência de acesso web em `POST /v1/analyze`.
- [x] 3.2 Responder `macro_context_unavailable` em HTTP 503 quando faltar contexto utilizável, sem decisão acionável, e preservar `no_signal` por indicadores insuficientes; verificar os envelopes 1.1, a auditoria e os casos de cache ausente, vencido, inválido e `no_relevant_news`.
- [x] 3.3 Revalidar `sent_at`, cotação e prazo macro após os modelos, definir criação/expiração da resposta no fim e impedir decisão vencida com `stale_market_snapshot`; verificar testes com relógio controlado e validar as respostas pelo contrato 1.1.
- [x] 3.4 Persistir evidências e versões macro/técnica/decisão com vínculo ao registro de cache, registrar durações por etapa e atualizar `contracts/backend-v1.md`/`backend/README.md`; verificar testes de auditoria e que logs/respostas omitem segredos.

## 4. Validar o backend isoladamente no Hopscotch

- [x] 4.1 Preparar exemplo de snapshot com horários atuais e roteiro Hopscotch para WDO e WIN; verificar que o POST reproduz o contrato 1.1 sem depender de fixture com data antiga.
- [x] 4.2 Executar o comando macro real para o instrumento de teste e conferir no SQLite estado, fontes, versões e validade; quando houver `invalid_model_output`, registrar o diagnóstico seguro e corrigir o formato antes de prosseguir.
- [ ] 4.3 Executar no Hopscotch os cenários de cache válido, `no_relevant_news`, cache ausente/vencido, falha do provedor, snapshot vencido e resposta acionável/`no_signal`; verificar códigos HTTP, `request_id`, evidências, expiração e ausência de chamada web durante o POST.
- [ ] 4.4 Comparar durações do POST com a linha de base anterior e registrar o resultado observado; só considerar o backend pronto quando os testes do Hopscotch passarem, sem inferir melhora na taxa de acerto.

## Workflow follow-up

- Após a validação do backend no Hopscotch, retomar as tarefas pendentes de `redesign-ea-trading-ticket-manual-analysis` no MetaTrader do usuário.
