# Spec Delta

## ADDED Requirements

### Requirement: Cliente aplica manualmente uma recomendação vigente
Com a automação desligada, o EA SHALL permitir que o cliente aplique explicitamente uma recomendação acionável, válida e correspondente ao símbolo atual, usando a quantidade e os limites de risco configurados no terminal.

#### Scenario: Aplicar recomendação válida
- **WHEN** o cliente aciona aplicar para uma recomendação ainda vigente e válida, com automação desligada e sem posição ou ordem ativa no símbolo
- **THEN** o EA executa as validações existentes de volume, risco, preços, permissão de negociação e bloqueios e envia a ordem a mercado somente se todas forem aprovadas

#### Scenario: Recomendação sem sinal, vencida ou inválida
- **WHEN** o cliente tenta aplicar uma recomendação que não é acionável, está vencida, foi rejeitada na validação ou não corresponde ao símbolo atual
- **THEN** o EA não envia a ordem e apresenta o motivo do bloqueio

#### Scenario: Posição/ordem ativa ou automação ligada
- **WHEN** o cliente tenta aplicar uma recomendação com posição ou ordem ativa no símbolo, ou com a automação ligada
- **THEN** o EA não envia a ordem e informa que a aplicação manual está indisponível nesse estado

#### Scenario: Resultado da aplicação manual
- **WHEN** uma ordem manual é enviada, rejeitada ou tem resultado ambíguo
- **THEN** o EA registra a resposta do backend, a recomendação aplicada, os parâmetros efetivos e o resultado real da execução associados ao mesmo `request_id`, sem registrar rejeição ou ambiguidade como ordem executada
