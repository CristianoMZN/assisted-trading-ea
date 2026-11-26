# Instalação e configuração do EA

## Iniciar o backend local

Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
# Edite .env e configure os modelos dos agentes e OPENROUTER_API_KEY
.venv/bin/alembic upgrade head
.venv/bin/python -m backend
```

O serviço usa `127.0.0.1:9000` por padrão, e `InpBackendUrl` já vem preenchido como `http://127.0.0.1:9000/v1/analyze`. Se o backend estiver em outro endereço, altere esse campo nas propriedades do EA. Libere `http://127.0.0.1:9000` em **Ferramentas → Opções → Expert Advisors** do terminal. `GET /health` informa as versões do serviço e do contrato. A requisição e resposta seguem `contracts/backend-v1.md` (schema 1.1).

Copie `.env.example` para `.env` e informe nele `OPENROUTER_MODEL_TECHNICAL_INTERPRETATION`, `OPENROUTER_MODEL_DECISION` e `OPENROUTER_API_KEY`; os dois agentes podem usar modelos iguais ou diferentes. Esse arquivo é carregado automaticamente pelo backend e migrations, e está excluído do Git. Os feeds HTTPS opcionais também são configurados em `NEWS_RSS_URLS`. Instruções de instalação, configuração, banco, retenção e estados de erro estão em [backend/README.md](../../../backend/README.md).

## Instalar na instância correta

1. Abra a instância do MetaTrader 5 em que o EA será usado.
2. No terminal, escolha **Arquivo → Abrir pasta de dados**.
3. Copie a pasta `AssistedTradingEA` inteira para `MQL5/Experts` dentro dessa pasta de dados. Preserve o `.mq5` e a subpasta `Include` com todos os `.mqh`.
4. Abra `MQL5/Experts/AssistedTradingEA/AssistedTradingEA.mq5` no MetaEditor dessa instância e compile com **F7**.
5. Verifique o painel **Errors** do MetaEditor. Não use o pacote como pronto se a compilação indicar erros.
6. Volte ao MT5, clique com o botão direito em **Expert Advisors** no Navigator e escolha **Atualizar**. Se necessário, reinicie o terminal.

## Configurar o EA

| Campo | O que informar | Observação |
| --- | --- | --- |
| `InpLogicalInstrument` | `WIN` ou `WDO` | Deve corresponder ao contrato do gráfico. |
| `InpBrokerSymbol` | Símbolo exato do broker, como `WDOZ26` | Pode ficar vazio para usar o símbolo do gráfico atual. |
| `InpBackendUrl` | `http://127.0.0.1:9000/v1/analyze` | Use o endereço local do serviço; não um URL de teste como webhook.site. |
| `InpPollingIntervalMinutes` | 1 a 5 | Intervalo entre snapshots/análises, em minutos. |
| `InpHttpTimeoutMs` | 250 a 30000 | Tempo máximo de espera pela resposta, em milissegundos. |
| `InpMaxLossPerTrade` | Perda máxima tolerada por operação | Moeda da conta; inclui o custo de ida e volta configurado. Zero bloqueia a automação. |
| `InpRiskRewardPreference` | `1:2` ou `1:3` | Razão geométrica entre distância até o stop e até o alvo. |
| `InpMaxStopPoints` | Distância máxima do stop em pontos MT5 | É medido em `SYMBOL_POINT`, não em ticks. Consulte a conversão abaixo antes de definir. |
| `InpRoundTripCostPerContract` | Custos totais de entrada + saída por contrato | Moeda da conta; inclua tarifas/comissões aplicáveis. Zero significa que o EA assume custo zero. |
| `InpDailyLossLimit` | Perda diária máxima tolerada | Moeda da conta; ao atingir, suspende a automação e fecha posições deste Magic ID. |
| `InpInitialContracts` | Quantidade inicial de contratos | Deve respeitar mínimo, máximo e passo do símbolo; também pode ser ajustada no painel. |
| `InpMagicNumber` | Identificador numérico deste EA | Mantenha o padrão se só houver uma instância; use outro valor para separar instâncias. |
| `InpDeviationPoints` | Desvio máximo de execução em pontos MT5 | Tolerância de preço para a execução/fechamento; também depende de `SYMBOL_POINT`. |
| `InpUseFixture` / `InpFixtureNoSignal` | `false` para uso normal | Fixture é só demonstração e nunca envia ordens reais. |
| `InpLogFileName` | Nome do arquivo JSON Lines | O padrão grava a auditoria em `MQL5/Files`. |

