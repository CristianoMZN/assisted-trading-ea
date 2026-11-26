# Tasks

## 1. Contrato e compatibilidade

- [x] 1.1 Atualizar `contracts/backend-v1.md` e `scripts/backend_contract.py` com preferências de RR, stop máximo, limites/custos, correlação e `reason_code`; verificar com os testes de contrato que payloads válidos e inválidos são classificados corretamente.
- [x] 1.2 Atualizar tipos e cliente MQL5 para serializar as preferências e ler resposta versionada/`no_signal`; verificar com casos de fixture que EA e validador interpretam os mesmos campos.

## 2. Serviço FastAPI e configuração

- [x] 2.1 Criar a aplicação FastAPI, configuração local e rotas de health/análise; verificar inicialização local e respostas documentadas para health e versão incompatível.
- [x] 2.2 Documentar configuração de execução, variáveis e erros operacionais; verificar que um operador consegue iniciar o backend seguindo as instruções.

## 3. Persistência e credencial local

- [x] 3.1 Configurar SQLAlchemy, URL SQLite padrão, modelos e migrations Alembic para análise, evidências e versões; verificar criação de banco vazio e migração sobre banco existente.
- [x] 3.2 Implementar armazenamento BYOK cifrado usando chave do cofre do sistema operacional, com fallback explícito por variável de ambiente; verificar que nenhum segredo aparece em logs, respostas ou exportações.
- [x] 3.3 Implementar persistência e retenção configurável de registros de análise; verificar recuperação local de resultado, estado e versões após reinício.

## 4. Análise e decisão

- [x] 4.1 Implementar adaptadores de notícias com origem, horário e estados de ausência/falha; verificar cenários com notícia, sem notícia e fonte indisponível.
- [x] 4.2 Implementar indicadores determinísticos a partir do snapshot e prompts versionados para as etapas de interpretação/decisão; verificar dados suficientes, dados insuficientes e associação das versões ao resultado.
- [x] 4.3 Integrar OpenRouter com modelo configurável e chave BYOK, validação de saída estruturada e tratamento de falhas; verificar que chave ausente, timeout e saída fora do esquema nunca geram compra/venda.
- [x] 4.4 Implementar a validação determinística de direção, tick, stop, RR, perda e retorno líquido após custo; verificar motivos estáveis de `no_signal` para cada limite violado.

## 5. Preferências, painel e limite diário no EA

- [x] 5.1 Adicionar ao painel campos de RR, stop máximo, risco por operação, custo por contrato e limite diário; verificar validação local e serialização dos valores no request.
- [x] 5.2 Exibir `reason_code` e explicação de `no_signal` sem preparar ordem; verificar que resposta ausente ou inválida continua sem sinal.
- [x] 5.3 Apurar P&L líquido diário em moeda da conta por identificador deste EA, incluindo realizado e flutuante, e fechar posições gerenciadas ao atingir o limite; verificar exclusão de operações de terceiros e comportamento após reinício.
- [x] 5.4 Suspender consultas e novas ordens após o limite, apresentar falhas de fechamento e exigir reativação manual no próximo dia de negociação; verificar a transição de bloqueio e reinício diário.

## 6. Integração e documentação

- [x] 6.1 Executar verificações integradas de contrato, análise, persistência, limites e compatibilidade EA/backend; registrar resultados com cenários de resposta válida, `no_signal`, indisponibilidade e limite diário atingido.
- [x] 6.2 Atualizar documentação operacional e de configuração do projeto; verificar consistência entre README, contrato, nomes de configuração e comportamento implementado.
- [x] 6.3 Carregar `.env` automaticamente e configurar modelos independentes para interpretação técnica e decisão; executar ambos os agentes no pipeline e persistir a versão de cada modelo.
