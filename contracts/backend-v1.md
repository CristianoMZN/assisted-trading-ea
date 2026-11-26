# Contrato EA ↔ backend Python, versão 1

O EA faz `POST` periódico para `POST /v1/analyze` no backend Python/FastAPI configurado pelo cliente, com intervalo selecionável de 1 a 5 minutos. Não faz polling quando já existe posição aberta no símbolo. O backend deste repositório valida a requisição, calcula indicadores, coleta feeds RSS/Atom configurados, consulta OpenRouter e aplica validações determinísticas de risco. Mensagens usam UTF-8 e timestamps ISO 8601 em UTC. Versão desconhecida, corpo inválido ou resposta vencida sempre resulta em sem sinal.

## Requisição `market_snapshot`

- `schema_version`: exatamente `1.1`.
- `message_type`: `market_snapshot`.
- `request_id`: UUID para correlacionar resposta e log.
- `sent_at`: instante UTC da captura.
- `instrument`: `logical_symbol` (`WIN` ou `WDO`) e `broker_symbol` configurado.
- `symbol_properties`: `point`, `tick_size`, `tick_value_loss`, `tick_value_profit`, `stops_level_points` e `digits` obtidos do broker no momento da captura. Tick values estão na moeda da conta para um contrato por tick; valores ausentes/inválidos impedem recomendação acionável.
- `timeframe`: `M5`.
- `window`: `from` e `to` em UTC cobrindo a janela móvel de sete dias.
- `server_utc_offset_seconds`: diferença usada pelo EA para converter timestamps das barras do horário do servidor para UTC no momento da captura.
- `history_first_available_at`: primeiro horário local de histórico M5 disponível após sincronização; precisa ser anterior ou igual ao início da janela solicitada.
- `current_quote`: bid/ask/last, volume, flags e timestamp do último tick disponível; o backend pode usar a cotação para avaliar entrada a mercado.
- `tick_flow`: volume agregado de negócios com flags de compra/venda durante o intervalo desde o polling anterior. `classification_available` indica se o broker classificou negócios por lado; quando não, volumes ficam `null` e não podem ser tratados como zero.
- `candles`: candles M5 disponíveis dentro da janela, ordenados do mais antigo ao mais recente. Cada candle leva `timestamp`, OHLC, `tick_volume`, `real_volume`, `buy_volume` e `sell_volume`; volume real/agressor pode ser `null` quando o broker não o fornece.
- `unavailable_fields`: nomes dos campos de mercado que a instância não forneceu. Ausência não pode ser convertida em zero nem inferida.
- `preferences`: `risk_reward` (`1:2` ou `1:3`), `max_stop_points`, `max_loss_per_trade`, `round_trip_cost_per_contract`, `daily_loss_limit` e `contracts`; números finitos não negativos, com stop máximo, contratos e perdas máximas maiores que zero. Valores monetários usam a moeda da conta. `contracts` é a quantidade escolhida no EA e não concede ao backend autoridade para enviar ordens.

O período de sete dias é de calendário. Fechamentos de mercado e fins de semana podem reduzir a quantidade de candles; cada candle enviado deve ser válido e temporalmente dentro da janela.

## Resposta `analysis_response`

- `schema_version`: exatamente `1.1`; `message_type`: `analysis_response`; `request_id`: igual ao pedido.
- `created_at` e `expires_at`: timestamps UTC; a resposta só é acionável enquanto `now < expires_at`.
- `instrument`: deve corresponder ao pedido.
- `status`: `actionable` ou `no_signal`; indisponibilidade operacional é devolvida como envelope HTTP `error` (por exemplo, HTTP 503), não como decisão.
- `decision`: objeto para `actionable`, `null` para `no_signal`. Deve conter `direction` (`BUY`/`SELL`), `entry_type` (`MARKET`), preço de referência, `stop_loss`, `take_profit`, `risk_reward` (`1:2`/`1:3`), `scenario` e `confidence` (`low`/`medium`/`high`). O backend decide todos esses valores, exceto quantidade, que o cliente ajusta no EA.
- `reason_code` e `reason`: obrigatórios em `no_signal`, ambos `null` em `actionable`. `reason_code` é um identificador estável em `snake_case`; `reason` é uma explicação operacional curta e não contém raciocínio privado do modelo.
- `sources`: lista de blocos do backend (`technical`, `news`, `prediction_market`) com `status`, `source`, `observed_at`, `valid_until` e `summary`; campos sem fonte/horário confiável não podem ser usados como evidência validada. Mercado ausente usa `not_relevant`, sem probabilidade inventada.

O EA verifica envelope, validade, símbolo, direção, preços e relação risco-retorno dentro de um tick do símbolo. Relação 1:2 significa distância entrada-stop : entrada-alvo = 1:2; 1:3 significa 1:3, com orientação compatível com compra/venda. O EA não recalcula a decisão. Correlação da resposta é feita por `request_id`.

O backend interpreta essa relação como razão geométrica entre distâncias de preço. Custos são aplicados separadamente ao cálculo em moeda da conta: compõem a perda estimada e o retorno líquido esperado precisa permanecer positivo após custos. O limite diário também é enviado para auditoria/configuração, mas seu bloqueio e encerramento de posições são aplicados pelo EA no terminal.

## Resposta de erro `error`

Em falha HTTP ou de aplicação, o servidor pode devolver `schema_version`, `message_type: error`, `request_id`, `error.code`, `error.message` e `error.retryable`. O EA mostra o código/estado e não transforma erro em sinal neutro nem reaproveita análise vencida. Clientes e servidores devem rejeitar versões de esquema incompatíveis.

## Execução

O contrato não envia ordem ao backend. `preferences.contracts` é informativo para estimativa e auditoria; depois de receber decisão válida, o EA usa a quantidade configurada no painel. A automação inicia desligada e deve ser ligada manualmente no painel; enquanto ativa, uma decisão válida gera ordem a mercado sem confirmação por operação, desde que limites de risco, símbolo e demais validações estejam configurados e válidos. O polling pausa enquanto houver posição no símbolo e retoma após encerramento.

## Fixtures e validação

Exemplos ficam em `contracts/examples/`. Rode `python3 -m unittest discover -s tests` para validar envelope, ausência de campos, expiração, versão e coerência básica da boleta sem dependências externas.
