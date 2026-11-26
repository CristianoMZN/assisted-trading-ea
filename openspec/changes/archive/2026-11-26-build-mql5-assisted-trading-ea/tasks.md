# Tasks

Implementação e validação em terminal estão separadas: a fonte MQL5 e o contrato foram escritos, mas os testes que exigem MetaEditor/MT5 continuam pendentes neste ambiente.

## 1. Decisões do MVP e contrato

- [x] 1.1 Registrar coleta M5 por sete dias, decisão exclusiva do backend FastAPI externo, polling configurável de 1 a 5 minutos suspenso com posição aberta, notícias/Polymarket/OpenAI fora deste change, campos da boleta, automação manualmente ativada sem confirmação por ordem, limites do símbolo e perda máxima configurável.
- [x] 1.2 Definir o contrato JSON versionado EA/backend e exemplos; validar com testes automatizados campos, expiração, versão, candles e relação risco-retorno.

## 2. Estrutura MQL5 e painel

- [x] 2.1 Criar EA `.mq5` e módulos `.mqh` de configuração, painel, dados, transporte, execução e registro.
- [x] 2.2 Abrir/compilar os arquivos no MetaEditor e confirmar que são reconhecidos como Expert Advisor.
- [x] 2.3 Implementar mapeamento WIN/WDO, painel de estado/sinal e campos configuráveis de quantidade e polling.
- [x] 2.4 Validar símbolos válidos/inválidos, fixture e estados do painel no Strategy Tester/terminal.
- [x] 2.5 Implementar ativação manual desligada por padrão, polling no timer de 1 a 5 minutos, pausa com posição/ordem existente e remoção dos objetos do painel ao desanexar.
- [x] 2.6 Verificar ciclo de vida, ativação, pausa e retomada no MT5.

## 3. Contexto de mercado

- [x] 3.1 Implementar captura e serialização local de candles M5 de sete dias, cotação e dados de ticks/volume disponíveis, sem calcular direção no EA.
- [x] 3.2 Verificar no Strategy Tester candles, histórico insuficiente e campos ausentes/inconsistentes.
- [x] 3.3 Implementar cliente HTTP POST, timeout configurável, mensagens de erro e parsing do contrato versionado.
- [x] 3.4 Verificar endpoint permitido, serviço indisponível, timeout e versão desconhecida no MT5.
- [x] 3.5 Implementar validação de atualidade, símbolo, fontes, direção, tick size, preços e relação risco-retorno; fixtures estão identificadas e impedidas de negociar.
- [x] 3.6 Exercitar respostas vencidas, inválidas e dependências externas ausentes no terminal.

## 4. Boleta, execução automática e registro

- [x] 4.1 Implementar exibição da direção, referência de entrada a mercado, SL/TP e quantidade ajustável; validar volume, tick size, distância mínima e limite máximo de perda.
- [x] 4.2 Verificar no terminal entradas inválidas e bloqueios correspondentes.
- [x] 4.3 Implementar automação desligada por padrão, execução sem confirmação por operação, pausa com posição aberta, validação de `OrderCheck`/retcode/transação e trava por conta/símbolo entre instâncias do EA.
- [x] 4.4 Verificar ativar/desativar, pausa/retomada, proteções SL/TP e execução em conta demo.
- [x] 4.5 Implementar registro local JSONL versionado de snapshots, respostas, decisões, erros e transações, sem credenciais.
- [x] 4.6 Verificar persistência e falha de escrita no terminal.

## 5. Pacote e validação de instalação

- [x] 5.1 Empacotar fontes/inclusões e escrever guia para instalar na pasta de dados correta, compilar, atualizar Navigator e configurar URL/automação.
- [x] 5.2 Confirmar instalação limpa ou registrar evidência equivalente em MT5 compatível.
- [x] 5.3 Compilar no MetaEditor e validar anexação, fixture, bloqueios, polling, execução automática e envio em conta demo; registrar erros/warnings e ambiente antes de declarar pacote pronto.
