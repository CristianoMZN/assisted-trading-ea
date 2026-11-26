# Tasks

## Encerramento

Em 26/11/2026, o usuário decidiu abandonar as três verificações pendentes desta mudança e encerrá-la. Os fontes MQL5 já alterados permanecem no projeto, mas as tarefas 1.2, 1.3 e 4.1 ficam sem validação no MetaTrader e não são marcadas como concluídas. O trabalho futuro de backend segue na mudança separada `precompute-macroeconomic-analysis`.

## 1. Reorganizar o painel da boleta

- [x] 1.1 Agrupar estado do mercado, recomendação, parâmetros de risco e ações no painel MQL5, e verificar no MetaTrader que decisão e níveis ficam destacados e legíveis no gráfico.
- [ ] 1.2 Apresentar estados distintos de análise pendente, `actionable`, `no_signal`, erro, expiração e bloqueio, e verificar que cada estado mostra os dados corretos sem reutilizar recomendação antiga.
  - Cancelada por decisão do usuário em 26/11/2026: estados revisados nos fontes, sem validação visual no MT5.
- [ ] 1.3 Adicionar os botões de análise manual e aplicação da recomendação com habilitação coerente com automação, consulta em andamento e exposição aberta, e verificar a atualização visual após cada transição.
  - Cancelada por decisão do usuário em 26/11/2026: guardas e textos revisados nos fontes, sem validação dos botões no MT5.

## 2. Implementar análise manual do snapshot

- [x] 2.1 Extrair o fluxo compartilhado de captura, POST, parsing e auditoria usado pelo polling, e verificar que o polling automático continua usando o endpoint e o contrato 1.1 existentes.
- [x] 2.2 Ligar o botão de análise ao fluxo compartilhado somente com automação desligada e sem posição/ordem ativa, e verificar que a resposta atualiza a boleta sem enviar ordem.
- [x] 2.3 Registrar solicitação manual, resposta e falhas com o `request_id` correspondente, e verificar os eventos JSONL sem incluir credenciais.

## 3. Aplicar recomendação manual com segurança

- [x] 3.1 Ligar a ação de aplicação à rotina comum de validação e envio, revalidando validade, símbolo, volume, risco, permissão e exposição imediatamente antes da ordem, e verificar que ordem só é enviada quando todos os bloqueios passam.
- [x] 3.2 Bloquear aplicação de resposta vencida, sem sinal, inválida, com automação ligada ou posição/ordem ativa, e verificar que o painel mostra o motivo sem enviar ordem.
- [x] 3.3 Registrar aplicação, parâmetros efetivos e resultado confirmado/rejeitado/ambíguo associados ao mesmo `request_id`, e verificar que os estados não confirmados não são registrados como executados.

## 4. Verificar integração e documentar uso

- [ ] 4.1 Compilar o EA e percorrer no MetaTrader os fluxos manual e automático, incluindo sem sinal, falha HTTP, expiração, risco bloqueado e ordem já ativa, e verificar que cada estado corresponde às especificações.
  - Compilação da revisão anterior no MetaEditor do usuário confirmada em 26/11/2026. Recompilação destes ajustes e verificação dos fluxos no terminal ainda pendentes.
  - Cancelada por decisão do usuário em 26/11/2026: recompilação e testes de integração no MT5 não realizados para esta revisão. Erros `invalid_model_output` do agente macro pertencem à mudança do backend.
- [x] 4.2 Atualizar a documentação de instalação/operação com os controles e o fluxo manual, e verificar que os nomes e instruções correspondem ao painel entregue.