### Converter pontos e ticks

No MT5, abra a Observação do Mercado, clique com o botão direito em `WDOZ26` e escolha **Especificação**. Confira `Point`, `Tick size` e `Stops level`. O limite em pontos corresponde a `InpMaxStopPoints × Point` de variação de preço. Por exemplo, se `Point=0.001` e `Tick size=0.5`, um tick equivale a 500 pontos; nesse caso, `InpMaxStopPoints=5` permite só 0.005 de preço, menos que um tick, e bloqueará stops válidos. A distância também precisa respeitar o `Stops level` do broker.

Defina `InpMaxLossPerTrade`, `InpDailyLossLimit` e os custos conforme sua conta e sua tolerância de risco; não use valores de exemplo sem conferir o valor do tick e as tarifas do broker. O backend e o EA incluem o custo de ida e volta na perda e exigem retorno líquido positivo. A estimativa não inclui slippage.

O limite diário agrega P&L realizado e flutuante do Magic ID deste EA, incluindo comissão, taxas e swap. Quando o limite é atingido, o EA desliga a automação, fecha apenas posições gerenciadas e mantém o bloqueio até o próximo dia do servidor. A automação requer ativação manual novamente.

No terminal, abra **Ferramentas → Opções → Expert Advisors** e adicione o endereço do backend à lista de URLs permitidas para `WebRequest`. Ative **Negociação algorítmica** no terminal e permita negociação nas propriedades do EA.

## Ativação e comportamento

O EA começa com automação desligada. Ajuste quantidade e intervalo no painel e só então clique **AUTOMAÇÃO: LIGADA**. Com automação ativa, uma resposta atual e válida que proponha compra/venda pode gerar ordem real a mercado sem confirmação individual, desde que passe pelas validações de símbolo, volume, stop, alvo e perda máxima.

O polling pausa enquanto houver posição ou ordem ativa no símbolo e retoma após o encerramento. Desligar a automação impede novas consultas e entradas; não remove SL/TP de uma posição já aberta. Se o estado de uma solicitação ficar ambíguo ou o registro local falhar, o EA bloqueia novas operações para evitar repetição automática. Resposta `no_signal`, erro HTTP, versão incompatível ou dados insuficientes nunca geram ordem.

Use primeiro uma conta demo para conferir endpoint permitido, mapeamento, tamanho da posição, proteções SL/TP, pause/resume e logs. O backend FastAPI está no diretório `backend/`; Polymarket não está integrado e aparece como fonte `not_relevant`.

## Referências do fluxo de instalação

- O guia oficial do [MetaTrader 5 sobre Expert Advisors](https://www.metatrader5.com/en/terminal/help/algotrading/autotrading) descreve `MQL5/Experts`, **Abrir pasta de dados**, compilação no MetaEditor com **F7** e saída `.ex5`.
- A [estrutura de pastas do MetaEditor](https://www.metatrader5.com/en/metaeditor/help/structure) confirma que `Experts` recebe fontes `.mq5`/`.mqh` e que `Files` é a pasta de dados usada pelos EAs.
- O [Navigator do MetaEditor](https://www.metatrader5.com/en/metaeditor/help/workspace/navigator) descreve como atualizar a árvore de fontes.

O ambiente de desenvolvimento deste pacote não contém MetaEditor/terminal MT5, portanto a compilação e o teste limpo de instalação precisam ser concluídos em uma instância MT5 compatível.
