import unittest

from avaliacao.agregacao import CasoAgregado
from avaliacao.estatistica import (LIMIAR, CasosDesemparelhados, mid_p_mcnemar,
                                   parear, testar_agente)


class MidP(unittest.TestCase):
    """Valores conferidos à mão (ver a explicação do README)."""

    def test_b1_c0(self):
        # n=1, k=0: P(X<=0)=1/2, P(X=0)=1/2 -> 2*(1/2-1/4)=0,5
        self.assertEqual(mid_p_mcnemar(1, 0), 0.5)

    def test_b5_c0(self):
        # 2*(1/32 - 1/64) = 1/32
        self.assertEqual(mid_p_mcnemar(5, 0), 0.03125)

    def test_b6_c0(self):
        self.assertEqual(mid_p_mcnemar(6, 0), 1 / 64)

    def test_b1_c2(self):
        # n=3: 2*(4/8 - 3/16) = 0,625
        self.assertEqual(mid_p_mcnemar(1, 2), 0.625)

    def test_simetrico(self):
        self.assertEqual(mid_p_mcnemar(2, 7), mid_p_mcnemar(7, 2))

    def test_b_igual_c_limitado_a_1(self):
        # n=2, k=1: 2*(1 - 1/4)... = 1,5 -> 1
        for b in (1, 2, 5):
            with self.subTest(b=b):
                self.assertEqual(mid_p_mcnemar(b, b), 1.0)

    def test_sem_discordantes_nao_ha_teste(self):
        self.assertIsNone(mid_p_mcnemar(0, 0))

    def test_negativo_falha(self):
        with self.assertRaises(ValueError):
            mid_p_mcnemar(-1, 2)

    def test_nunca_passa_de_1(self):
        for b in range(0, 12):
            for c in range(0, 12):
                p = mid_p_mcnemar(b, c)
                if p is not None:
                    self.assertTrue(0 < p <= 1)


class Bonferroni(unittest.TestCase):
    def test_limiar(self):
        self.assertAlmostEqual(LIMIAR, 0.05 / 3)
        self.assertAlmostEqual(LIMIAR, 0.016667, places=6)

    def test_5_a_0_nao_rejeita_e_6_a_0_rejeita(self):
        self.assertGreater(mid_p_mcnemar(5, 0), LIMIAR)
        self.assertLessEqual(mid_p_mcnemar(6, 0), LIMIAR)


def caso(id_caso, tratamento, rotulo="legitima", reparou=True, passou=True,
         correto=True, agente="agente1", versao="agentica"):
    return CasoAgregado(
        agente=agente, tratamento=tratamento,
        versao_agente=None if tratamento == "baseline" else versao,
        id_caso=id_caso, categoria="x", rotulo_oraculo=rotulo, reparou=reparou,
        passou=passou, reparo_correto=correto, repeticoes=3,
        tempo_s=1.0, tokens=1.0, custo_usd=0.0)


class Pareamento(unittest.TestCase):
    def test_caso_faltando_levanta(self):
        casos = [caso("A", "baseline"), caso("B", "baseline"), caso("A", "agentes")]
        with self.assertRaises(CasosDesemparelhados) as cm:
            parear(casos, "agente1")
        self.assertEqual(cm.exception.so_baseline, ["B"])

    def test_v1_e_agente_unico_ficam_fora(self):
        casos = [caso("A", "baseline"), caso("A", "agentes"),
                 caso("Z", "agentes", versao="v1"), caso("Y", "agente_unico")]
        self.assertEqual(list(parear(casos, "agente1")), ["A"])


class Hipoteses(unittest.TestCase):
    def test_cinco_casos_do_exemplo(self):
        # Detection Accuracy; legítima acerta se repara. Mesmo exemplo de 5 casos
        # explicado ao João: b=1, c=2.
        casos = []
        for i, (rb, ra) in enumerate([(True, True), (False, True), (False, True),
                                      (True, False), (False, False)], 1):
            casos += [caso(f"C{i}", "baseline", reparou=rb),
                      caso(f"C{i}", "agentes", reparou=ra)]
        da = testar_agente(casos, "agente1")[0]
        self.assertEqual((da.b, da.c, da.n, da.p), (1, 2, 3, 0.625))
        self.assertFalse(da.rejeita)

    def test_sem_discordantes_so_descritivo(self):
        casos = [caso("A", "baseline"), caso("A", "agentes")]
        for t in testar_agente(casos, "agente1"):
            self.assertIsNone(t.p)
            self.assertIsNone(t.rejeita)

    def test_subconjuntos_por_hipotese(self):
        casos = [caso("L", "baseline", correto=False), caso("L", "agentes", correto=True),
                 caso("P", "baseline", rotulo="problema_real", reparou=True, passou=True),
                 caso("P", "agentes", rotulo="problema_real", reparou=False, passou=False)]
        da, rr, sf = testar_agente(casos, "agente1")
        self.assertEqual((da.n_pares, rr.n_pares, sf.n_pares), (2, 1, 1))
        self.assertEqual((rr.b, rr.c), (0, 1))
        self.assertEqual((sf.b, sf.c), (0, 1))

    def test_seis_a_zero_rejeita(self):
        casos = []
        for i in range(6):
            casos += [caso(f"L{i}", "baseline", correto=False),
                      caso(f"L{i}", "agentes", correto=True)]
        rr = testar_agente(casos, "agente1")[1]
        self.assertTrue(rr.rejeita)


if __name__ == "__main__":
    unittest.main()
