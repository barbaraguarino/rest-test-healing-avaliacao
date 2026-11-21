# Rest Test Healing (Avaliação)

Script de métricas do estudo "Manutenção de Testes de APIs REST usando Agentes de IA" (disciplina IA Generativa para Engenharia de Software, 2026.2). Lê o arquivo de resultados de um agente e calcula as métricas do acordo de avaliação comum. Faz parte do pacote de replicação.

Este repositório **implementa** o acordo; ele não o define. Métricas, fórmulas, critério de reparo correto, formato do arquivo de resultados e tratamento de execuções com erro estão no documento *2. Planejamento do Estudo* (§13, "Acordo de avaliação comum", e §15, "Plano de Análise") e na *1. Definição do Estudo* (§4, matriz de confusão e árvore GQM), no repositório `rest-test-healing-estudo`. Se este código e esses documentos divergirem, valem os documentos.

O script não usa LLM, não chama API paga e só depende da biblioteca padrão do Python 3. Testado com Python 3.14.4 (os 75 testes passam, em 21/11/2026). A estatística de inferência (McNemar mid-p e limiar de Bonferroni, T20b) está em `avaliacao/estatistica.py` e `avaliacao/mcnemar.py`; as métricas da T20a não mudaram.

## Como rodar

Na pasta do repositório:

```
python -m avaliacao caminho/para/resultados-agente1.json
python -m avaliacao caminho/para/resultados-agente1.json --json metricas.json
```

- A saída em texto vai para a tela: matriz de confusão, métricas com o cálculo ao lado (ex.: `8/12`), estatísticas descritivas de tempo, tokens e custo, e os mesmos blocos por categoria de mudança.
- `--json` grava o mesmo relatório em JSON, para a análise estatística.
- Métrica com denominador zero aparece como `n/d` (texto) e `null` (JSON).
- Se o arquivo não passar na validação, nenhuma métrica é calculada: o script lista todos os problemas e termina com código 2.

### Teste de hipóteses (T20b), pelo PyCharm

Compara a baseline com a versão agêntica, por agente: três hipóteses (Detection Accuracy em todos os casos, Repair Rate nos legítimos, Safety nos `problema_real`), com McNemar mid-p bicaudal (D126) e limiar de Bonferroni α/3 ≈ 0,0167 (D84).

*Run → Edit Configurations → + → Python*; em *Run*, escolha **Module name** e digite `avaliacao.mcnemar`; em *Parameters*, os caminhos dos arquivos de resultados separados por espaço (baseline e versão agêntica; um arquivo por tratamento, ou um só se ele já tiver os dois); para gravar também em JSON, acrescente `--json saida.json`; em *Working directory*, a pasta deste repositório.

- Cada arquivo passa pela mesma validação das métricas; se algum for recusado, nada é testado (código 2).
- O pareamento é por `id_caso`, depois da maioria das repetições. Se um caso faltar num dos tratamentos, o script para e lista os casos (código 3).
- Na tabela: b = só a baseline acertou; c = só a versão agêntica acertou; n = b + c. Sem nenhum par discordante (n = 0) não há teste, só o descritivo. A decisão compara o p direto com o limiar α/3, sem p ajustado (D140).
- O agente único e a versão `v1` ficam fora do teste.

### No IntelliJ

Rodar o script: *Run → Edit Configurations → + → Python*; em *Run*, escolha **Module name** e digite `avaliacao`; em *Parameters*, o caminho do arquivo de resultados; em *Working directory*, a pasta deste repositório.

Rodar os testes: botão direito na pasta `tests` → *Run 'Python tests in tests'*. Por terminal: `python -m unittest discover -s tests -t .`

O teste de sanidade usa o piloto da baseline do Agente 1, `resultados/piloto/resultados-agente1.json` do repositório `rest-test-healing-agente-contrato`. Ele procura esse repositório ao lado deste; para outro lugar, defina a variável de ambiente `PILOTO_AGENTE1` com o caminho do arquivo. Sem o arquivo, esse teste é pulado.

## Estrutura

| Módulo | Responsabilidade |
|---|---|
| `avaliacao/validacao.py` | Valida o arquivo antes de calcular: `versao_api`, campos, valores permitidos, nulos coerentes com a decisão, chave de unicidade, número ímpar de repetições |
| `avaliacao/agregacao.py` | Agrega as repetições de cada caso por maioria (decisão, teste que passa, reparo correto) |
| `avaliacao/metricas.py` | Conta VP, FN, FP, VN, R, M e Ip e calcula as métricas |
| `avaliacao/relatorio.py` | Monta o relatório e o formata em texto e JSON |
| `avaliacao/__main__.py` | Linha de comando |

## Comportamentos que não estão óbvios no acordo

- **Registros `erro_llm` e `erro_execucao`** saem antes da maioria; um caso que fica sem nenhuma execução válida é listado no relatório e fica fora das métricas. Os demais códigos de erro contam como falha do tratamento.
- **`equivalente_oraculo` nulo** é aceito em caso de `problema_real` reparado (não há correção esperada). Num caso legítimo reparado, o nulo é recusado como revisão manual pendente.
- **Número par de repetições válidas** num caso e tratamento é recusado, porque não há maioria.
- **Grupos separados:** cada combinação de agente, tratamento e `versao_agente` tem as próprias métricas; o piloto `v1` aparece marcado como resultado parcial.
- Um aviso aparece se M for maior que FP depois da agregação, o que a Definição não prevê.
