# fastapi-analysis-api Specification

## Purpose
Define a interface HTTP local usada pelo EA para verificar disponibilidade do backend e submeter snapshots de mercado para análise, com respostas compatíveis e explicáveis.

## Requirements

### Requirement: Backend expõe estado de saúde
O serviço SHALL expor uma rota de health que informe se a API está operacional sem incluir credenciais ou dados de usuário.

#### Scenario: Serviço operacional
- **WHEN** o EA ou operador consulta a rota de health
- **THEN** a resposta indica estado operacional e versão do serviço

### Requirement: API valida e analisa snapshots do EA
A rota de análise SHALL aceitar apenas snapshots compatíveis com a versão do contrato, validar campos obrigatórios e retornar uma resposta versionada com decisão, evidências e parâmetros da boleta quando aplicável.

#### Scenario: Snapshot válido
- **WHEN** a requisição contém snapshot e preferências válidos para a versão declarada
- **THEN** a API devolve uma resposta correlacionada à requisição com decisão compatível com o contrato

#### Scenario: Snapshot inválido ou versão incompatível
- **WHEN** faltam campos obrigatórios ou a versão não é suportada
- **THEN** a API retorna erro estruturado e não produz recomendação acionável

### Requirement: Resposta sem operação explica a decisão
Uma resposta `no_signal` SHALL incluir código de motivo estável e explicação curta voltada à operação, sem expor raciocínio privado do modelo.

#### Scenario: Risco inviável
- **WHEN** stop, alvo, relação risco-retorno, custo ou limite configurado impede uma operação válida
- **THEN** a API retorna `no_signal` com código e descrição que identifiquem a condição impeditiva

### Requirement: API não registra segredos
A API SHALL omitir chaves de provedores e demais segredos dos corpos de resposta, logs operacionais e mensagens de erro.

#### Scenario: Falha em provedor
- **WHEN** uma dependência externa retorna erro
- **THEN** a resposta informa indisponibilidade sem reproduzir chave, cabeçalho de autorização ou conteúdo secreto
