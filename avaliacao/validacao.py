"""Validação do arquivo de resultados antes de qualquer cálculo.

As regras vêm do Planejamento do Estudo (§13, "Arquivo de resultados", e §15,
"Validação dos dados antes da análise") e das decisões D74 e D87. Esta etapa
não calcula métrica: só diz se o arquivo pode ser usado e, se não puder,
lista todos os problemas de uma vez.
"""

import json

VERSAO_API_ACORDADA = "linha-de-base-2"

CAMPOS = (
    "id_caso", "agente", "tratamento", "versao_agente", "categoria",
    "rotulo_oraculo", "decisao", "compilou", "passou", "equivalente_oraculo",
    "assercoes_enfraquecidas", "cenario_alterado", "repeticao", "tempo_s",
    "tokens", "custo_usd", "erro",
)

AGENTES = ("agente1", "agente2")
TRATAMENTOS = ("baseline", "agentes", "agente_unico")
VERSOES_AGENTE = ("v1", "agentica")
ROTULOS = ("legitima", "problema_real")
DECISOES = ("reparar", "nao_reparar")
CODIGOS_ERRO = (
    "limite_chamadas", "max_tokens", "guarda", "timeout",
    "erro_llm", "saida_invalida", "erro_execucao",
)

# Falhas de infraestrutura: o caso é reexecutado e o registro não entra
# nas métricas (Planejamento §15, "Execuções com erro").
ERROS_DE_INFRAESTRUTURA = ("erro_llm", "erro_execucao")

# Campos que só fazem sentido quando o artefato foi alterado.
CAMPOS_DO_REPARO = (
    "compilou", "equivalente_oraculo", "assercoes_enfraquecidas",
    "cenario_alterado",
)

CHAVE_DE_UNICIDADE = ("id_caso", "agente", "tratamento", "versao_agente", "repeticao")


class ArquivoInvalido(Exception):
    """O arquivo de resultados não passou na validação; `problemas` lista os motivos."""

    def __init__(self, problemas):
        self.problemas = list(problemas)
        super().__init__("\n".join(self.problemas))


def _eh_inteiro(valor):
    # bool é subclasse de int em Python; `True` não é um número válido aqui.
    return isinstance(valor, int) and not isinstance(valor, bool)


def _eh_numero(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and valor >= 0)


def _validar_dominios(r):
    problemas = []

    def exigir_em(campo, permitidos):
        if r[campo] not in permitidos:
            problemas.append(f"{campo}={r[campo]!r} fora de {list(permitidos)}")

    for campo in ("id_caso", "categoria"):
        if not isinstance(r[campo], str) or not r[campo]:
            problemas.append(f"{campo}={r[campo]!r} deve ser texto não vazio")
    exigir_em("agente", AGENTES)
    exigir_em("tratamento", TRATAMENTOS)
    exigir_em("rotulo_oraculo", ROTULOS)
    exigir_em("decisao", DECISOES)
    if r["versao_agente"] is not None:
        exigir_em("versao_agente", VERSOES_AGENTE)
    if r["erro"] is not None:
        exigir_em("erro", CODIGOS_ERRO)

    if not isinstance(r["passou"], bool):
        problemas.append(f"passou={r['passou']!r} deve ser true ou false")
    for campo in CAMPOS_DO_REPARO:
        if r[campo] is not None and not isinstance(r[campo], bool):
            problemas.append(f"{campo}={r[campo]!r} deve ser true, false ou null")

    if not _eh_inteiro(r["repeticao"]) or r["repeticao"] < 1:
        problemas.append(f"repeticao={r['repeticao']!r} deve ser inteiro >= 1")
    if not _eh_inteiro(r["tokens"]) or r["tokens"] < 0:
        problemas.append(f"tokens={r['tokens']!r} deve ser inteiro >= 0")
    for campo in ("tempo_s", "custo_usd"):
        if not _eh_numero(r[campo]):
            problemas.append(f"{campo}={r[campo]!r} deve ser número >= 0")
    return problemas


