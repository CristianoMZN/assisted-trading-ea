# Design

## Context

O painel é composto por objetos nativos do gráfico MQL5 em `Include/Panel.mqh`. O `OnTimer` concentra captura, POST, parsing, registro e envio automático de ordem em `AssistedTradingEA.mq5`. O `OnChartEvent` já encaminha cliques e edição de campos. O cliente HTTP `WebRequest` é síncrono. O endpoint e o contrato de snapshot/resposta 1.1 já existem e não precisam mudar.

## Goals / Non-Goals

**Goals:**

- Separar visualmente contexto/estado, recomendação e controles de risco/execução.
- Reaproveitar captura, análise, parsing, auditoria, validação e envio de ordem nos caminhos automático e manual, com políticas de execução distintas.
- Manter a recomendação ligada ao `request_id`, símbolo e validade retornados pelo backend.

**Non-Goals:**

- Alterar o endpoint, o contrato JSON 1.1 ou a estratégia de análise do backend.
- Introduzir uma nova execução paralela para HTTP ou trocar os controles nativos MQL5.
- Permitir análise/aplicação manual com automação ligada ou com posição/ordem ativa no símbolo.

## Decisions

1. **Tratar análise e execução como ações separadas.** Extrair o fluxo compartilhado de captura e análise do `OnTimer` para que polling automático e botão manual usem o mesmo snapshot, POST, parser e tratamento da resposta. A origem da análise define a política: polling com automação ligada mantém execução automática atual; análise manual com automação desligada só atualiza a recomendação e nunca envia ordem. Isso evita duplicar protocolo e preserva a expectativa de confirmação explícita no modo manual. Uma fila assíncrona seria uma alternativa, mas exigiria arquitetura de rede que o EA atual não possui; o botão deve exibir o estado antes da chamada e o resultado ao retornar do `WebRequest` síncrono.

2. **Aplicar a decisão pela mesma rotina de execução validada.** O botão de aplicação chama o fluxo já usado para checar símbolo, quantidade, stop, risco, permissão e bloqueios, e não reconstrói preços nem envia ordem ao backend. Antes do envio, revalidar que a análise ainda é acionável, corresponde ao símbolo configurado e não expirou; bloquear também se automação, posição, ordem ou execução pendente estiver ativa. Alternativamente duplicar a lógica de `OrderSend` para o caminho manual, mas isso aumentaria o risco de divergência nas proteções.

3. **Usar controles visuais agrupados no painel nativo.** Reorganizar `Panel.mqh` em blocos de contexto e estado, decisão e níveis, configurações de risco e ações. Destacar direção e níveis com hierarquia de fonte/cor, agrupar rótulos com campos e separar estados de análise, sem sinal, indisponibilidade e bloqueio de execução. Isso mantém compatibilidade com o gráfico do MT5 e evita dependências externas; o limite é a tipografia e os componentes simples disponíveis no MQL5.

4. **Auditar o fluxo manual com correlação existente.** Registrar eventos distintos para solicitação manual, resposta do backend e aplicação manual, usando o mesmo `request_id`, antes de registrar o resultado real da ordem. Reutilizar o formato JSONL sem registrar credenciais nem confundir solicitação aceita com execução confirmada.

## Risks / Trade-offs

- [O POST síncrono pode deixar o gráfico momentaneamente sem responder] → Indicar o estado de consulta antes da chamada, evitar envios duplicados e documentar/limitar o timeout pela configuração já existente.
- [A recomendação pode expirar entre a análise e o clique em aplicar] → Revalidar `expires_at` imediatamente antes da ordem e exigir nova análise se estiver vencida.
- [A remodelagem pode exceder o espaço visível do gráfico] → Agrupar campos e controlar dimensões/posicionamento do painel, mantendo estados e ação principal visíveis.
- [Dois caminhos de execução podem divergir] → Compartilhar a rotina de validação e envio; diferenciar apenas a política que decide se uma análise aciona automaticamente essa rotina.

## Migration Plan

1. Atualizar o EA distribuído com a nova organização do painel e ações manuais, mantendo o contrato e os inputs de configuração atuais.
2. Validar no terminal que o modo manual somente envia ordem após aplicação, que o polling automático mantém o comportamento existente e que estados de expiração/bloqueio são exibidos.
3. Reversão: instalar a versão anterior do EA; o backend e os snapshots permanecem compatíveis por não haver migração de API.
