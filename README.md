# Boleta assistida para WIN e WDO

Expert Advisor para MetaTrader 5 e backend local Python/FastAPI. O EA captura dados do gráfico, envia snapshots por polling HTTP `POST` e apresenta a resposta. O backend calcula indicadores, coleta notícias RSS/Atom configuradas, consulta OpenRouter e valida deterministicamente a decisão antes de retornar uma entrada, stop loss e take profit.

## Objetivo do MVP

- Capturar candles M5 do símbolo configurado, cobrindo os sete dias anteriores, além dos dados de ticks e volume disponíveis no terminal.
- Enviar os dados ao endpoint Python configurado pelo operador, sem chaves de provedores no terminal.
- Apresentar separadamente a resposta do backend, incluindo direção (compra, venda ou sem sinal), cenário, horário, confiança e evidências/fontes retornadas.
- Receber do backend a entrada a mercado, stop loss, take profit e relação risco-retorno geométrica de 1:2 ou 1:3. O EA envia a preferência selecionada; a quantidade de contratos fica ajustável pelo cliente e deve respeitar os limites do símbolo.
- Executar automaticamente uma ordem real quando a automação estiver ligada e o backend retornar decisão válida; não pedir confirmação por operação. A automação começa desligada e é ativada/desativada manualmente no painel.
- Deixar a quantidade de contratos configurável pelo cliente antes de ligar a automação.
- Registrar snapshot associado, resposta, decisão automática e resultado efetivo da execução sem credenciais.

## Arquitetura inicial

```text
MetaTrader 5 (EA/painel)
  ├─ candles M5 dos últimos 7 dias e dados de ticks/volume disponíveis
  ├─ polling HTTP POST configurável (1 a 5 minutos) → backend FastAPI local
  ├─ exibição da decisão e boleta editável (quantidade)
  └─ decisão válida com automação ligada e gráfico sem posição → ordem a mercado com SL/TP
                              ├─ indicadores técnicos determinísticos
                              ├─ fontes RSS/Atom configuradas
                              └─ OpenRouter com chave BYOK local
```

O EA não calcula indicadores nem consulta provedores diretamente, e não envia dados por tick individual. O backend local calcula SMA5/SMA20/RSI14/ATR14, registra evidências e versões, e só aceita uma decisão estruturada após validação de risco. Se dados, provedor, armazenamento ou evidência não estiverem disponíveis, não produz compra/venda. O EA envia snapshots enquanto a automação estiver ligada e não houver posição aberta no símbolo. A disponibilidade de negócios/ticks e volume agressor depende do broker; campos indisponíveis são identificados como ausentes, nunca inventados.

## Limites e salvaguardas do MVP

- A automação de ordens reais começa desligada e exige ativação manual explícita no painel; depois de ativada, cada decisão válida do backend é executada sem confirmação por operação.
- Não há martingale, aumento automático de posição ou nova consulta enquanto existir posição aberta no símbolo.
- Bloquear envio se a resposta do backend estiver vencida, inválida ou incompatível, ou se preço, volume, stop ou alvo violarem as propriedades do símbolo.
- Exigir RR geométrico 1:2 ou 1:3, stop máximo, perda máxima por operação, custo de ida e volta por contrato e limite diário, todos configurados no painel. Backend e EA verificam perda estimada incluindo o custo configurado, retorno líquido positivo após custos, distância mínima de stop do broker e stop máximo. A estimativa não inclui slippage.
- Ao atingir o limite diário negativo, o EA suspende automação, bloqueia novas consultas e fecha posições gerenciadas pelo Magic ID; posições de terceiros não são fechadas. O bloqueio persiste até o próximo dia do servidor e a automação exige reativação manual.
- A quantidade é ajustável pelo cliente dentro do mínimo, máximo e passo de volume do símbolo.
- WIN e WDO podem aparecer com sufixos diferentes conforme o broker e o vencimento. A configuração deve mapear o nome exibido para o símbolo negociável correto.
- Verificar o retcode e o resultado da transação do servidor; retorno positivo de `OrderSend` sozinho não significa execução concluída.
- Exibir que decisões do backend, notícias, análise técnica e probabilidades de mercados de previsão não garantem resultado.

## Configuração inicial

- Período de coleta: M5, janela móvel fixa de sete dias.
- Estratégias de risco-retorno geométricas aceitas: 1:2 ou 1:3, selecionadas no painel e preservadas dentro de um tick.
- Fontes de notícias são configuradas no backend por `NEWS_RSS_URLS`; mercado de previsão permanece como `not_relevant` sem integração configurada.
- O backend escuta em `127.0.0.1:8000` por padrão. Endpoint e timeout HTTP são configuráveis no EA; intervalo de polling é configurável de 1 a 5 minutos.
- Boleta: direção, quantidade ajustável, entrada a mercado, stop loss e take profit retornados pelo backend.
- Limites: propriedades de volume/preço e tick do broker, stop máximo, perda e custo por operação e perda diária definidos pelo cliente.

