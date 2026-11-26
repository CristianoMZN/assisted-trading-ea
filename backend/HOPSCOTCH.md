# Hopscotch validation of backend contract 1.1

Run migrations and `refresh-macro` from the repository root, using the same `DATABASE_URL` and model settings as the server. Start `.venv/bin/python -m backend`. In Hopscotch, create a `POST` request to `http://127.0.0.1:9000/v1/analyze` with `Content-Type: application/json`.

Generate a current test body immediately before each POST and paste its JSON into Hopscotch:

```bash
.venv/bin/python -m scripts.hopscotch_snapshot --instrument WDO --broker-symbol WDOZ26 --bid 5422.0 --ask 5422.5
.venv/bin/python -m scripts.hopscotch_snapshot --instrument WIN --broker-symbol WINZ26 --bid 130000 --ask 130005
```

The generated candles and prices are **synthetic transport test data**, not live market evidence or a trading recommendation. Use the actual broker symbol, tick size, tick value and quote from MetaTrader for an operational test. Replace the generated prices and candles accordingly; keep timestamps current and internally consistent. Generate a fresh body for every request because `sent_at` and `current_quote.timestamp` expire after 30 seconds by default.

Check `schema_version: 1.1`, the same `request_id`, and valid `created_at`/`expires_at` in every response. For a prepared macro cache, inspect `sources` for `macroeconomic_news` and original `valid_until`, `cache_id`, model and prompt version; compare with the row in SQLite. Test `no_relevant_news` by refreshing with that validated result, and missing/expired cache by using a fresh database or waiting beyond `MACRO_VALIDITY_MINUTES`. Check HTTP 503 `macro_context_unavailable` for missing cache, HTTP 503 for model failure, and HTTP 200 `no_signal` for old snapshots. With a current cache and snapshot, check either validated `actionable` or reasoned `no_signal`. Confirm server logs contain no `macro_news`, web or RSS collection stage during POST and record stage durations for comparison with the earlier baseline.

## Validation record — 2026-11-26

- Alembic is at `0005_analysis_macro_link` (head). The local SQLite database contains historical macro executions.
- A real `refresh-macro --instrument WDO` attempt was recorded as macro execution `16`: `state=unavailable`, `error_code=provider_unavailable`, safe diagnostic `OpenRouter could not be reached.` It has no `valid_until`; no new usable context was created. This is a provider connectivity failure, not `invalid_model_output`.
- A later WDO attempt (`17`) returned `research_unavailable`. A separate Hoppscotch call to OpenRouter using `upstage/solar-mini-4-5` returned a completion with `web_search_requests=1` and `tool_calls_executed=1`. This establishes that the key, model, and web search worked for that smaller request. It did not test the refresh command's required `web_fetch`, strict JSON schema, or full macro prompt. The response's generated URL should not be treated as validated macro evidence.
- WDO attempt `18` returned `invalid_model_output` for `transmission_channel` after the one allowed retry. The original response was not stored, so its exact invalid value cannot be recovered. Prompt v7 now states the non-empty 300-character limit and discards items without a source-backed mechanism; the validator now distinguishes wrong type, empty text, and excess length without logging the text.
- WDO attempt `19` completed with `state=available` and one macro item. SQLite confirms a summary, an HTTPS source URL, non-empty item fields, a model ID, prompt version `macroeconomic-news-v7`, and no error code. It completed at `2026-11-26 22:10:38 UTC` and retained the configured 15-minute validity through `22:25:38 UTC`. The source page itself was not independently fetched by this validation session; this check covers the stored record and CLI result.
- The last previously successful WDO execution (`12`) has a summary, seven items, RSS evidence, model ID, and prompt version `macroeconomic-news-v5`. Its original validity ended at `2026-11-26 19:33:19 UTC`, so it cannot validate the current v6 prompt or feed a current POST.
- Local tests for macro refresh, analysis API, and current snapshot generation passed (18 tests). These tests use simulated provider responses and do not count as Hoppscotch validation.
- Hoppscotch could open, but its browser could not connect to this workspace's `127.0.0.1:9000`. No Hoppscotch scenario was marked complete. The earlier POST latency baseline and a comparable new measurement are not available in the project records inspected here.

To finish the manual check in the browser that shares the backend's network, first obtain a fresh successful refresh for each instrument. For every POST, generate a new snapshot immediately before sending it. Record the HTTP status, `request_id`, response status or error code, macro cache ID and validity, `created_at`/`expires_at`, and server stage durations. Exercise the valid, `no_relevant_news`, missing/expired, provider failure, stale snapshot, `actionable`, and `no_signal` cases. Compare the measured POST durations with a recorded pre-change baseline; do not infer a latency improvement or trading accuracy from the architecture alone.
