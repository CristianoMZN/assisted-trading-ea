# Spec Delta

## MODIFIED Requirements

### Requirement: Boleta apresenta a decisão do backend
O EA SHALL receber e apresentar ação (compra, venda ou sem sinal), execução a mercado, stop loss, take profit e relação risco-retorno. O cliente SHALL poder configurar quantidade e relação risco-retorno 1:2 ou 1:3. O backend decide se há operação, direção e preços respeitando essas preferências.

#### Scenario: Backend retorna decisão válida com automação desligada
- **WHEN** existe uma resposta atual e válida do backend com compra ou venda e a automação está desligada
- **THEN** o EA exibe símbolo, entrada a mercado, quantidade, stop loss, take profit e relação risco-retorno sem enviar ordem

#### Scenario: Sem decisão válida
- **WHEN** não há resposta válida e atual para o símbolo configurado
- **THEN** o EA informa sem sinal e não prepara uma ordem acionável

#### Scenario: Backend retorna relação não aceita
- **WHEN** a resposta não corresponde à relação risco-retorno configurada ou seus preços não correspondem à relação declarada dentro da precisão do símbolo
- **THEN** o EA rejeita a boleta e bloqueia o envio

### Requirement: Boleta respeita limites do símbolo e risco configurado
Antes de qualquer envio automático, o EA SHALL validar quantidade contra volume mínimo, máximo e passo do símbolo, preços contra tick size e stops level, e perda estimada contra o limite máximo por operação, o máximo de stop em pontos e o custo configurados pelo cliente.

#### Scenario: Quantidade fora dos limites do símbolo
- **WHEN** a quantidade é inferior, superior ou incompatível com o passo permitido pelo broker
- **THEN** o EA bloqueia o envio e identifica o campo que precisa de ajuste

#### Scenario: Preço ou stop incompatível
- **WHEN** entrada a mercado, stop ou alvo viola precisão ou distância mínima aplicável ao símbolo
- **THEN** o EA bloqueia o envio e mostra quais valores precisam ser corrigidos

#### Scenario: Limite de risco excedido ou não configurado
- **WHEN** a perda estimada excede o limite do cliente, o stop excede o máximo configurado ou o limite máximo por operação não está definido
- **THEN** o EA bloqueia o envio e identifica a configuração ou valor incompatível

#### Scenario: Custo inviabiliza o retorno líquido
- **WHEN** o retorno estimado após o custo de ida e volta informado é zero ou negativo
- **THEN** o EA bloqueia o envio e informa que os custos inviabilizam o retorno esperado

## ADDED Requirements

### Requirement: Limite diário protege as operações deste EA
O EA SHALL apurar o resultado líquido diário das operações identificadas como suas em moeda da conta, incluindo resultado realizado e P&L aberto, e SHALL comparar esse valor com o limite diário configurado.

#### Scenario: Limite diário atingido
- **WHEN** o resultado líquido diário realizado e aberto alcança ou ultrapassa a perda máxima permitida
- **THEN** o EA fecha posições abertas gerenciadas por este EA, interrompe consultas e novas ordens até o próximo dia de operação e informa o bloqueio

#### Scenario: Operações de outros sistemas
- **WHEN** a conta possui posições ou resultados que não pertencem a este EA
- **THEN** eles não alteram o cálculo do limite diário nem são fechados pelo bloqueio deste EA

#### Scenario: Início de novo dia de operação
- **WHEN** começa o próximo dia de operação segundo a referência temporal definida para a conta
- **THEN** o limite é recalculado para o novo dia e o cliente pode reativar a automação
