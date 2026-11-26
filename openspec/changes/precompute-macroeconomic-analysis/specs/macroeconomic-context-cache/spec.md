# Spec Delta

## Purpose

Permitir que o backend mantenha análises macroeconômicas verificadas e recentes por instrumento, prontas para uso em decisões de mercado sem pesquisa web durante a requisição HTTP.

## ADDED Requirements

### Requirement: Contexto macroeconômico é atualizado por comando separado
O backend SHALL oferecer um comando de linha que execute a pesquisa macroeconômica para `WIN` ou `WDO` antes das requisições de análise e informe sucesso ou falha sem expor credenciais.

#### Scenario: Atualização bem-sucedida
- **WHEN** o operador executa o comando para um instrumento suportado e a pesquisa retorna dados válidos
- **THEN** o comando persiste o resultado e informa instrumento, estado e prazo de validade

#### Scenario: Atualização falha
- **WHEN** o provedor, a pesquisa web ou a validação do resultado falha
- **THEN** o comando sai com falha identificável, não grava contexto parcial e não prolonga a validade do resultado anterior

### Requirement: Contexto persistido é separado por instrumento e rastreável
Cada resultado macroeconômico válido SHALL conservar instrumento lógico, estado, resumo, itens e fontes verificadas, horário de coleta, validade, modelo e versão do prompt, sem segredos. A atualização de um instrumento SHALL ser atômica e não modificar o contexto de outro.

#### Scenario: Leitura do instrumento correspondente
- **WHEN** existe contexto válido para `WDO` e a análise solicitada é para `WIN`
- **THEN** o contexto de `WDO` não é tratado como evidência de `WIN`

#### Scenario: Pesquisa sem notícia pertinente
- **WHEN** a pesquisa foi concluída e validada com `no_relevant_news` e lista vazia
- **THEN** esse resultado pode ser armazenado como contexto válido até expirar, distinguindo ausência de notícia de falha de pesquisa

### Requirement: Somente contexto atual e utilizável alimenta decisões
O contexto macroeconômico SHALL ter validade configurável, inicialmente de 15 minutos contados da conclusão da pesquisa; resultados ausentes, vencidos, incompletos ou `unavailable` SHALL ser identificados como indisponíveis para recomendação acionável.

#### Scenario: Contexto vence
- **WHEN** o horário atual alcança `valid_until` do contexto
- **THEN** o backend deixa de usá-lo em novas decisões, mesmo que ainda esteja armazenado para auditoria

#### Scenario: Pesquisa posterior falha
- **WHEN** a última atualização falha e existe um resultado anterior
- **THEN** o resultado anterior continua auditável e utilizável apenas até sua validade original
