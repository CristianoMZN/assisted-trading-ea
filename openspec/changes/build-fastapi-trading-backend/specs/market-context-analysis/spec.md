# Spec Delta

## ADDED Requirements

### Requirement: Backend avalia o snapshot e as preferências recebidas
O backend SHALL associar cada análise ao snapshot e às preferências de risco/custo enviados pelo EA, e SHALL distinguir dados ausentes, desatualizados ou inválidos antes de produzir sinal.

#### Scenario: Snapshot íntegro e atual
- **WHEN** o backend recebe snapshot íntegro e atual junto às preferências válidas
- **THEN** usa ambos como entrada da análise e associa a resposta à requisição correspondente

#### Scenario: Snapshot inválido ou desatualizado
- **WHEN** os dados estão incompletos, inválidos ou fora da janela de atualidade aceita
- **THEN** o backend retorna `no_signal` ou erro estruturado sem inferir valores ausentes

### Requirement: Evidências e fontes são apresentadas separadamente da decisão
O backend SHALL apresentar os resultados de análise técnica e jornalística como evidências identificáveis e separadas da decisão final, incluindo fonte e horário quando disponíveis.

#### Scenario: Evidência disponível
- **WHEN** uma etapa de análise retorna dados ou notícias utilizáveis
- **THEN** a resposta associa cada evidência à sua origem e a mantém distinta da decisão consolidada

#### Scenario: Etapa sem evidência
- **WHEN** uma fonte não retorna informação pertinente ou está indisponível
- **THEN** a resposta informa esse estado e não cria conteúdo substituto
