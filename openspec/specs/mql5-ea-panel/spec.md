# mql5-ea-panel Specification

## Purpose

Apresenta no gráfico do MetaTrader 5 o estado da captura e a decisão recebida do backend, além do estado da automação e da execução.

## Requirements

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

### Requirement: EA respeita símbolo configurado
O EA SHALL permitir mapear WIN ou WDO ao nome negociável usado pelo servidor do broker e SHALL indicar qual símbolo é capturado e negociado.

#### Scenario: Símbolo com sufixo do broker
- **WHEN** o operador configura o nome negociável correspondente a WIN ou WDO
- **THEN** captura, requisição, resposta e boleta usam esse símbolo mapeado

#### Scenario: Mapeamento ausente ou inválido
- **WHEN** WIN ou WDO não pode ser mapeado a um símbolo disponível no terminal
- **THEN** o EA não envia captura nem apresenta recomendação acionável para outro símbolo e informa o problema

### Requirement: EA informa limitações e falhas operacionais
O EA SHALL comunicar indisponibilidade de dados, serviço, resposta vencida e bloqueio de negociação sem apresentá-los como recomendação.

#### Scenario: Serviço externo indisponível
- **WHEN** consulta ao backend falha ou excede o timeout
- **THEN** painel identifica indisponibilidade e mantém o estado sem sinal até obter resposta válida

#### Scenario: Terminal ou símbolo sem dados locais
- **WHEN** não há candles suficientes para a janela solicitada ou dados essenciais de ticks/volume
- **THEN** painel informa os dados ausentes e não envia uma captura declarada como completa

### Requirement: Automação e polling são controláveis pelo cliente
O painel SHALL iniciar com automação desligada, permitir ativá-la/desativá-la manualmente e expor intervalo de polling de 1 a 5 minutos. O estado de posição aberta e a pausa de polling SHALL ficar visíveis.

#### Scenario: Automação ativada
- **WHEN** o cliente liga a automação com configurações válidas
- **THEN** o painel identifica automação ativa e mostra o intervalo selecionado

#### Scenario: Posição aberta
- **WHEN** existe posição no símbolo configurado
- **THEN** o painel informa que o polling está pausado até a posição encerrar

### Requirement: Painel configura preferências de risco e custo
O painel SHALL permitir configurar relação risco-retorno 1:2 ou 1:3, máximo de stop em pontos, perda máxima por operação em moeda da conta, custo estimado de ida e volta por contrato e perda máxima diária em moeda da conta.

#### Scenario: Preferências válidas
- **WHEN** o operador define valores válidos para os limites e custos
- **THEN** o painel apresenta as configurações e o EA as envia ao backend na solicitação de análise

#### Scenario: Preferência ausente ou inválida
- **WHEN** um valor obrigatório está ausente, fora do intervalo permitido ou não representa configuração válida
- **THEN** o painel identifica o campo e impede a ativação da automação

### Requirement: Painel apresenta motivo de não operar
Quando o backend retorna `no_signal`, o painel SHALL apresentar o código e a explicação operacional retornados sem tratar a resposta como boleta executável.

#### Scenario: Backend retorna motivo de não operação
- **WHEN** a resposta atual é `no_signal` com motivo estruturado
- **THEN** o painel exibe esse motivo e não prepara uma ordem

### Requirement: Painel apresenta bloqueio de perda diária
O painel SHALL mostrar o resultado diário calculado, o limite configurado e o estado bloqueado quando a perda diária é atingida.

#### Scenario: EA alcança o limite diário
- **WHEN** o cálculo de resultado líquido das operações deste EA atinge o limite diário
- **THEN** o painel informa o encerramento das posições gerenciadas e que consultas/ordens estão suspensas até o próximo dia de operação

#### Scenario: Novo dia de operação
- **WHEN** inicia um novo dia de operação e a apuração diária reinicia
- **THEN** o painel atualiza o resultado e permite ao cliente reativar a automação manualmente

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
