# Spec Delta

## Purpose

Entrega o Expert Advisor em formato e estrutura reconhecidos pelo MetaTrader 5, com instruções suficientes para o operador copiar, compilar e encontrar o programa no Navigator do terminal.

## ADDED Requirements

### Requirement: Distribuição é compatível com o fluxo MQL5 do MT5
A distribuição SHALL incluir um arquivo principal de Expert Advisor `.mq5` e todos os arquivos de inclusão necessários, com organização compatível com o MetaEditor e sem dependência de arquivos MQL4.

#### Scenario: Abrir o projeto no MetaEditor
- **WHEN** o operador abre o arquivo principal do pacote no MetaEditor do MetaTrader 5
- **THEN** o projeto e seus arquivos de inclusão são reconhecidos como código MQL5 para um Expert Advisor

#### Scenario: Pacote incompleto
- **WHEN** um arquivo de inclusão necessário está ausente
- **THEN** a documentação ou a compilação identifica a dependência ausente em vez de apresentar o pacote como pronto

### Requirement: Expert Advisor pode ser compilado para o Navigator
O código-fonte SHALL compilar no MetaEditor para gerar o executável `.ex5` do Expert Advisor, sem erros de compilação.

#### Scenario: Compilação concluída
- **WHEN** o operador compila o arquivo principal no MetaEditor
- **THEN** é produzido um arquivo `.ex5` utilizável pelo MT5 na pasta de Experts correspondente

#### Scenario: Compilação falha
- **WHEN** o compilador encontra erros
- **THEN** o pacote não é descrito como pronto para uso e as instruções apontam para o log de compilação do MetaEditor

### Requirement: Instalação localiza o EA na pasta de dados do terminal
A distribuição SHALL instruir o operador a usar a pasta de dados da instância de MetaTrader 5 pretendida e localizar o Expert Advisor sob `MQL5/Experts`, atualizar o Navigator e anexar o EA ao gráfico.

#### Scenario: Instalação na instância correta
- **WHEN** o operador copia o pacote para `MQL5/Experts` dentro da pasta de dados aberta pelo terminal pretendido e compila
- **THEN** o EA compilado aparece em Expert Advisors no Navigator após atualizar a lista

#### Scenario: Mais de uma instância do MT5
- **WHEN** há múltiplas instalações ou contas de broker no computador
- **THEN** as instruções orientam a abrir a pasta de dados pela própria instância em uso para evitar instalar na pasta de outro terminal
