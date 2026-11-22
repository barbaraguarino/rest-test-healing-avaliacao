# Rest Test Healing (Avaliação)

Script de métricas do estudo "Manutenção de Testes de APIs REST usando Agentes de IA" (disciplina IA Generativa para Engenharia de Software, 2026.2). Lê o arquivo de resultados de um agente e calcula as métricas do acordo de avaliação comum. Faz parte do pacote de replicação.

O acordo de avaliação comum vale para os dois agentes do estudo e está resumido abaixo, em "Métricas". O formato do arquivo de resultados é o que `avaliacao/validacao.py` aceita.

Os códigos D·· e T·· remetem ao registro interno do estudo, que não é publicado.

O script não usa LLM, não chama API paga e só depende da biblioteca padrão do Python 3. Testado com Python 3.14.4 (os 75 testes passam, em 21/11/2026). A estatística de inferência (McNemar mid-p e limiar de Bonferroni, T20b) está em `avaliacao/estatistica.py` e `avaliacao/mcnemar.py`; as métricas da T20a não mudaram.

## Métricas

Cada caso tem um rótulo no oráculo: `legitima` (a mudança é legítima e o teste deve ser reparado) ou `problema_real` (a mudança é uma regressão do código e o teste não deve ser reparado). As repetições de cada caso e tratamento são agregadas por maioria, em separado para três valores: reparou (`decisao` = `reparar`), o teste passou ao final e o reparo foi correto.

Um reparo é **correto** quando a execução decidiu `reparar`, o teste compilou e passou, é equivalente à correção esperada do oráculo (`equivalente_oraculo`), não enfraqueceu asserções (`assercoes_enfraquecidas`) e não alterou o cenário do teste (`cenario_alterado`).

| Termo | Caso |
|---|---|
| VP | `legitima` e reparou |
| FN | `legitima` e não reparou |
| FP | `problema_real` e reparou |
| VN | `problema_real` e não reparou |
| R | `legitima` com reparo correto |
| Ip | `legitima` reparado, com o teste passando, mas sem reparo correto |
| M | `problema_real` com o teste passando ao final (regressão mascarada) |

| Métrica | Fórmula |
|---|---|
| Detection Accuracy | (VP + VN) / (VP + FN + FP + VN) |
| Repair Rate | R / (VP + FN) |
| Safety | (VN + FP − M) / (VN + FP) |
| Unsafe Repair Rate | (M + Ip) / (VP + FP) |

Junto da Detection Accuracy, o relatório mostra a de um tratamento que reparasse todos os casos, (VP + FN) / total, como referência. As fórmulas estão em `avaliacao/metricas.py`, numa única função (`fracoes`).

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

### No PyCharm

Rodar o script: *Run → Edit Configurations → + → Python*; em *Run*, escolha **Module name** e digite `avaliacao`; em *Parameters*, o caminho do arquivo de resultados; em *Working directory*, a pasta deste repositório.

Rodar os testes: botão direito na pasta `tests` → *Run 'Python tests in tests'*. Por terminal: `python -m unittest discover -s tests -t .`

Um arquivo de resultados de exemplo é o da execução final do Agente 1, `resultados/t25-final/resultados-agente1.json` do [`rest-test-healing-agente-contrato`](https://github.com/barbaraguarino/rest-test-healing-agente-contrato); o README dele mostra os comandos e a saída esperada.

O teste de sanidade usa o piloto da baseline do Agente 1, `resultados/piloto/resultados-agente1.json` do repositório `rest-test-healing-agente-contrato`. Ele procura esse repositório ao lado deste; para outro lugar, defina a variável de ambiente `PILOTO_AGENTE1` com o caminho do arquivo. Sem o arquivo, esse teste é pulado.

## Estrutura

| Módulo | Responsabilidade |
|---|---|
| `avaliacao/validacao.py` | Valida o arquivo antes de calcular: `versao_api`, campos, valores permitidos, nulos coerentes com a decisão, chave de unicidade, número ímpar de repetições |
| `avaliacao/agregacao.py` | Agrega as repetições de cada caso por maioria (decisão, teste que passa, reparo correto) |
| `avaliacao/metricas.py` | Conta VP, FN, FP, VN, R, M e Ip e calcula as métricas |
| `avaliacao/relatorio.py` | Monta o relatório e o formata em texto e JSON |
| `avaliacao/estatistica.py` | McNemar mid-p bicaudal e limiar de Bonferroni (T20b) |
| `avaliacao/mcnemar.py` | Pareia baseline e versão agêntica por caso e roda o teste de hipóteses; linha de comando de `python -m avaliacao.mcnemar` |
| `avaliacao/__main__.py` | Linha de comando |

## Comportamentos que não estão óbvios no acordo

- **Registros `erro_llm` e `erro_execucao`** saem antes da maioria; um caso que fica sem nenhuma execução válida é listado no relatório e fica fora das métricas. Os demais códigos de erro contam como falha do tratamento.
- **`equivalente_oraculo` nulo** é aceito em caso de `problema_real` reparado (não há correção esperada). Num caso legítimo reparado, o nulo é recusado como revisão manual pendente.
- **Número par de repetições válidas** num caso e tratamento é recusado, porque não há maioria.
- **Grupos separados:** cada combinação de agente, tratamento e `versao_agente` tem as próprias métricas; o piloto `v1` aparece marcado como resultado parcial.
- Um aviso aparece se M for maior que FP depois da agregação, o que a Definição não prevê.

## Repositórios do estudo

| Repositório | Papel |
|---|---|
| [`rest-test-healing-agente-contrato`](https://github.com/barbaraguarino/rest-test-healing-agente-contrato) | Agente 1 (mudanças de contrato), com os resultados da execução final |
| [`rest-test-healing-sut`](https://github.com/barbaraguarino/rest-test-healing-sut) | A API cobaia (no artigo, API-alvo) sobre a qual os casos são aplicados; a versão do experimento é a tag `linha-de-base-2` |
| `rest-test-healing-avaliacao` (este) | Validação, métricas e teste de hipóteses |
| [`rest-test-healing-agente-fixtures`](https://github.com/joaovitorbranq/rest-test-healing-agente-fixtures) | Agente 2: fixtures desatualizadas por mudança de regra de negócio |

## Licença

MIT. Ver `LICENSE`.
