# Design

## Context

Veja `proposal.md` para motivação e `specs/` para o contrato de comportamento. Este change contém fontes MQL5 e o contrato com um backend Python externo; não implementa o backend. O EA coleta dados, apresenta decisões e executa automaticamente quando o cliente ativa esse modo no painel.

O período de coleta é fixo em M5 com janela móvel de sete dias. O EA coleta candles e campos de ticks/volume que o terminal/broker disponibiliza. Não calcula sinais técnicos, não consulta notícias ou Polymarket diretamente e não presume que campos indisponíveis existam. O backend devolve decisão, entrada a mercado, stop loss, take profit, relação 1:2 ou 1:3 e evidências/fonte.

O serviço externo esperado é uma REST API em Python/FastAPI. Ela recebe snapshots por HTTP `POST` periódico (polling) e concentra análise técnica, fontes de notícia, Polymarket, integração OpenAI e decisão. A implementação do backend permanece fora deste change. A URL do endpoint, timeout e intervalo de polling são configurações do EA; nenhum ambiente ou endereço de hospedagem é presumido. `WebRequest` do MQL5 é síncrono, depende de permissão explícita de URL e não funciona no Strategy Tester. Referências: [programas MQL5](https://www.mql5.com/en/docs/runtime), [WebRequest](https://www.mql5.com/en/docs/network/webrequest), [Expert Advisors e indicadores no MT5](https://www.metatrader5.com/en/terminal/help/algotrading/trade_robots_indicators).

## Goals / Non-Goals

**Goals:** criar EA importável/compilável; transmitir janela local de mercado ao backend por polling de 1 a 5 minutos; apresentar resposta estruturada; permitir ao cliente ajustar quantidade; executar ordens reais automaticamente após ativação manual do modo automático; pausar polling com posição aberta; validar risco, símbolo e resposta do servidor; registrar resultados.

**Non-Goals:** implementar ou hospedar backend FastAPI, fontes de notícia, integração Polymarket/OpenAI ou lógica de decisão; enviar ordens antes da ativação manual da automação; prometer rentabilidade ou escolher parâmetros de estratégia além de validar a relação 1:2 ou 1:3 retornada pelo backend.

## Decisions

### EA cliente MQL5 com módulos distribuídos

Manter um `.mq5` principal como Expert Advisor e separar interface, captura, configuração, transporte, validação de resposta/boleta, execução e registro em `.mqh`. Usar APIs nativas do MQL5, sem DLL ou runtime externo.

### Coleta M5 de sete dias

O timer prepara snapshot de candles M5 dos sete dias anteriores e dados/ticks/volume disponíveis para o símbolo mapeado. Consulta não é feita por tick. Timestamps das barras são convertidos do horário do servidor para UTC e o offset observado é incluído no payload. Campos de agressão compradora/vendedora só são enviados se fornecidos pelo terminal/broker; caso contrário, são explicitamente ausentes. Histórico indisponível ou candle inconsistente bloqueia a submissão do snapshot.

### Backend externo decide

O contrato versionado é JSON sobre HTTP POST e leva símbolo, período, janela temporal, candles, ticks/volume disponíveis e timestamps. Resposta tipada inclui ação, entrada a mercado, stop loss, take profit, relação risco-retorno 1:2 ou 1:3, horários de criação/validade e evidências/fonte separadas. Resposta inválida, desconhecida ou vencida produz sem sinal. Endpoint não contém credenciais de provedores.

### Automação explicitamente ligada, sem confirmação por ordem

Automação inicia desligada e o cliente a liga/desliga manualmente no painel. Enquanto ligada, o timer faz polling no intervalo configurado de 1 a 5 minutos. Se existir posição ou ordem ativa no símbolo mapeado (inclusive posição aberta manualmente), o EA suspende polling e não aceita outra entrada até resolução. Revalidar a ausência de posição antes do envio e usar trava terminal global por conta/símbolo para evitar entradas concorrentes entre instâncias do EA.

Sem confirmação individual, uma resposta `actionable` atual pode gerar uma ordem real a mercado somente quando automação está ligada. Antes de chamar `OrderSend`, validar resposta, direção, volume mínimo/máximo/passo, precisão/distância mínima do símbolo e perda estimada abaixo do limite máximo configurado pelo cliente; rejeitar se o limite não estiver configurado. A estimativa usa `OrderCalcProfit` na moeda da conta e não inclui comissão ou slippage. Enviar SL e TP junto da ordem quando suportado. Se não for possível confirmar proteção, tratar como falha operacional, informar e bloquear novas operações até resolução. Inspecionar retcode e transações do servidor: retorno `true` de `OrderSend` não prova execução.

Nunca reenviar automaticamente uma solicitação de resultado ambíguo. Bloquear nova execução automática até resolver o estado da ordem/posição e registrar o resultado observado. Desligar automação interrompe novos polls/envios sem remover stops/targets de posição já aberta.

### Transporte e fixtures

Usar `WebRequest` HTTP POST com intervalo de 1 a 5 minutos e timeout configurável; documentar liberar endpoint na lista de URLs permitidas do terminal. O Strategy Tester não executa `WebRequest`; permitir fixture identificada para validar painel, parsing e bloqueios, mas fixtures nunca habilitam ordem real.

### Registro local versionado

Registrar pedido/resposta, payload de mercado associado à decisão acionável, quantidade/SL/TP usados, decisão automática, identificadores da ordem e transações/resultado, sem segredos, em arquivo na pasta `Files` da instância do terminal. Falha de persistência é visível e bloqueia novas operações automáticas.

### Empacotamento reproduzível

Manter fontes e guia no repositório, compilar o arquivo principal no MetaEditor e instalar sob `MQL5/Experts` da pasta de dados da instância correta. A compilação final e testes de envio somente podem ser verificados no MetaEditor/terminal MT5 compatível; usar conta demo para validar o fluxo, sem declarar teste real como requisito de desenvolvimento.

## Risks / Trade-offs

- [Dados de ticks/volume variam por broker] → identificar disponibilidade e bloquear snapshots incompletos quando o campo for essencial ao contrato.
- [HTTP síncrono pode bloquear eventos] → limitar intervalo e timeout e não consultar a cada tick.
- [Envio real pode resultar em execução parcial/rejeição] → reconhecer o resultado somente após examinar retcode e transações; nunca repetir automaticamente uma solicitação ambígua.
- [Stop/target podem ser recusados ou não aceitos junto da ordem] → tratar proteção ausente como falha operacional e informar o estado exato.
- [Risco monetário depende de símbolo e cliente] → exigir limite máximo de perda por operação e calcular com propriedades de tick/contrato do terminal.
- [MetaEditor depende de ambiente Windows/MT5] → registrar ambiente e resultado quando disponível; não declarar pacote compilado sem evidência.
