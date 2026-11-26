# Proposal

## Why

O change entrega um Expert Advisor para MetaTrader 5 que envia contexto do gráfico a um backend externo, apresenta a decisão recebida e executa ordens automaticamente depois que o cliente ativa a automação no painel.

## What Changes

- Criar um Expert Advisor MQL5 inicial, compilável no MetaEditor e reconhecido pelo Navigator do MetaTrader 5.
- Capturar candles M5 dos sete dias anteriores e dados de ticks/volume disponíveis no terminal e enviá-los ao backend Python configurado.
- Apresentar a decisão do backend, que é a única camada que define direção, entrada a mercado, stop loss, take profit e relação risco-retorno 1:2 ou 1:3. Notícias, Polymarket e análise ficam fora do pacote MQL5.
- Permitir ao cliente configurar quantidade e intervalo de polling de 1 a 5 minutos e ativar/desativar manualmente a automação; com automação ativa, executar ordens reais a mercado sem confirmação por operação quando o backend retornar sinal válido.
- Suspender polling enquanto existir posição aberta no símbolo e retomá-lo após o encerramento.
- Validar limites do símbolo e perda máxima por operação configurada, registrar recomendação/dados/decisão/resultado real e indicar ausência de sinal quando dados ou serviço forem inválidos ou vencidos.
- Definir o pacote e as instruções para copiar/compilar o EA no diretório correto de dados do MT5, sem embutir credenciais de serviços externos no terminal.

## Capabilities

### New Capabilities

- `mql5-ea-panel`: ciclo de vida do EA e painel no gráfico para apresentar contexto e estado da análise.
- `market-context-analysis`: coleta de contexto local e envio ao backend, com exibição separada dos blocos retornados e validação de atualidade/disponibilidade.
- `assisted-trade-ticket`: preparação, validação e envio confirmado de uma ordem real a mercado.
- `mql5-distribution`: estrutura, compilação e instruções de instalação do EA no MetaTrader 5.

### Modified Capabilities

Nenhuma. O projeto ainda não possui specs principais registradas.

## Impact

Afeta o novo código MQL5 e seus arquivos de inclusão, o contrato versionado entre EA e backend FastAPI externo, a validação dos limites do símbolo e do risco por operação, a automação de ordens reais após ativação manual, o registro de resultados e a documentação de compilação/importação. O EA coleta M5 por sete dias e dados de ticks/volume disponíveis; não escolhe fontes nem calcula decisões, pois notícias, Polymarket e análise pertencem ao backend fora deste change. Endpoint, timeout e intervalo de polling são configuráveis; polling pausa quando há posição no símbolo.