def _validar_coerencia(r):
    """Regras que cruzam campos: versão por tratamento (D74, D87) e nulos."""
    problemas = []
    if r["tratamento"] == "baseline" and r["versao_agente"] is not None:
        problemas.append("baseline exige versao_agente nulo")
    if r["tratamento"] == "agentes" and r["versao_agente"] is None:
        problemas.append("tratamento agentes exige versao_agente v1 ou agentica")
    if r["tratamento"] == "agente_unico" and r["versao_agente"] != "agentica":
        problemas.append("agente_unico exige versao_agente agentica (D87)")

    if r["decisao"] == "nao_reparar":
        # Nulo significa "não se aplica", nunca "falso" (§13).
        for campo in CAMPOS_DO_REPARO:
            if r[campo] is not None:
                problemas.append(f"{campo} deve ser nulo quando decisao=nao_reparar")
    elif r["decisao"] == "reparar":
        for campo in ("compilou", "assercoes_enfraquecidas", "cenario_alterado"):
            if r[campo] is None:
                problemas.append(f"{campo} nulo com decisao=reparar")
        # Numa regressão não há correção esperada, então o nulo é legítimo
        # (lacuna de redação da D74, registrada para a dupla).
        if r["equivalente_oraculo"] is None and r["rotulo_oraculo"] == "legitima":
            problemas.append(
                "equivalente_oraculo nulo em caso legítimo reparado: "
                "pendente de revisão manual (D80)")
    return problemas


def validar_registro(r):
    """Devolve a lista de problemas de um registro (vazia se estiver válido)."""
    ausentes = [c for c in CAMPOS if c not in r]
    if ausentes:
        return [f"campos ausentes: {', '.join(ausentes)}"]
    problemas = _validar_dominios(r)
    if not problemas:
        problemas = _validar_coerencia(r)
    return problemas


def validar(dados, versao_api=VERSAO_API_ACORDADA):
    """Valida o arquivo inteiro e lança `ArquivoInvalido` com todos os problemas.

    Devolve a lista de registros quando tudo está certo.
    """
    if not isinstance(dados, dict) or "execucoes" not in dados or "versao_api" not in dados:
        raise ArquivoInvalido(["o arquivo deve ser um objeto com 'versao_api' e 'execucoes'"])

    problemas = []
    if dados["versao_api"] != versao_api:
        problemas.append(f"versao_api={dados['versao_api']!r}, esperado {versao_api!r}")
    execucoes = dados["execucoes"]
    if not isinstance(execucoes, list):
        raise ArquivoInvalido(problemas + ["'execucoes' deve ser uma lista"])

    chaves_vistas = set()
    repeticoes_validas = {}
    identidade_do_caso = {}
    for i, r in enumerate(execucoes):
        onde = f"registro {i}"
        if not isinstance(r, dict):
            problemas.append(f"{onde}: deve ser um objeto")
            continue
        if "id_caso" in r:
            onde += f" ({r['id_caso']})"
        erros = validar_registro(r)
        problemas.extend(f"{onde}: {p}" for p in erros)
        if erros:
            continue

        chave = tuple(r[c] for c in CHAVE_DE_UNICIDADE)
        if chave in chaves_vistas:
            problemas.append(f"{onde}: chave repetida {chave}")
        chaves_vistas.add(chave)
        # Rótulo e categoria são do caso, não da repetição: devem coincidir.
        caso = (r["agente"], r["tratamento"], r["versao_agente"], r["id_caso"])
        identidade = (r["rotulo_oraculo"], r["categoria"])
        if identidade_do_caso.setdefault(caso, identidade) != identidade:
            problemas.append(
                f"{onde}: rotulo_oraculo/categoria diferem de outra repetição do caso")
        if r["erro"] not in ERROS_DE_INFRAESTRUTURA:
            grupo = chave[:-1]
            repeticoes_validas[grupo] = repeticoes_validas.get(grupo, 0) + 1

    # Sem número ímpar de repetições não há maioria (D81).
    for grupo, quantas in sorted(repeticoes_validas.items(), key=str):
        if quantas % 2 == 0:
            problemas.append(
                f"{grupo}: {quantas} repetições válidas (número par); "
                "reexecutar para obter número ímpar (D81)")

    if problemas:
        raise ArquivoInvalido(problemas)
    return execucoes


def carregar(caminho):
    """Lê o JSON em UTF-8 e valida; devolve a lista de registros."""
    with open(caminho, encoding="utf-8") as arquivo:
        return validar(json.load(arquivo))
