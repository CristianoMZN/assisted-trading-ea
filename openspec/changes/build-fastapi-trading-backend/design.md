# Design

## Context

O EA MQL5 já coleta snapshots M5 e conversa com um contrato versionado, mas não existe serviço de análise implementado. As especificações desta mudança estão em `specs/`; a motivação e os limites do MVP estão em `proposal.md`.

## Goals / Non-Goals

**Goals:** definir fronteiras testáveis entre captura, análise, cálculo de risco, execução e persistência; manter os componentes externos substituíveis; preservar resposta segura quando uma dependência falhar.

**Non-Goals:** executar ordens no Python, hospedar o serviço em nuvem, fixar para sempre um modelo ou fornecedor de notícias, nem depender da saída do modelo para validar limites numéricos.

## Decisions

### Serviço HTTP e fluxo de análise

- O FastAPI expõe uma verificação de saúde e uma rota versionada de análise que segue `contracts/backend-v1.md`; validação de entrada ocorre antes de qualquer chamada externa.
- Um serviço de aplicação coordena o fluxo: coleta de notícias e cálculo técnico podem ocorrer em paralelo; um decisor consolida somente evidências disponíveis; uma etapa determinística valida a decisão e monta a resposta da boleta.
- Se uma etapa necessária falhar, estiver desatualizada ou não produzir dados suficientes, a operação termina em `no_signal` ou erro estruturado, nunca com compra/venda inventada. Falhas parciais de fontes opcionais ficam explícitas nas evidências.
- O modelo recebe formato de saída restrito e não define a resposta HTTP. A validação do backend confere direção, preços, precisão/tick, stop máximo, RR escolhido, perda estimada e retorno líquido após custo. O EA repete as validações críticas antes de enviar ordem.
- O backend não envia ordens ao broker. O EA segue sendo o único componente que executa a boleta e fecha as posições sob sua gestão.

### Componentes de análise

- Adaptadores isolam fontes jornalísticas, facilitando selecionar e substituir fontes sem mudar a API. Cada evidência conserva origem, horário disponível e estado de coleta.
- Indicadores são calculados a partir dos candles/ticks recebidos por código reprodutível. O modelo interpreta os valores e as evidências, mas não cria indicadores nem preenche campos ausentes.
- Prompts dos agentes ficam em arquivos versionados por papel (notícias, técnico quando houver interpretação em linguagem natural, decisão); modelos, limites e parâmetros ficam em configuração. Uma análise registra identificadores de versão e o identificador do modelo escolhido.
- A primeira seleção de modelo OpenRouter e das fontes será configurável e avaliada na implementação. A arquitetura não assume que um modelo específico oferece navegação ou ferramenta de busca; coleta externa é responsabilidade explícita dos adaptadores.

### Risco e contrato do EA

- O request inclui preferência de RR (1:2 ou 1:3), stop máximo em pontos, risco máximo por operação em moeda da conta e custo estimado de ida e volta por contrato. O serviço de risco usa propriedades do símbolo e snapshot para criar níveis candidatos, depois rejeita qualquer nível que viole uma preferência.
- O backend estima perda com a convenção de tick size/tick value do instrumento e o custo informado; o EA recalcula a perda com as propriedades atuais do símbolo antes da execução. Divergência ou dados indisponíveis bloqueiam a ordem.
- A resposta `no_signal` contém `reason_code` estável e uma mensagem curta adequada ao painel. Respostas de compra/venda mantêm os campos existentes de entrada, stop, alvo e RR, acrescentando correlação e metadados de evidência/versão sem expor raciocínio privado.
- A mudança atualiza `contracts/backend-v1.md` e o validador de contrato junto dos tipos MQL5, evitando uma janela em que servidor e EA interpretem payloads diferentes. A versão do contrato permite rejeitar clientes incompatíveis com clareza.

### Persistência e credencial BYOK

