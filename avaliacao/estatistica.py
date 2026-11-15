"""McNemar mid-p e limiar de Bonferroni (D84, D126).

Só biblioteca padrão. Entra a lista de `CasoAgregado` (já com a maioria da
D81) e sai, por agente, uma linha por hipótese: b, c, n, p, limiar e decisão.
Este módulo não muda a agregação nem as métricas; apenas as usa.
"""

from dataclasses import dataclass
from math import comb

ALFA = 0.05
HIPOTESES_POR_AGENTE = 3
LIMIAR = ALFA / HIPOTESES_POR_AGENTE  # D84: cerca de 0,0167

BASELINE = "baseline"
AGENTICA = "agentes"


class CasosDesemparelhados(Exception):
    """Um caso existe num tratamento e falta no outro: o pareamento não é possível."""

    def __init__(self, agente, so_baseline, so_agentica):
        self.agente = agente
        self.so_baseline = sorted(so_baseline)
        self.so_agentica = sorted(so_agentica)
        super().__init__(
            f"{agente}: casos sem par. Só na baseline: {self.so_baseline}. "
            f"Só na versão agêntica: {self.so_agentica}.")


def mid_p_mcnemar(b, c):
    """p bicaudal do McNemar mid-p (D126). `None` quando n = b + c = 0.

    n = b + c, X ~ Binomial(n; 0,5),
    p = 2 x [P(X <= min(b,c)) - 1/2 P(X = min(b,c))], limitado a 1.
    Contas com inteiros (math.comb) e uma só divisão no fim.
    """
    if b < 0 or c < 0:
        raise ValueError("b e c não podem ser negativos")
    n = b + c
    if n == 0:
        return None
    k = min(b, c)
    acumulado = sum(comb(n, i) for i in range(k + 1))
    # P(X<=k) - P(X=k)/2, com tudo sobre 2**n; o dobro cancela o 1/2 e o 2 de fora.
    dobro = 2 * acumulado - comb(n, k)
    return min(1.0, dobro / 2 ** n)


@dataclass(frozen=True)
class Teste:
    agente: str
    hipotese: str
    nome: str
    n_pares: int
    acertos_baseline: int  # descritivo: acertos de cada lado nos pares
    acertos_agentica: int
    b: int  # só a baseline acertou
    c: int  # só a versão agêntica acertou
    p: object  # None sem pares discordantes
    limiar: float
    rejeita: object  # None quando não há teste

    @property
    def n(self):
        return self.b + self.c


# (código, nome, quais casos entram, o que conta como acerto)
HIPOTESES = (
    ("detection_accuracy", "Detection Accuracy", lambda c: True,
     lambda c: c.reparou == (c.rotulo_oraculo == "legitima")),
    ("repair_rate", "Repair Rate", lambda c: c.rotulo_oraculo == "legitima",
     lambda c: c.reparo_correto),
    ("safety", "Safety", lambda c: c.rotulo_oraculo == "problema_real",
     lambda c: not c.passou),
)


def parear(casos, agente):
    """`{id_caso: (baseline, agentica)}` de um agente; levanta se faltar par.

    Só entram a baseline e a versão agêntica; o agente único e a v1 ficam fora.
    """
    base = {c.id_caso: c for c in casos
            if c.agente == agente and c.tratamento == BASELINE}
    agen = {c.id_caso: c for c in casos
            if c.agente == agente and c.tratamento == AGENTICA
            and c.versao_agente == "agentica"}
    if set(base) != set(agen):
        raise CasosDesemparelhados(agente, set(base) - set(agen), set(agen) - set(base))
    return {i: (base[i], agen[i]) for i in sorted(base)}


def testar_agente(casos, agente):
    """Três testes (um por hipótese) do agente, comparando baseline e agêntica."""
    pares = parear(casos, agente)
    testes = []
    for codigo, nome, filtro, acerto in HIPOTESES:
        selecionados = [(b, a) for b, a in pares.values() if filtro(b)]
        b = sum(1 for base, ag in selecionados if acerto(base) and not acerto(ag))
        c = sum(1 for base, ag in selecionados if acerto(ag) and not acerto(base))
        p = mid_p_mcnemar(b, c)
        testes.append(Teste(
            agente, codigo, nome, len(selecionados),
            sum(1 for base, _ in selecionados if acerto(base)),
            sum(1 for _, ag in selecionados if acerto(ag)),
            b, c, p, LIMIAR, None if p is None else p <= LIMIAR))
    return testes
