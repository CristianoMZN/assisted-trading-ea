# local-backend-storage Specification

## Purpose
Define como o backend local conserva configurações e registros necessários ao funcionamento e à auditoria, mantendo os dados no ambiente do operador.

## Requirements

### Requirement: Persistência local é configurável
O backend SHALL iniciar com persistência SQLite local e SHALL obter a conexão por configuração substituível, preservando o comportamento da aplicação quando outro banco relacional compatível for configurado.

#### Scenario: Configuração padrão
- **WHEN** o operador inicia o serviço sem configurar outro banco
- **THEN** o backend usa o banco SQLite local e cria ou atualiza o esquema suportado

#### Scenario: Outra URL de banco configurada
- **WHEN** o operador fornece uma URL válida de banco compatível e aplica as migrações disponíveis
- **THEN** o backend usa a conexão configurada sem alterar o contrato HTTP

### Requirement: Registros operacionais ficam disponíveis localmente
O backend SHALL persistir análises, versões de configuração, respostas e estados necessários para auditoria e apuração dos limites operacionais.

#### Scenario: Análise concluída
- **WHEN** uma requisição de análise chega ao estado concluído ou `no_signal`
- **THEN** o registro local conserva correlação, decisão, motivo, evidências e versões relevantes sem credenciais

### Requirement: Credencial OpenRouter pertence ao operador
O backend SHALL permitir que cada instalação use a própria chave OpenRouter, protegê-la no armazenamento local conforme os recursos disponíveis no sistema operacional e nunca incluí-la em registros, exportações ou respostas.

#### Scenario: Operador configura a chave
- **WHEN** o operador fornece sua chave para a instalação local
- **THEN** somente o backend pode utilizá-la na comunicação com OpenRouter e a chave não é enviada ao EA

#### Scenario: Exportação ou registro de diagnóstico
- **WHEN** dados operacionais são registrados ou exportados
- **THEN** a chave e os cabeçalhos de autenticação permanecem omitidos

### Requirement: Mudanças de esquema são versionadas
As alterações no esquema de persistência SHALL ser aplicáveis de forma versionada para que a instalação possa evoluir o banco sem recriar manualmente os dados existentes.

#### Scenario: Atualização do esquema
- **WHEN** uma nova versão do backend requer mudança de esquema
- **THEN** a instalação pode aplicar uma migração identificável sobre os dados existentes
