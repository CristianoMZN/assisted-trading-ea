# Proposal

## Why

A boleta atual concentra muitas informações e configurações em um painel pouco organizado, dificultando a leitura da recomendação e os ajustes do operador. Também falta um comando para solicitar uma análise ao backend sob demanda e revisar a resposta antes de enviar uma ordem, o que torna os testes e a operação assistida menos práticos.

## What Changes

- Reorganizar visualmente o painel em áreas claras para mercado/estado, recomendação e configurações de risco e execução.
- Permitir solicitar manualmente uma análise, enviando ao backend um snapshot no contrato existente.
- Apresentar recomendações acionáveis, respostas `no_signal` com motivo e falhas do backend em estados distintos.
- Permitir aplicar explicitamente uma recomendação válida para enviar a ordem, preservando as validações de risco, símbolo, quantidade, expiração e posição/ordem aberta.
- Preservar o modo automático existente quando ativado; no modo manual, uma análise recebida não envia ordem até o operador aplicar a recomendação.

## Capabilities

### New Capabilities

<!-- None: the change extends the existing EA panel and assisted ticket behaviors. -->

### Modified Capabilities

- `mql5-ea-panel`: reorganizar a apresentação e adicionar controles visíveis para análise sob demanda e aplicação da recomendação.
- `assisted-trade-ticket`: permitir execução manual de uma recomendação vigente, mantendo a execução automática existente quando a automação estiver ligada.

## Impact

- EA MQL5 em `MQL5/Experts/AssistedTradingEA/`, especialmente `Include/Panel.mqh`, `Include/MarketData.mqh` e o fluxo de eventos/execução em `AssistedTradingEA.mq5`.
- Contrato HTTP existente `POST /v1/analyze` e contrato de resposta 1.1 em `contracts/backend-v1.md`; não se prevê mudança de API.
- Registro local de auditoria para diferenciar análise manual, recomendação aplicada e resultado da ordem.