## Iniciar o backend local

Na raiz do repositório, crie o ambiente Python, instale dependências, aplique migrations e inicie o serviço:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend
```

Consulte `GET /health` e configure `InpBackendUrl` como `http://127.0.0.1:8000/v1/analyze` (ou o endereço/porta configurados). O terminal MT5 precisa permitir essa URL em **Ferramentas → Opções → Expert Advisors**. Para habilitar decisões, configure `OPENROUTER_MODEL` e salve a chave OpenRouter cifrada no cofre do sistema operacional; se o cofre não estiver disponível, `OPENROUTER_API_KEY` é lida do ambiente e não é persistida. `NEWS_RSS_URLS` aceita até cinco feeds HTTPS. Veja [backend/README.md](backend/README.md) para variáveis, erros e detalhes da persistência.

## Instalar e importar no MetaTrader 5

1. No MetaTrader 5 desktop, selecione **Arquivo → Abrir pasta de dados**. Essa é a pasta da instância em que o EA precisa aparecer.
2. Abra `MQL5/Experts` dentro dessa pasta e copie para lá a pasta `AssistedTradingEA` deste repositório, mantendo juntos `AssistedTradingEA.mq5`, `AssistedTradingEA.ex5` (quando já compilado) e a subpasta `Include` com os arquivos `.mqh`.
3. Abra o MetaEditor a partir dessa instância do terminal com **F4**. Abra `MQL5/Experts/AssistedTradingEA/AssistedTradingEA.mq5` da pasta de dados do terminal.
4. No seletor de arquitetura ao lado do botão **Compilar**, escolha **X64 Regular** e compile com **F7**. Essa opção prioriza compatibilidade com diferentes processadores. Confira a aba **Erros**: a compilação precisa terminar sem erros e criar `AssistedTradingEA.ex5` na mesma pasta do `.mq5`.
5. Volte ao MetaTrader. No **Navegador**, clique com o botão direito em **Consultor expert** e escolha **Atualizar**. Expanda `Consultor expert → AssistedTradingEA`; o EA deve aparecer como um item abaixo dessa pasta.
6. Abra um gráfico do instrumento pretendido, por exemplo, dando dois cliques em `WDOF27` na Observação do Mercado, e selecione o período **M5**.
7. Arraste o item `AssistedTradingEA` do Navegador para o gráfico. Nas entradas, configure `InpLogicalInstrument` (WIN/WDO), `InpBrokerSymbol` com o nome exato do broker, a URL completa da API, intervalo, quantidade e limite de perda.
8. Configure RR, stop máximo, perda máxima por operação, custo por contrato e limite de perda diária no painel. Para testar somente a interface, configure `InpUseFixture=true` e `InpFixtureNoSignal=true`. A fixture mostra um estado de teste, não chama o backend e não envia ordens. Depois, volte `InpUseFixture=false`.

O terminal precisa ter a URL do backend liberada em **Ferramentas → Opções → Experts → Relacione no quadro abaixo as URL que deseja permitir a função WebRequest**. O checkbox de DLL não é necessário. O botão de automação do EA começa desligado.

**Importante:** compilar o arquivo na pasta do repositório não instala o EA na instância do MetaTrader. Copie a pasta para a pasta de dados do terminal e compile a cópia dali; isso garante que o MetaEditor e o Navegador estejam usando a mesma instância. O backend incluído roda localmente e expõe o contrato v1.1 em `POST /v1/analyze`.

## Referências técnicas

- MQL5 `WebRequest`: requer liberar os endereços nas opções do terminal, é síncrono e não funciona no Strategy Tester. [Documentação](https://www.mql5.com/en/docs/network/webrequest)
- MetaEditor: **X64 Regular** usa o conjunto básico de instruções e oferece compatibilidade ampla; AVX/AVX2/AVX512 exigem suporte do processador. [Documentação de compilação](https://www.metatrader5.com/en/metaeditor/help/development/compile)
- MQL5 `OrderSend`: retorno `true` não confirma execução; é necessário verificar o código de retorno e a transação. [Documentação](https://www.mql5.com/en/docs/trading/ordersend)
- MetaTrader 5: use os dados disponíveis da instância e do broker para validar símbolo, volume, tick size e distância mínima de stops.

Guia de instalação, configuração e ativação: [`MQL5/Experts/AssistedTradingEA/INSTALL.md`](MQL5/Experts/AssistedTradingEA/INSTALL.md).
