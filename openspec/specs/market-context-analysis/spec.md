# market-context-analysis Specification

## Purpose

Captura contexto de mercado local no MetaTrader 5 e o envia ao backend Python para análise. Notícias, Polymarket e a decisão de trading são responsabilidade do backend e não são implementados neste pacote MQL5.

## Requirements

### Requirement: EA coleta os dados locais definidos
O EA SHALL coletar candles M5 de uma janela móvel de sete dias para o símbolo configurado e SHALL incluir dados de ticks e volume disponíveis no terminal, identificando campos indisponíveis sem inventar valores.

#### Scenario: Histórico completo disponível
- **WHEN** o histórico do símbolo cobre os sete dias solicitados
- **THEN** a requisição contém candles M5, timestamps e os campos de tick/volume disponíveis, associados ao símbolo e período

#### Scenario: Histórico insuficiente ou inconsistente
- **WHEN** faltam candles, timestamps ou campos essenciais, ou os dados locais são inconsistentes
- **THEN** o EA indica a deficiência e não envia o conjunto como snapshot íntegro

### Requirement: Backend é a única camada de análise e decisão
O EA SHALL enviar dados locais ao endpoint configurado e SHALL apresentar a análise e decisão recebidas sem calcular direção ou substituir resposta ausente por análise própria. O backend pode combinar dados técnicos, notícias e mercados de previsão, incluindo Polymarket; fontes e critérios de pertinência são externos ao change MQL5.

#### Scenario: Backend devolve uma decisão válida
- **WHEN** o EA recebe uma resposta atual e compatível com o contrato
- **THEN** apresenta separadamente os blocos de evidência retornados e a direção, stop loss, take profit e relação risco-retorno decididos pelo backend

#### Scenario: Backend não encontra mercado de previsão pertinente
- **WHEN** o backend informa que não há mercado Polymarket pertinente
- **THEN** o EA apresenta esse estado sem inventar uma probabilidade

#### Scenario: Serviço indisponível ou resposta inválida
- **WHEN** a consulta falha, excede timeout, ou a resposta está ausente, vencida ou incompatível
- **THEN** o painel informa a falha e fica sem sinal; não reutiliza decisão anterior como atual

### Requirement: Credenciais de provedores ficam fora do terminal
O EA SHALL usar somente o endpoint configurado do backend e SHALL não armazenar chaves secretas de notícias, Polymarket ou modelos no código distribuído nem em parâmetros do EA.

#### Scenario: Endpoint não está liberado
- **WHEN** o MetaTrader bloqueia o endereço por configuração de acesso web
- **THEN** o EA informa que o endpoint deve ser liberado e não substitui a resposta ausente por dados fictícios

### Requirement: Backend avalia o snapshot e as preferências recebidas
O backend SHALL associar cada análise ao snapshot e às preferências de risco/custo enviados pelo EA, e SHALL distinguir dados ausentes, desatualizados ou inválidos antes de produzir sinal.

#### Scenario: Snapshot íntegro e atual
- **WHEN** o backend recebe snapshot íntegro e atual junto às preferências válidas
- **THEN** usa ambos como entrada da análise e associa a resposta à requisição correspondente

#### Scenario: Snapshot inválido ou desatualizado
- **WHEN** os dados estão incompletos, inválidos ou fora da janela de atualidade aceita
- **THEN** o backend retorna `no_signal` ou erro estruturado sem inferir valores ausentes

### Requirement: Evidências e fontes são apresentadas separadamente da decisão
O backend SHALL apresentar os resultados de análise técnica e jornalística como evidências identificáveis e separadas da decisão final, incluindo fonte e horário quando disponíveis.

#### Scenario: Evidência disponível
- **WHEN** uma etapa de análise retorna dados ou notícias utilizáveis
- **THEN** a resposta associa cada evidência à sua origem e a mantém distinta da decisão consolidada

#### Scenario: Etapa sem evidência
- **WHEN** uma fonte não retorna informação pertinente ou está indisponível
- **THEN** a resposta informa esse estado e não cria conteúdo substituto