- SQLAlchemy isola a aplicação do dialeto do banco; Alembic versiona o esquema. SQLite é o padrão local, escolhido por não exigir serviço separado; `DATABASE_URL` seleciona a conexão. Trocar o URL não garante migração automática de dados: a mudança futura de banco inclui exportação/migração compatível e execução das migrations.
- Persistem análises e estados necessários à auditoria e recuperação local. Dados temporários e snapshots devem ter retenção configurável para controlar tamanho e exposição.
- A chave OpenRouter é fornecida pelo operador para sua instalação. Ela é armazenada como segredo cifrado no banco local, com chave de cifragem mantida no armazenamento de credenciais do sistema operacional; não fica no EA, no repositório, no arquivo de configuração em texto puro nem nos logs. Se o SO não oferecer armazenamento de credenciais utilizável, a configuração por variável de ambiente é alternativa explícita, sem persistir a chave em SQLite.

### Limite diário no EA

- O EA apura o P&L líquido em moeda da conta usando negócios realizados daquele dia e P&L flutuante das posições gerenciadas pelo identificador do EA. Não inclui operações manuais ou de outros EAs.
- A referência do dia é a data de negociação/servidor reportada pelo MetaTrader. Ao alcançar o limite, o EA solicita o fechamento das posições sob sua gestão, deixa de consultar o backend e bloqueia novas ordens até a próxima data de negociação; o painel reporta tanto o gatilho quanto eventual falha de fechamento.
- O EA reconstrói a apuração com histórico da conta e posições atuais depois de reiniciar, em vez de depender somente de memória volátil. A automação continua exigindo reativação manual quando um novo dia começa.

## Risks / Trade-offs

- [Fontes de notícia têm cobertura, atrasos e disponibilidade diferentes] → adaptar fontes, registrar horário/estado e retornar `no_signal` quando faltar evidência essencial.
- [Modelos podem responder fora do formato ou variar entre chamadas] → validar saída estruturada, limitar a resposta a evidências e manter o gate numérico determinístico.
- [Convenções de tick value, conversão cambial e custos podem variar por broker] → validar propriedades do símbolo nos dois lados e bloquear quando não houver cálculo confiável.
- [Credencial local pode ser exposta por malware ou acesso à conta do sistema] → cifrar com chave do cofre do SO, restringir arquivos locais e nunca registrar segredos.
- [Fechar posição ao atingir perda pode falhar por mercado fechado, conexão ou rejeição] → manter bloqueio de novas ordens, exibir o estado real e continuar tentando/permitir ação manual conforme retcodes, sem afirmar que a posição foi encerrada.
- [SQLite pode não atender futura execução concorrente em nuvem] → manter acesso por ORM/migrations e planejar avaliação de banco/lock distribuído antes da implantação compartilhada.

## Migration Plan

1. Atualizar contrato e validador para definir versão, preferências e formato de motivo.
2. Implementar EA e backend em conjunto, mantendo inicialmente automação desligada e exibindo payload/resposta para inspeção.
3. Criar banco local e aplicar migrations; configurar chave OpenRouter e fontes/modelo na instalação.
4. Validar health, erros de contrato, respostas `no_signal`, cálculos de risco, apuração diária e compatibilidade de execução em ambiente de demonstração antes do uso operacional.
5. Para rollback, restaurar a versão anterior do EA/backend e manter cópia do banco anterior à migration; não remover os dados locais até confirmar a versão restaurada.

## Open Questions

- Quais fontes de notícias e qual modelo OpenRouter serão os primeiros selecionados? Essa escolha pode ser feita por configuração/adaptadores durante a implementação sem alterar o contrato ou os limites desta proposta.
- Como o instalador disponibilizará a chave local do sistema operacional em cada plataforma-alvo do backend? A interface concreta depende das plataformas suportadas e pode ser escolhida durante a implementação; a exigência de não guardar segredo em texto puro permanece.
