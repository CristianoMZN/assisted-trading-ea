# Spec Delta

## ADDED Requirements

### Requirement: Pesquisa macroeconômica fica fora do caminho da decisão online
Para snapshots com dados técnicos suficientes, o backend SHALL obter o contexto macroeconômico persistido do mesmo instrumento, SHALL executar a interpretação técnica sobre o snapshot recebido e SHALL fornecer ambos ao agente de decisão nessa ordem. A requisição HTTP SHALL não executar pesquisa web macroeconômica nem atualizar o cache.

#### Scenario: Contexto atual e snapshot suficiente
- **WHEN** a requisição contém dados técnicos suficientes e existe contexto macro válido para o instrumento
- **THEN** o agente técnico interpreta os dados recebidos e o agente de decisão recebe essa interpretação e a evidência macro persistida com seus horários e versões

#### Scenario: Requisições sucessivas
- **WHEN** duas requisições do mesmo instrumento chegam enquanto o contexto macro permanece válido
- **THEN** ambas podem reutilizar o contexto salvo, mas cada uma recebe interpretação técnica e decisão específicas para seu próprio snapshot

#### Scenario: Dados técnicos insuficientes
- **WHEN** o snapshot não permite calcular os indicadores exigidos
- **THEN** o backend retorna `no_signal` sem acionar os modelos técnico e de decisão e sem exigir uma nova pesquisa macroeconômica
