# multi-agent-market-analysis Specification

## Purpose
Define a análise coordenada de contexto jornalístico e técnico e sua consolidação em uma decisão operacional validada antes de chegar ao EA.

## Requirements

### Requirement: Evidências de notícias são rastreáveis
A análise jornalística SHALL usar fontes configuradas e retornar evidências pertinentes com fonte, horário de publicação ou coleta e resumo, distinguindo ausência de notícia de falha de consulta.

#### Scenario: Fontes retornam notícias pertinentes
- **WHEN** a busca encontra notícias recentes relacionadas ao instrumento ou a fatores de mercado relevantes
- **THEN** a resposta inclui evidências atribuídas às fontes e seus horários disponíveis

#### Scenario: Busca não encontra notícias ou falha
- **WHEN** não há notícia pertinente ou a fonte está indisponível
- **THEN** a análise registra respectivamente ausência de evidência ou indisponibilidade e não inventa notícias

### Requirement: Análise técnica usa somente dados recebidos
A análise técnica SHALL derivar indicadores e condições do snapshot recebido, identificar dados insuficientes e manter cálculos observáveis reproduzíveis fora da geração de texto do modelo.

#### Scenario: Snapshot contém dados suficientes
- **WHEN** o snapshot contém candles e campos necessários para os indicadores configurados
- **THEN** a análise técnica retorna valores, período utilizado e interpretação associada aos dados

#### Scenario: Snapshot insuficiente
- **WHEN** os candles ou campos não permitem calcular a análise configurada
- **THEN** o resultado identifica os dados ausentes e não inventa indicadores

### Requirement: Decisão de modelo usa OpenRouter configurado pelo operador
A etapa de decisão SHALL usar a chave OpenRouter fornecida pelo próprio operador e um modelo configurado, produzindo apenas a decisão estruturada, confiança calibrada e justificativa curta a partir das evidências fornecidas.

Os agentes de interpretação técnica e decisão SHALL aceitar configurações de modelo independentes. A interpretação técnica SHALL ser executada antes da decisão e fornecida como evidência contextual, sem substituir os indicadores ou as validações determinísticas.

#### Scenario: Decisão recebida do modelo
- **WHEN** o provedor retorna uma resposta que corresponde ao formato de decisão
- **THEN** o backend valida e associa a resposta à versão do modelo e dos prompts usados

#### Scenario: Cada agente tem um modelo configurado
- **WHEN** o operador define modelos para interpretação técnica e decisão
- **THEN** cada chamada usa o modelo do respectivo agente e registra seus identificadores no resultado persistido

#### Scenario: Chave ausente ou provedor indisponível
- **WHEN** não há chave configurada ou a chamada não pode ser concluída
- **THEN** o backend retorna indisponibilidade sem criar recomendação de compra ou venda

### Requirement: Decisão final é validada deterministicamente
Antes de responder ao EA, o backend SHALL validar direção, preços, tick size, limite máximo de stop, relação geométrica risco-retorno escolhida, perda estimada por operação, custo informado e retorno líquido esperado. A relação 1:2 ou 1:3 SHALL corresponder exatamente às distâncias de preço entrada-stop e entrada-alvo, com tolerância de um tick; custos SHALL compor a perda estimada e o retorno líquido esperado SHALL permanecer positivo após custos.

#### Scenario: Sinal passa pelas regras operacionais
- **WHEN** a direção e os níveis propostos respeitam as preferências e regras do instrumento
- **THEN** o backend retorna uma boleta coerente com os preços, relação e perda estimada

#### Scenario: Sinal falha em regra operacional
- **WHEN** qualquer limite ou validação impede a operação
- **THEN** o backend substitui a recomendação por `no_signal` com código de motivo e explicação curta

### Requirement: Prompts e versões da análise são auditáveis
Cada análise SHALL identificar as versões dos prompts e configurações de modelo utilizadas e associá-las ao resultado registrado sem armazenar segredo do provedor.

#### Scenario: Resultado persistido
- **WHEN** uma análise é concluída ou falha após iniciar
- **THEN** o registro contém identificadores de versão, resultado operacional e estado das etapas sem conter chaves secretas
