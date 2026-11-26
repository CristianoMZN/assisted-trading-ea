# Design

## Context

Hoje `backend/__main__.py` inicia apenas o Uvicorn. Em `backend/main.py`, a rota calcula indicadores, consulta RSS, executa `analyze_news` com ferramentas web, chama `interpret_technical` e depois `decide`. O resultado macro não tem tabela própria: cada análise persiste somente sua cópia de evidências. `created_at` e `expires_at` são definidos antes das chamadas remotas e a validação final usa o horário inicial. O prompt macro e o campo `usdbrl_effect` são específicos de WDO, embora a API aceite WIN e WDO. O contrato HTTP atual é 1.1 e o EA não deve ser alterado nesta etapa.

## Goals / Non-Goals

**Goals:**

- Permitir atualizar contexto macro sem servidor HTTP ativo, usando a mesma configuração de banco, credencial e modelo do backend.
- Fazer a requisição online depender apenas de leitura local, indicadores, agente técnico, agente de decisão e validações determinísticas.
- Preservar a separação entre ausência de notícia confirmada, indisponibilidade de pesquisa e cache vencido, com rastreabilidade de fontes e versões.
- Impedir resposta acionável baseada em mercado vencido ao fim do processamento e medir a latência por etapa.

**Non-Goals:**

- Agendar automaticamente a atualização macro, mudar o envelope HTTP 1.1 ou implementar o agente no EA.
- Garantir redução determinada de latência ou aumento de taxa de acerto sem medições e backtest.
- Validar o painel MQL5 ou enviar ordens nesta etapa.

## Decisions

1. **Adicionar subcomando `refresh-macro` ao módulo `backend`.** `python -m backend` continua iniciando a API; `python -m backend refresh-macro --instrument WDO` executa a coleta RSS, pesquisa web, validação e gravação, e sai com código não zero em falha. `--instrument WIN` usa contexto e prompt adequados ao índice, sem tratar pressão sobre USD/BRL como direção de WIN. Exigir o instrumento evita preencher o cache errado. A alternativa de atualizar no startup ou sob demanda manteria pesquisa lenta no caminho operacional.

2. **Guardar execuções imutáveis em tabela versionada.** Uma migração Alembic adiciona registros por instrumento, com estado, resumo, itens/fonte, evidências RSS, `as_of`, `completed_at`, `valid_until`, modelo, prompt e erro operacional sem segredo. A gravação do resultado completo ocorre numa transação; uma falha pode ser auditada, mas não altera nem prorroga a última execução válida. A leitura escolhe a execução válida mais recente do mesmo instrumento ainda dentro dos 15 minutos padrão. `no_relevant_news` é sucesso utilizável; `unavailable`, saída inválida e ausência de dados não são. A validade é configurável e começa na conclusão da pesquisa, não no início. Uma única linha mutável simplificaria consultas, mas perderia o histórico necessário para auditoria e diagnóstico.

3. **Simplificar a saída estruturada macro sem inventar evidências.** O agente continua obrigado a pesquisar e abrir fontes permitidas. Prompts e validação distinguem WDO e WIN, mas convergem em um formato interno comum de efeito relativo ao instrumento. Reduzir campos exigidos do modelo para os fatos/fonte necessários, derivar apenas metadados determinísticos e rejeitar URL ou fato não verificável. Erros `invalid_model_output` ficam no comando de atualização com diagnóstico de campos e fonte, sem derrubar uma chamada HTTP enquanto o cache anterior ainda for válido. Um único retry limitado no comando pode recuperar desvio de formato, sem aceitar conteúdo não validado.

4. **Ler cache antes dos modelos no endpoint.** Para snapshot tecnicamente suficiente, a rota consulta o cache do instrumento e retorna HTTP 503 `macro_context_unavailable` se não houver resultado utilizável. Não executa RSS nem `analyze_news`; inclui no contexto de interpretação/decisão a cópia macro e RSS com horários e versões originais. Depois chama o agente técnico e o de decisão em sequência e mantém a validação de risco. Um snapshot insuficiente ainda retorna `no_signal` sem chamada a modelo. A resposta persiste a referência ao registro macro e as evidências usadas.

5. **Reavaliar atualidade no fim.** Limites configuráveis para `sent_at` e `current_quote.timestamp`, inicialmente 30 segundos, são checados no início e antes de devolver `actionable`. Definir `created_at` ao concluir e limitar `expires_at` pela menor validade entre snapshot, cotação, macro e a janela de resposta; se não restar prazo, retornar `no_signal` com `stale_market_snapshot`. O teste Hopscotch deve gerar timestamps atuais em vez de reutilizar fixture antiga. A alternativa de confiar só no `expires_at` criado antes dos modelos permitiria resposta já vencida ou cotação antiga.

## Risks / Trade-offs

- [A análise macro pode vencer durante uma requisição] → Conferir `valid_until` também no fim; não emitir sinal acionável quando o prazo acabou.
- [Duas atualizações simultâneas podem chegar fora de ordem] → Selecionar por conclusão válida mais recente e usar transações independentes por instrumento.
- [SQLite pode ficar ocupado por um escritor] → Manter transações curtas, configurar espera de lock e testar leitura enquanto o comando grava; não manter transação aberta durante chamadas web.
- [WIN exige interpretação macro diferente de WDO] → Usar prompt/efeito por instrumento e testar separação do cache; não converter automaticamente `usdbrl_effect` em direção de índice.
- [Duas chamadas online ainda podem exceder o limite de atualidade] → Registrar durações separadas e devolver `no_signal` vencido; otimização adicional depende das medições no Hopscotch.

## Migration Plan

1. Aplicar a migração do cache sem apagar análises existentes; manter o esquema de resposta 1.1.
2. Configurar modelo e credencial, executar `refresh-macro` para o instrumento de teste e conferir estado, fontes e validade no banco/saída do comando.
3. Iniciar API e validar no Hopscotch os cenários com cache válido, sem notícia relevante, cache ausente/vencido, falha de modelo, snapshot vencido e fluxo técnico/decisão. Comparar tempos por etapa com a linha de base anterior.
4. Após o backend funcionar no Hopscotch, retomar a mudança `redesign-ea-trading-ticket-manual-analysis` para compilação e testes no MetaTrader do usuário.
5. Reversão: restaurar a versão anterior da aplicação; a migração nova pode permanecer sem afetar tabelas anteriores. Para voltar a usar a versão anterior, ela seguirá pesquisando macro dentro da requisição.
