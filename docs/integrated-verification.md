# Verificação integrada do backend de trading

Verificação registrada em 2026-11-26 para o contrato 1.1.

## Resultados

- `python -m unittest discover -s tests -q`: 49 testes aprovados.
- `python -m compileall -q backend tests`: compilação sintática Python concluída.
- `alembic upgrade head` sobre SQLite vazio em arquivo temporário: migrations 0001, 0002 e 0003 aplicadas.
- Health e registro de rotas: `/health` retorna status `ok`, versão do serviço `0.1.0` e contrato `1.1`; `/v1/analyze` está registrado.
- Contrato: fixtures válidas, versões incompatíveis, snapshot inválido/expirado, resposta `no_signal` e códigos estáveis cobertos por testes.
- Análise: cenário acionável validado e persistido; dados insuficientes geram `no_signal` persistido sem chamada ao modelo; candidato com retorno líquido não positivo gera `no_signal`.
- Indisponibilidade: chave ausente, timeout, resposta do provedor fora do esquema e falha de armazenamento não geram compra/venda; mensagens e persistência de versões cobertas pelos testes.
- Risco: direção, cotação, tick, distância mínima do broker, stop máximo, RR geométrico exato, perda incluindo custo e retorno líquido positivo cobertos.
- Notícias: casos com item relevante, feed vazio, fonte indisponível e configuração ausente mantêm estados distintos.
- EA: testes estáticos verificam serialização v1.1, `reason_code`, validação final de stop/custo, P&L limitado ao Magic ID, persistência do bloqueio diário e reinício sem reativação automática.

## Limites da verificação

Os testes do EA são estáticos sobre o código-fonte. MetaEditor/terminal MetaTrader 5 não está disponível neste ambiente, então a compilação MQL5 e uma execução real de ordens/fechamento diário ainda precisam ser verificadas em uma instalação MT5 compatível. Não foram feitas chamadas a feeds reais nem ao OpenRouter; esses caminhos usam respostas controladas nos testes.
