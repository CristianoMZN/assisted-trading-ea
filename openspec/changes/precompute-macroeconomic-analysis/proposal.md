# Proposal

## Why

A pesquisa macroeconômica com ferramentas web ocorre hoje dentro de `POST /v1/analyze` e pode consumir grande parte do tempo da requisição. Nesse intervalo, o snapshot e a cotação podem perder utilidade para uma decisão operacional; falhas de formato do agente de notícias também impedem o teste do restante do fluxo pelo Hopscotch.

## What Changes

- Adicionar um comando de linha para pesquisar e validar a análise macroeconômica antes das requisições, com persistência versionada em SQLite por instrumento lógico (`WIN`/`WDO`).
- Definir validade configurável para esse contexto, com padrão inicial de 15 minutos, e impedir sinal acionável quando não houver contexto válido, ele estiver vencido ou a pesquisa tiver falhado.
- Retirar a pesquisa web e a coleta de notícias do caminho de `POST /v1/analyze`; a rota lê o contexto macro local, interpreta o snapshot técnico atual e chama o agente de decisão, preservando as validações determinísticas.
- Verificar a idade do snapshot/cotação no término do processamento antes de devolver uma recomendação acionável, além de manter a expiração da resposta.
- Documentar e testar primeiro o comando e o contrato HTTP 1.1 pelo Hopscotch; a validação da boleta no MetaTrader fica para depois.

## Capabilities

### New Capabilities

- `macroeconomic-context-cache`: atualização prévia por comando, armazenamento, rastreabilidade, validade e recuperação segura da análise macroeconômica.

### Modified Capabilities

- `multi-agent-market-analysis`: o agente macro passa a executar fora da requisição e seus dados persistidos alimentam a decisão depois da interpretação técnica.
- `fastapi-analysis-api`: a rota usa o contexto macro pré-calculado e bloqueia recomendações com contexto ou snapshot vencido, mantendo o envelope 1.1.
- `market-context-analysis`: a atualidade do snapshot e da cotação também é verificada ao concluir a análise.

## Impact

- CLI em `backend/__main__.py`, orquestração em `backend/main.py`, cliente OpenRouter, prompts, configuração, repositório/modelos SQLAlchemy e migração Alembic.
- Contrato `contracts/backend-v1.md`, documentação operacional e testes Python/Hopscotch; o formato HTTP 1.1 e os fontes MQL5 não precisam mudar nesta etapa.
- A redução da latência é uma meta verificável; melhora da taxa de acerto exige medição posterior e não é presumida pela arquitetura.
