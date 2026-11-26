# Spec Delta

## MODIFIED Requirements

### Requirement: Backend avalia o snapshot e as preferências recebidas
O backend SHALL associar cada análise ao snapshot e às preferências de risco/custo enviados pelo EA, e SHALL distinguir dados ausentes, desatualizados ou inválidos antes de produzir sinal. A atualidade dos dados de mercado SHALL ser reavaliada ao concluir o processamento antes de qualquer resposta acionável.

#### Scenario: Snapshot íntegro e atual
- **WHEN** o backend recebe snapshot íntegro e atual junto às preferências válidas
- **THEN** usa ambos como entrada da análise e associa a resposta à requisição correspondente

#### Scenario: Snapshot inválido ou desatualizado
- **WHEN** os dados estão incompletos, inválidos ou fora da janela de atualidade aceita
- **THEN** o backend retorna `no_signal` ou erro estruturado sem inferir valores ausentes

#### Scenario: Snapshot envelhece durante a análise
- **WHEN** o snapshot ou a cotação ultrapassa o limite de atualidade enquanto o backend consulta os modelos
- **THEN** o backend não converte a decisão recebida em sinal acionável e registra o motivo de expiração dos dados
