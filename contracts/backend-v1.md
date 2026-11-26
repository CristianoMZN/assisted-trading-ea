# Contrato EA ↔ backend Python, versão 1

O EA faz `POST` periódico para o endpoint HTTPS da REST API Python/FastAPI configurado pelo cliente, com intervalo selecionável de 1 a 5 minutos. Não faz polling quando já existe posição aberta no símbolo. O change implementa o cliente e o contrato; não implementa o servidor FastAPI, as fontes de notícias, a integração Polymarket, a integração OpenAI ou a lógica de decisão. Mensagens usam UTF-8 e timestamps ISO 8601 em UTC. Versão desconhecida, corpo inválido ou resposta vencida sempre resulta em sem sinal.

## Requisição `market_snapshot`

- `schema_version`: exatamente `1.1`.
- `message_type`: `market_snapshot`.
- `request_id`: UUID para correlacionar resposta e log.
- `sent_at`: instante UTC da captura.
- `instrument`: `logical_symbol` (`WIN` ou `WDO`) e `broker_symbol` configurado.
- `timeframe`: `M5`.
- `window`: `from` e `to` em UTC cobrindo a janela móvel de sete dias.
- `server_utc_offset_seconds`: diferença usada pelo EA para converter timestamps das barras do horário do servidor para UTC no momento da captura.
- `history_first_available_at`: primeiro horário local de histórico M5 disponível após sincronização; precisa ser anterior ou igual ao início da janela solicitada.
- `current_quote`: bid/ask/last, volume, flags e timestamp do último tick disponível; o backend pode usar a cotação para avaliar entrada a mercado.
- `tick_flow`: volume agregado de negócios com flags de compra/venda durante o intervalo desde o polling anterior. `classification_available` indica se o broker classificou negócios por lado; quando não, volumes ficam `null` e não podem ser tratados como zero.
- `candles`: candles M5 disponíveis dentro da janela, ordenados do mais antigo ao mais recente. Cada candle leva `timestamp`, OHLC, `tick_volume`, `real_volume`, `buy_volume` e `sell_volume`; volume real/agressor pode ser `null` quando o broker não o fornece.
- `unavailable_fields`: nomes dos campos de mercado que a instância não forneceu. Ausência não pode ser convertida em zero nem inferida.
- `preferences`: `risk_reward` (`1:2` ou `1:3`), `max_stop_points`, `max_loss_per_trade`, `round_trip_cost_per_contract` e `daily_loss_limit`, todos números finitos não negativos; stop máximo e perdas máximas devem ser maiores que zero. Valores monetários usam a moeda da conta.

O período de sete dias é de calendário. Fechamentos de mercado e fins de semana podem reduzir a quantidade de candles; cada candle enviado deve ser válido e temporalmente dentro da janela.

## Resposta `analysis_response`

- `schema_version`: exatamente `1.1`; `message_type`: `analysis_response`; `request_id`: igual ao pedido.
- `created_at` e `expires_at`: timestamps UTC; a resposta só é acionável enquanto `now < expires_at`.
- `instrument`: deve corresponder ao pedido.
- `status`: `actionable` ou `no_signal`.
- `decision`: objeto para `actionable`, `null` para `no_signal`. Deve conter `direction` (`BUY`/`SELL`), `entry_type` (`MARKET`), preço de referência, `stop_loss`, `take_profit`, `risk_reward` (`1:2`/`1:3`), `scenario` e `confidence` (`low`/`medium`/`high`). O backend decide todos esses valores, exceto quantidade, que o cliente ajusta no EA.
- `reason_code` e `reason`: obrigatórios em `no_signal`, ambos `null` em `actionable`. `reason_code` é um identificador estável em `snake_case`; `reason` é uma explicação operacional curta e não contém raciocínio privado do modelo.
- `sources`: lista de blocos do backend (`technical`, `news`, `prediction_market`) com `status`, `source`, `observed_at`, `valid_until` e `summary`; campos sem fonte/horário confiável não podem ser usados como evidência validada. Mercado ausente usa `not_relevant`, sem probabilidade inventada.

O EA verifica envelope, validade, símbolo, direção, preços e relação risco-retorno dentro de um tick do símbolo. Relação 1:2 significa distância entrada-stop : entrada-alvo = 1:2; 1:3 significa 1:3, com orientação compatível com compra/venda. O EA não recalcula a decisão. Correlação da resposta é feita por `request_id`.

## Resposta de erro `error`

Em falha HTTP ou de aplicação, o servidor pode devolver `schema_version`, `message_type: error`, `request_id`, `error.code`, `error.message` e `error.retryable`. O EA mostra o código/estado e não transforma erro em sinal neutro nem reaproveita análise vencida. Clientes e servidores devem rejeitar versões de esquema incompatíveis.

## Execução

O contrato não envia quantidade nem ordem ao backend. Depois de receber uma decisão válida, o EA usa quantidade configurada pelo cliente. A automação inicia desligada e deve ser ligada manualmente no painel; enquanto ativa, uma decisão válida gera ordem a mercado sem confirmação por operação, desde que limite máximo de perda, símbolo e demais validações estejam configurados e válidos. O polling pausa enquanto houver posição no símbolo e retoma após encerramento.

## Fixtures e validação

Exemplos ficam em `contracts/examples/`. Rode `python3 -m unittest discover -s tests` para validar envelope, ausência de campos, expiração, versão e coerência básica da boleta sem dependências externas.
