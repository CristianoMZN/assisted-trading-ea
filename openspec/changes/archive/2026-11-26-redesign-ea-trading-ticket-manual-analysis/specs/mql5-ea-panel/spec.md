# Spec Delta

## MODIFIED Requirements

### Requirement: EA apresenta painel de análise e boleta
O EA SHALL apresentar símbolo negociável, timeframe M5, janela de dados de sete dias, direção recebida (compra, venda ou sem sinal), cenário, horário, confiança, relação risco-retorno e estado da conexão/resposta. O painel SHALL organizar recomendação, estado operacional e configurações em áreas visualmente distintas e SHALL destacar a decisão e os níveis de preço.

#### Scenario: Análise disponível
- **WHEN** uma resposta válida é recebida para o símbolo configurado
- **THEN** o painel apresenta a decisão e os preços de entrada a mercado, stop loss e take profit com os campos de evidência e horário retornados, em uma área de recomendação claramente identificada

#### Scenario: Nenhuma análise válida
- **WHEN** ainda não existe análise válida para a configuração atual
- **THEN** o painel mostra sem sinal e não reaproveita direção ou boleta anterior como atual

#### Scenario: Resposta sem sinal ou falha operacional
- **WHEN** o backend retorna `no_signal` ou a consulta falha
- **THEN** o painel exibe o motivo da ausência de oportunidade ou o erro de serviço em estado distinto, sem apresentá-lo como recomendação

## ADDED Requirements

### Requirement: Painel permite solicitar análise manual
O painel SHALL permitir que o operador solicite uma análise sob demanda e SHALL identificar o estado da consulta e apresentar seu resultado quando a chamada terminar.

#### Scenario: Solicitar análise com automação desligada
- **WHEN** não há posição ou ordem ativa no símbolo, nenhuma consulta está em andamento e o operador aciona a análise manual
- **THEN** o EA captura e envia um snapshot pelo contrato de backend configurado, exibe o estado de processamento e aguarda a resposta sem enviar uma ordem automaticamente

#### Scenario: Consulta manual em andamento ou automação ligada
- **WHEN** uma consulta manual já está em andamento ou a automação está ligada
- **THEN** o painel impede uma nova consulta manual e informa o estado que impede a ação

#### Scenario: Sem posição disponível para análise manual
- **WHEN** existe posição ou ordem ativa para o símbolo configurado
- **THEN** o EA não envia o snapshot manual e informa que a análise está indisponível enquanto houver exposição ativa
