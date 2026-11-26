# Hoppscotch validation of backend contract 1.1

## Enviar um snapshot WDO novo a cada clique

Antes do teste, prepare um contexto macro válido para WDO com `.venv/bin/python -m backend refresh-macro --instrument WDO` e inicie o backend com `.venv/bin/python -m backend`, usando o mesmo `DATABASE_URL`. No Hoppscotch, configure:

1. Método e URL: `POST http://127.0.0.1:9000/v1/analyze`.
2. **Body**: tipo `application/json`, modo raw, contendo **somente** `<<freshMarketSnapshot>>`, sem aspas nem chaves adicionais.
3. **Pre-request Script**: cole todo o conteúdo de [`hoppscotch-wdo-pre-request.js`](hoppscotch-wdo-pre-request.js). Edite o objeto `input` no início do script para definir cotação, propriedades do símbolo, quantidade e limites de risco do teste.
4. Clique **Send**. O script cria um novo `request_id`, `sent_at`, horário da cotação, janela, fluxo e 20 candles M5 antes de cada envio. Confira no request efetivamente enviado que o `request_id` muda e que `sent_at` e `current_quote.timestamp` estão próximos do horário UTC atual.

Não cole no Body um JSON gerado anteriormente. O último `stale_market_snapshot` registrado em 26/11/2026 chegou às `22:45:38 UTC` com `sent_at` e cotação de `22:21:58 UTC`, atraso de 23 minutos e 40 segundos. A requisição foi recebida; o backend a classificou como vencida antes de chamar os agentes. O limite local de 300 segundos não pode aceitar esse corpo antigo.

O script usa preços e candles **sintéticos**: serve para testar o transporte, o contrato e a análise do backend com os parâmetros informados, sem representar mercado ao vivo ou uma recomendação operacional. Se usar dados reais, atualize a cotação e os candles juntos; alterar apenas timestamps torna o snapshot incoerente. O contexto macro é separado e precisa estar válido para WDO. Se ele faltar, a resposta esperada é HTTP 503 `macro_context_unavailable`.

Se ainda aparecer `Snapshot ou cotação venceram antes da análise.`, examine o request enviado, não apenas o texto no editor do Body. Se o Body contiver um UUID/horário antigo ou o literal `<<freshMarketSnapshot>>`, corrija o vínculo do script e remova qualquer variável de request ou coleção com esse mesmo nome que esteja prevalecendo sobre a variável definida pelo script. Se a mensagem disser `durante a análise`, os agentes terminaram após o prazo do snapshot; isso é um caso distinto.

O backend usa `MARKET_SNAPSHOT_MAX_AGE_SECONDS` para limitar a idade de `sent_at` e da cotação, inclusive depois das chamadas dos modelos. O valor padrão é 30 segundos; para testes sintéticos de integração pode ser configurado até 300 segundos no ambiente do processo do backend, seguido de reinício. Isso não aumenta a validade do cache macro. No ambiente local deste projeto, `.env` já contém 300 segundos.

Para gerar JSON pelo terminal em vez do script, use os comandos abaixo e envie o corpo imediatamente. Esse método exige gerar e colar um novo JSON em **cada** POST:

```bash
.venv/bin/python -m scripts.hopscotch_snapshot --instrument WDO --broker-symbol WDOZ26 --bid 5422.0 --ask 5422.5
.venv/bin/python -m scripts.hopscotch_snapshot --instrument WIN --broker-symbol WINZ26 --bid 130000 --ask 130005
```

Check `schema_version: 1.1`, the same `request_id`, and valid `created_at`/`expires_at` in every response. For a prepared macro cache, inspect `sources` for `macroeconomic_news` and original `valid_until`, `cache_id`, model and prompt version; compare with the row in SQLite. Test `no_relevant_news` by refreshing with that validated result, and missing/expired cache by using a fresh database or waiting beyond `MACRO_VALIDITY_MINUTES`. Check HTTP 503 `macro_context_unavailable` for missing cache, HTTP 503 for model failure, and HTTP 200 `no_signal` for old snapshots. With a current cache and snapshot, check either validated `actionable` or reasoned `no_signal`. Confirm server logs contain no `macro_news`, web or RSS collection stage during POST and record stage durations for comparison with the earlier baseline.

## Validation record — 2026-11-26

- Alembic is at `0005_analysis_macro_link` (head). The local SQLite database contains historical macro executions.
- A real `refresh-macro --instrument WDO` attempt was recorded as macro execution `16`: `state=unavailable`, `error_code=provider_unavailable`, safe diagnostic `OpenRouter could not be reached.` It has no `valid_until`; no new usable context was created. This is a provider connectivity failure, not `invalid_model_output`.
- A later WDO attempt (`17`) returned `research_unavailable`. A separate Hoppscotch call to OpenRouter using `upstage/solar-mini-4-5` returned a completion with `web_search_requests=1` and `tool_calls_executed=1`. This establishes that the key, model, and web search worked for that smaller request. It did not test the refresh command's required `web_fetch`, strict JSON schema, or full macro prompt. The response's generated URL should not be treated as validated macro evidence.
- WDO attempt `18` returned `invalid_model_output` for `transmission_channel` after the one allowed retry. The original response was not stored, so its exact invalid value cannot be recovered. Prompt v7 now states the non-empty 300-character limit and discards items without a source-backed mechanism; the validator now distinguishes wrong type, empty text, and excess length without logging the text.
- WDO attempt `19` completed with `state=available` and one macro item. SQLite confirms a summary, an HTTPS source URL, non-empty item fields, a model ID, prompt version `macroeconomic-news-v7`, and no error code. It completed at `2026-11-26 22:10:38 UTC` and retained the configured 15-minute validity through `22:25:38 UTC`. The source page itself was not independently fetched by this validation session; this check covers the stored record and CLI result.
- The Hoppscotch POST with request ID `a4c53919-1cc0-4a76-8888-970684e2037c` first arrived with a 39-second-old snapshot against the then-configured 30-second limit. After the local limit was raised to 300 seconds, a retry with the same request ID read macro cache `19` and completed technical interpretation, then returned `invalid_model_output` because the decision model's `scenario` failed local validation. The old diagnostic combined wrong type, empty text, and excess length; the raw model response was not stored. Decision prompt v2 now requests a short explanation and the validator reports these cases separately.
- The last previously successful WDO execution (`12`) has a summary, seven items, RSS evidence, model ID, and prompt version `macroeconomic-news-v5`. Its original validity ended at `2026-11-26 19:33:19 UTC`, so it cannot validate the current v6 prompt or feed a current POST.
- Local tests for macro refresh, analysis API, and current snapshot generation passed (18 tests). These tests use simulated provider responses and do not count as Hoppscotch validation.
- Hoppscotch could open, but its browser could not connect to this workspace's `127.0.0.1:9000`. No Hoppscotch scenario was marked complete. The earlier POST latency baseline and a comparable new measurement are not available in the project records inspected here.

To finish the manual check in the browser that shares the backend's network, first obtain a fresh successful refresh for each instrument. For every POST, generate a new snapshot immediately before sending it. Record the HTTP status, `request_id`, response status or error code, macro cache ID and validity, `created_at`/`expires_at`, and server stage durations. Exercise the valid, `no_relevant_news`, missing/expired, provider failure, stale snapshot, `actionable`, and `no_signal` cases. Compare the measured POST durations with a recorded pre-change baseline; do not infer a latency improvement or trading accuracy from the architecture alone.
