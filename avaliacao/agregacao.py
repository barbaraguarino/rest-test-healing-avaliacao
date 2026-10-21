"""Agregação das repetições de cada caso por maioria (D81).

Entra a lista de registros já validada por `validacao`. Sai um resultado por
caso e tratamento, com três valores binários agregados separadamente
(decisão, teste que passa ao final e reparo correto) e os valores
descritivos de tempo, tokens e custo.
"""

from dataclasses import dataclass

from avaliacao.validacao import ERROS_DE_INFRAESTRUTURA


@dataclass(frozen=True)
class CasoAgregado:
    agente: str
    tratamento: str
    versao_agente: object  # texto ou None (baseline)
    id_caso: str
    categoria: str
    rotulo_oraculo: str
    reparou: bool
    passou: bool
    reparo_correto: bool
    repeticoes: int
    tempo_s: float
    tokens: float
    custo_usd: float


def reparo_correto(r):
    """Critério de reparo correto do Planejamento §13, sobre uma execução.

    Compara com `True`/`False` de propósito: nulo (não se aplica) nunca
    conta como verdadeiro.
    """
    return (r["decisao"] == "reparar"
            and r["compilou"] is True
            and r["passou"] is True
            and r["equivalente_oraculo"] is True
            and r["assercoes_enfraquecidas"] is False
            and r["cenario_alterado"] is False)


def maioria(valores):
    """Valor que aparece em mais da metade das repetições.

    Número par de repetições não tem maioria garantida; a validação já
    recusa esse caso, e aqui falhar alto evita um empate silencioso.
    """
    if not valores or len(valores) % 2 == 0:
        raise ValueError(f"maioria exige número ímpar de valores, recebeu {len(valores)}")
    return sum(valores) > len(valores) / 2


def _media(valores):
    return sum(valores) / len(valores)


def agregar(registros):
    """Devolve `(casos, excluidos)`.

    `casos` tem um `CasoAgregado` por (agente, tratamento, versao_agente,
    id_caso). Registros `erro_llm` e `erro_execucao` saem antes da maioria
    (Planejamento §15); o caso que fica sem nenhuma execução válida vai para
    `excluidos`, uma lista de chaves, para ser reportado.
    """
    grupos = {}
    for r in registros:
        chave = (r["agente"], r["tratamento"], r["versao_agente"], r["id_caso"])
        grupos.setdefault(chave, []).append(r)

    casos, excluidos = [], []
    for chave in sorted(grupos, key=str):
        validos = [r for r in grupos[chave] if r["erro"] not in ERROS_DE_INFRAESTRUTURA]
        if not validos:
            excluidos.append(chave)
            continue
        primeiro = validos[0]
        casos.append(CasoAgregado(
            *chave,
            categoria=primeiro["categoria"],
            rotulo_oraculo=primeiro["rotulo_oraculo"],
            reparou=maioria([r["decisao"] == "reparar" for r in validos]),
            passou=maioria([r["passou"] for r in validos]),
            reparo_correto=maioria([reparo_correto(r) for r in validos]),
            repeticoes=len(validos),
            tempo_s=_media([r["tempo_s"] for r in validos]),
            tokens=_media([r["tokens"] for r in validos]),
            custo_usd=_media([r["custo_usd"] for r in validos]),
        ))
    return casos, excluidos
