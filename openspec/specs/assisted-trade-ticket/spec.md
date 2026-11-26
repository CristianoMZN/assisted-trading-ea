# assisted-trade-ticket Specification

## Purpose

Permite ao cliente configurar quantidade e risco e, após ativação manual da automação, executar a mercado as decisões válidas do backend, sem confirmação por operação.

## Requirements

### Requirement: Boleta apresenta a decisão do backend
O EA SHALL receber e apresentar ação (compra, venda ou sem sinal), execução a mercado, stop loss, take profit e relação risco-retorno de 1:2 ou 1:3. O cliente SHALL poder configurar a quantidade dentro dos limites do símbolo antes de ativar automação. O backend decide se há operação, direção, preços e relação risco-retorno.

#### Scenario: Backend retorna decisão válida com automação desligada
- **WHEN** existe uma resposta atual e válida do backend com compra ou venda e a automação está desligada
- **THEN** o EA exibe símbolo, entrada a mercado, quantidade, stop loss, take profit e relação risco-retorno sem enviar ordem

#### Scenario: Sem decisão válida
- **WHEN** não há resposta válida e atual para o símbolo configurado
- **THEN** o EA informa sem sinal e não prepara uma ordem acionável

#### Scenario: Backend retorna relação não aceita
- **WHEN** a resposta não representa relação risco-retorno 1:2 ou 1:3 ou seus preços não correspondem à relação declarada dentro da precisão do símbolo
- **THEN** o EA rejeita a boleta e bloqueia o envio

### Requirement: Boleta respeita limites do símbolo e risco configurado
Antes de qualquer envio automático, o EA SHALL validar quantidade contra volume mínimo, máximo e passo do símbolo, preços contra tick size e stops level, e perda estimada contra o limite máximo por operação configurado pelo cliente.

#### Scenario: Quantidade fora dos limites do símbolo
- **WHEN** a quantidade é inferior, superior ou incompatível com o passo permitido pelo broker
- **THEN** o EA bloqueia o envio e identifica o campo que precisa de ajuste

#### Scenario: Preço ou stop incompatível
- **WHEN** entrada a mercado, stop ou alvo viola precisão ou distância mínima aplicável ao símbolo
- **THEN** o EA bloqueia o envio e mostra quais valores precisam ser corrigidos

#### Scenario: Limite de risco excedido ou não configurado
- **WHEN** a perda estimada excede o limite do cliente ou o limite máximo por operação não está definido
- **THEN** o EA bloqueia o envio e identifica a configuração ou valor incompatível

### Requirement: Automação exige ativação explícita e começa desligada
O EA SHALL iniciar com automação desligada. Depois de ativada manualmente pelo cliente, SHALL executar uma ordem a mercado para cada decisão válida do backend, sem confirmação individual, desde que todas as validações de dados, símbolo e risco sejam atendidas. O cliente SHALL poder desligar a automação no painel a qualquer momento.

#### Scenario: Cliente ativa a automação
- **WHEN** o cliente liga a automação e endpoint, símbolo, quantidade e limite de perda estão válidos
- **THEN** o EA indica que a automação está ativa e inicia polling no intervalo configurado

#### Scenario: Automação está desligada
- **WHEN** a automação não foi ativada manualmente
- **THEN** o EA não envia ordens, mesmo que exista uma recomendação válida

#### Scenario: Existe posição aberta no símbolo
- **WHEN** há posição aberta no símbolo configurado, independentemente de origem
- **THEN** o EA suspende polling e não envia nova ordem até a posição ser encerrada

#### Scenario: Posição encerra com automação ativa
- **WHEN** não há mais posição aberta no símbolo e a automação continua ativa
- **THEN** o EA retoma o polling no próximo intervalo configurado

#### Scenario: Cliente desliga a automação
- **WHEN** o cliente desliga a automação pelo painel
- **THEN** o EA cancela polling futuro e não envia novas ordens, preservando stops/targets de posições já abertas

#### Scenario: Conta do terminal não permite a operação
- **WHEN** negociação algorítmica ou negociação para o símbolo/conta está desabilitada
- **THEN** o EA não tenta enviar a ordem e informa a condição impeditiva

#### Scenario: Servidor rejeita ou não conclui a ordem
- **WHEN** `OrderSend` falha, o servidor rejeita a solicitação ou a transação não é concluída
- **THEN** o EA apresenta o retcode/estado real, não registra a ordem como executada e não repete uma solicitação de resultado ambíguo automaticamente

### Requirement: Registro contém decisão automática e resultado real
O sistema SHALL registrar snapshot enviado, resposta recebida, parâmetros usados, decisão automática e resultado efetivo da ordem, sem credenciais.

#### Scenario: Ordem aceita, rejeitada ou parcialmente executada
- **WHEN** o servidor reporta o resultado da solicitação ou a transação da ordem
- **THEN** o registro relaciona o resultado e os identificadores retornados à decisão automática e ao snapshot associado

#### Scenario: Registro não pode ser concluído
- **WHEN** ocorre falha ao persistir registro ou resultado de execução
- **THEN** o EA informa a falha e não a apresenta como registro concluído
