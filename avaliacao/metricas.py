"""Termos da matriz de confusão e métricas do acordo de avaliação comum.

Fórmulas: Definição do Estudo §4 (árvore GQM). Condições de cada termo:
Planejamento do Estudo §13. Tudo aqui é aritmética sobre os `CasoAgregado`
já calculados; denominador zero devolve `None` ("não definido"), nunca 0 nem 1.
"""

import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class Termos:
    vp: int = 0
    fn: int = 0
    fp: int = 0
    vn: int = 0
    r: int = 0
    m: int = 0
    ip: int = 0

    @property
    def total(self):
        return self.vp + self.fn + self.fp + self.vn


def razao(numerador, denominador):
    """Divisão que devolve `None` quando o denominador é zero."""
    return None if denominador == 0 else numerador / denominador


def contar_termos(casos):
    """Conta VP, FN, FP, VN, R, M e Ip sobre os valores agregados dos casos."""
    c = dict(vp=0, fn=0, fp=0, vn=0, r=0, m=0, ip=0)
    for caso in casos:
        if caso.rotulo_oraculo == "legitima":
            c["vp" if caso.reparou else "fn"] += 1
            if caso.reparo_correto:
                c["r"] += 1
            if caso.reparou and caso.passou and not caso.reparo_correto:
                c["ip"] += 1
        else:
            c["fp" if caso.reparou else "vn"] += 1
            if caso.passou:
                c["m"] += 1
    return Termos(**c)


def fracoes(t):
    """Numerador e denominador de cada métrica (Definição §4, árvore GQM).

    Única definição das fórmulas: as funções abaixo e o relatório leem daqui.
    """
    return {
        "detection_accuracy": (t.vp + t.vn, t.total),
        "repair_rate": (t.r, t.vp + t.fn),
        "safety": (t.vn + t.fp - t.m, t.vn + t.fp),
        "unsafe_repair_rate": (t.m + t.ip, t.vp + t.fp),
    }


def detection_accuracy(t):
    return razao(*fracoes(t)["detection_accuracy"])


def repair_rate(t):
    return razao(*fracoes(t)["repair_rate"])


def safety(t):
    return razao(*fracoes(t)["safety"])


def unsafe_repair_rate(t):
    return razao(*fracoes(t)["unsafe_repair_rate"])


def acerto_de_quem_sempre_repara(t):
    """Detection Accuracy de um tratamento que repara todos os casos.

    É a referência que o Planejamento §15 manda reportar junto da acurácia:
    com a proporção 2:1 (D91) vale 2/3.
    """
    return razao(t.vp + t.fn, t.total)


def avisos(t):
    """Inconsistências possíveis depois de agregar as três maiorias em separado."""
    if t.m > t.fp:
        return [f"M ({t.m}) maior que FP ({t.fp}): a Definição §4 diz M <= FP; "
                "as maiorias de decisão e de passou divergiram"]
    return []


@dataclass(frozen=True)
class Resultado:
    n_casos: int
    termos: Termos
    detection_accuracy: object
    repair_rate: object
    safety: object
    unsafe_repair_rate: object
    referencia_sempre_repara: object
    avisos: tuple
    descritivas: dict
    fracoes: dict


def _descrever(valores):
    if not valores:
        return {"media": None, "mediana": None, "minimo": None, "maximo": None}
    return {"media": statistics.fmean(valores), "mediana": statistics.median(valores),
            "minimo": min(valores), "maximo": max(valores)}


def calcular(casos):
    """Métricas de um conjunto de casos agregados (um tratamento de um agente)."""
    casos = list(casos)
    t = contar_termos(casos)
    return Resultado(
        n_casos=len(casos),
        termos=t,
        detection_accuracy=detection_accuracy(t),
        repair_rate=repair_rate(t),
        safety=safety(t),
        unsafe_repair_rate=unsafe_repair_rate(t),
        referencia_sempre_repara=acerto_de_quem_sempre_repara(t),
        avisos=tuple(avisos(t)),
        descritivas={
            "tempo_s": _descrever([c.tempo_s for c in casos]),
            "tokens": _descrever([c.tokens for c in casos]),
            "custo_usd": _descrever([c.custo_usd for c in casos]),
        },
        fracoes=fracoes(t),
    )


def agrupar(casos, chave):
    """Separa os casos por `chave(caso)`, em ordem estável de aparição ordenada."""
    grupos = {}
    for caso in casos:
        grupos.setdefault(chave(caso), []).append(caso)
    return dict(sorted(grupos.items(), key=lambda item: str(item[0])))


def chave_do_tratamento(caso):
    return (caso.agente, caso.tratamento, caso.versao_agente)


def calcular_por_tratamento(casos, por_categoria=False):
    """`{(agente, tratamento, versao_agente): Resultado}`.

    Com `por_categoria=True`, a chave ganha a categoria como quarto item
    (estatística descritiva por categoria, Planejamento §15).
    """
    if por_categoria:
        def chave(c):
            return chave_do_tratamento(c) + (c.categoria,)
    else:
        chave = chave_do_tratamento
    return {k: calcular(v) for k, v in agrupar(casos, chave).items()}
