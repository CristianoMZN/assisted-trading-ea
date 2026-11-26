# Spec Delta

## ADDED Requirements

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
