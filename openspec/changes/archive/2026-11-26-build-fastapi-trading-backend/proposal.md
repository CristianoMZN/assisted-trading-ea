# Proposal

## Why

O EA já envia snapshots de mercado por um contrato versionado, mas ainda não há um serviço que valide esses dados, reúna notícias e análise técnica, aplique limites de risco e responda com uma boleta ou uma razão explícita para não operar. O backend local FastAPI completa esse fluxo e permite evoluir os modelos e a persistência sem colocar credenciais de provedores no MetaTrader.

## What Changes

- Criar uma API FastAPI local com health check e rota de análise compatível com o snapshot M5 do EA, atualizando o contrato para transportar preferências de risco e razões de `no_signal`.
- Orquestrar a coleta de notícias com fonte e horário, cálculo técnico reprodutível e uma etapa de decisão configurável via OpenRouter; prompts e resultados ficam associados a versões de modelo, provedor e instruções.
- Aplicar validação determinística à direção, stop, alvo, relação risco-retorno, tick size, perda estimada e retorno líquido esperado. Se a configuração não permitir uma operação coerente, responder sem sinal com código e explicação curta.
- Usar SQLite inicialmente, com SQLAlchemy e Alembic, e configurar a conexão por URL para permitir outro banco em uma instalação futura.
- Permitir que cada operador forneça sua própria chave OpenRouter para o backend local, sem enviá-la ao EA ou incluí-la em logs ou arquivos versionados.
- Ajustar o EA/painel para enviar relação risco-retorno escolhida, limite máximo de stop em pontos, limite de perda por operação, custo estimado de ida e volta e limite diário em moeda da conta; mostrar razões de não operação e, ao atingir o limite diário, fechar posições gerenciadas por este EA e suspender novas consultas até o próximo dia de operação.
- Manter a chave do provedor e o cálculo de risco fora do código distribuído do EA. O MVP não inclui hospedagem em nuvem nem promete uma taxa de acerto; modelos e fontes iniciais serão selecionados e avaliados durante a implementação.

## Capabilities

### New Capabilities

- `fastapi-analysis-api`: health check local e análise de snapshots com resposta versionada, incluindo motivos estruturados para `no_signal`.
- `multi-agent-market-analysis`: coleta de evidências de notícias, cálculo/interpretação técnica, decisão via OpenRouter, prompts versionados e validação final da boleta.
- `local-backend-storage`: persistência local em SQLite com SQLAlchemy/Alembic, configuração de banco e armazenamento local da credencial OpenRouter.

### Modified Capabilities

- `assisted-trade-ticket`: preferências de risco do cliente, custo estimado, limite diário e fechamento/bloqueio ao atingir a perda acumulada.
- `mql5-ea-panel`: configuração e apresentação dos novos limites, motivo de `no_signal` e estado de bloqueio diário.
- `market-context-analysis`: define como o backend consome o snapshot, registra evidências e entrega análise sem inventar campos ausentes.

## Impact

- **MQL5:** contrato, inputs, painel, registro local e fluxo de polling/execução do EA.
- **Python:** novo serviço FastAPI, orquestração de análise, acesso a OpenRouter e adaptadores de fontes de notícia.
- **Persistência/configuração:** SQLite, SQLAlchemy, Alembic, configuração de conexão e proteção da chave BYOK local.
- **Contrato:** a requisição passa a levar as preferências de risco/custo; `no_signal` passa a incluir código e explicação operacional.
- **Fora do MVP:** implantação em nuvem, chave OpenRouter compartilhada pelo projeto, escolha definitiva de um único modelo e promessa de acerto mínimo.
