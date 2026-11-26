# Spec Delta

## ADDED Requirements

### Requirement: API depende de contexto macro válido para sinal acionável
A rota `POST /v1/analyze` SHALL usar somente contexto macro persistido, atual e do mesmo instrumento. Se esse contexto não estiver disponível, SHALL devolver erro estruturado `macro_context_unavailable`, sem decisão acionável e sem iniciar pesquisa web durante a requisição.

#### Scenario: Contexto ausente ou vencido
- **WHEN** chega snapshot tecnicamente suficiente e não há contexto macro utilizável para seu instrumento
- **THEN** a API devolve envelope de erro 1.1 com código `macro_context_unavailable`, sem decisão de compra ou venda

#### Scenario: Contexto válido
- **WHEN** existe contexto utilizável para o instrumento e o snapshot é válido
- **THEN** a resposta mantém o contrato 1.1 e inclui a evidência macro com horário de coleta e validade originais do cache

### Requirement: Recomendação acionável exige mercado ainda atual ao terminar
O backend SHALL verificar a idade do snapshot e da cotação antes das chamadas de modelo e novamente antes de devolver uma decisão acionável, usando limites configuráveis. Um resultado que ultrapasse esses limites SHALL não ser acionável, mesmo que o snapshot fosse atual ao chegar.

#### Scenario: Modelo demora além da validade do snapshot
- **WHEN** a interpretação ou decisão termina depois do limite de atualidade do snapshot ou da cotação
- **THEN** a API devolve `no_signal` com motivo estável `stale_market_snapshot` e não envia preços acionáveis

#### Scenario: Análise termina dentro da validade
- **WHEN** contexto macro, snapshot e cotação ainda estão atuais ao término
- **THEN** a API pode devolver `actionable` somente após as validações determinísticas existentes, com `expires_at` posterior à criação e limitado pela validade dos dados usados
