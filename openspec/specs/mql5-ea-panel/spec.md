# mql5-ea-panel Specification

## Purpose

Apresenta no gráfico do MetaTrader 5 o estado da captura e a decisão recebida do backend, além do estado da automação e da execução.

## Requirements

### Requirement: EA apresenta painel de análise e boleta
O EA SHALL apresentar símbolo negociável, timeframe M5, janela de dados de sete dias, direção recebida (compra, venda ou sem sinal), cenário, horário, confiança, relação risco-retorno e estado da conexão/resposta.

#### Scenario: Análise disponível
- **WHEN** uma resposta válida é recebida para o símbolo configurado
- **THEN** o painel apresenta a decisão e os preços de entrada a mercado, stop loss e take profit com os campos de evidência e horário retornados

#### Scenario: Nenhuma análise válida
- **WHEN** ainda não existe análise válida para a configuração atual
- **THEN** o painel mostra sem sinal e não reaproveita direção ou boleta anterior como atual

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
