# Instalação e configuração do EA

## Iniciar o backend local

Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend
```

O serviço usa `127.0.0.1:8000` por padrão. Configure `InpBackendUrl` para `http://127.0.0.1:8000/v1/analyze` e libere o endereço em **Ferramentas → Opções → Expert Advisors** do terminal. `GET /health` informa as versões do serviço e do contrato. A requisição e resposta seguem `contracts/backend-v1.md` (schema 1.1).

Para habilitar decisões, defina `OPENROUTER_MODEL` e disponibilize uma chave OpenRouter salva cifrada no cofre do sistema operacional. Se o cofre não estiver disponível, o backend aceita `OPENROUTER_API_KEY` do ambiente sem gravá-la no banco. Os feeds HTTPS opcionais são configurados em `NEWS_RSS_URLS`. Instruções de instalação, configuração, banco, retenção e estados de erro estão em [backend/README.md](../../../backend/README.md).

## Instalar na instância correta

1. Abra a instância do MetaTrader 5 em que o EA será usado.
2. No terminal, escolha **Arquivo → Abrir pasta de dados**.
3. Copie a pasta `AssistedTradingEA` inteira para `MQL5/Experts` dentro dessa pasta de dados. Preserve o `.mq5` e a subpasta `Include` com todos os `.mqh`.
4. Abra `MQL5/Experts/AssistedTradingEA/AssistedTradingEA.mq5` no MetaEditor dessa instância e compile com **F7**.
5. Verifique o painel **Errors** do MetaEditor. Não use o pacote como pronto se a compilação indicar erros.
6. Volte ao MT5, clique com o botão direito em **Expert Advisors** no Navigator e escolha **Atualizar**. Se necessário, reinicie o terminal.

## Configurar o EA

- **InpLogicalInstrument:** escolha WIN ou WDO.
- **InpBrokerSymbol:** informe o nome exato do contrato no broker, incluindo vencimento/sufixo. O EA bloqueia se o nome não corresponder ao instrumento lógico.
- **InpBackendUrl:** URL HTTP/HTTPS da rota FastAPI que implementa o contrato `contracts/backend-v1.md`.
- **InpPollingIntervalMinutes:** intervalo inicial de 1 a 5 minutos; também pode ser alterado no campo do painel enquanto o EA está anexado.
- **InpHttpTimeoutMs:** timeout HTTP, de 250 a 30000 ms.
- **InpInitialContracts:** quantidade inicial; a quantidade pode ser ajustada no painel e deve respeitar mínimo, máximo e passo do símbolo.
- **Risco no painel:** escolha RR geométrico 1:2/1:3 e informe stop máximo em pontos, perda máxima por operação, custo de ida e volta por contrato e limite de perda diária, na moeda da conta para valores monetários. Valores inválidos ou zero nos limites obrigatórios bloqueiam a automação.
- **Limite diário:** agrega P&L realizado e flutuante do Magic ID do EA, incluindo comissão, taxas e swap. Quando o limite é atingido, o EA desliga automação, fecha apenas posições gerenciadas e mantém o bloqueio até o próximo dia do servidor. A automação requer ativação manual novamente.
- **Estimativa de risco:** backend e EA incluem o custo configurado na perda e exigem retorno líquido positivo após custos. Slippage não está incluído.
- **InpUseFixture:** use somente para testar a interface. Fixtures nunca podem ligar execução real.
- **InpLogFileName:** arquivo JSON Lines gravado em `MQL5/Files` da pasta de dados dessa instância.

No terminal, abra **Ferramentas → Opções → Expert Advisors** e adicione o endereço do backend à lista de URLs permitidas para `WebRequest`. Ative **Negociação algorítmica** no terminal e permita negociação nas propriedades do EA.

## Ativação e comportamento

O EA começa com automação desligada. Ajuste quantidade e intervalo no painel e só então clique **AUTOMAÇÃO: LIGADA**. Com automação ativa, uma resposta atual e válida que proponha compra/venda pode gerar ordem real a mercado sem confirmação individual, desde que passe pelas validações de símbolo, volume, stop, alvo e perda máxima.

O polling pausa enquanto houver posição ou ordem ativa no símbolo e retoma após o encerramento. Desligar a automação impede novas consultas e entradas; não remove SL/TP de uma posição já aberta. Se o estado de uma solicitação ficar ambíguo ou o registro local falhar, o EA bloqueia novas operações para evitar repetição automática. Resposta `no_signal`, erro HTTP, versão incompatível ou dados insuficientes nunca geram ordem.

Use primeiro uma conta demo para conferir endpoint permitido, mapeamento, tamanho da posição, proteções SL/TP, pause/resume e logs. O backend FastAPI está no diretório `backend/`; Polymarket não está integrado e aparece como fonte `not_relevant`.

## Referências do fluxo de instalação

- O guia oficial do [MetaTrader 5 sobre Expert Advisors](https://www.metatrader5.com/en/terminal/help/algotrading/autotrading) descreve `MQL5/Experts`, **Abrir pasta de dados**, compilação no MetaEditor com **F7** e saída `.ex5`.
- A [estrutura de pastas do MetaEditor](https://www.metatrader5.com/en/metaeditor/help/structure) confirma que `Experts` recebe fontes `.mq5`/`.mqh` e que `Files` é a pasta de dados usada pelos EAs.
- O [Navigator do MetaEditor](https://www.metatrader5.com/en/metaeditor/help/workspace/navigator) descreve como atualizar a árvore de fontes.

O ambiente de desenvolvimento deste pacote não contém MetaEditor/terminal MT5, portanto a compilação e o teste limpo de instalação precisam ser concluídos em uma instância MT5 compatível.
