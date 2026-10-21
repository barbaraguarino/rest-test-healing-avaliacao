import unittest

from avaliacao.agregacao import CasoAgregado
from avaliacao.metricas import (Termos, avisos, calcular, calcular_por_tratamento,
                                contar_termos, razao)


def caso(rotulo, reparou, passou=False, correto=False, id_caso="X", categoria="c",
         tratamento="baseline", versao=None, tempo=1.0, tokens=0, custo=0.0):
    return CasoAgregado("agente1", tratamento, versao, id_caso, categoria, rotulo,
                        reparou, passou, correto, 3, tempo, tokens, custo)


L, P = "legitima", "problema_real"


class Termos_(unittest.TestCase):
    def test_cada_condicao_da_tabela(self):
        casos = [
            caso(L, True, True, True),      # VP, R
            caso(L, True, True, False),     # VP, Ip
            caso(L, True, False, False),    # VP (teste ainda falha: não é Ip)
            caso(L, False),                 # FN
            caso(P, True, True),            # FP, M
            caso(P, True, False),           # FP
            caso(P, False),                 # VN
        ]
        self.assertEqual(contar_termos(casos), Termos(vp=3, fn=1, fp=2, vn=1, r=1, m=1, ip=1))

    def test_sem_casos(self):
        self.assertEqual(contar_termos([]), Termos())


class Metricas(unittest.TestCase):
    def test_exemplo_feito_a_mao(self):
        # VP=2 FN=1 FP=1 VN=2, R=1, M=1, Ip=1  ->  6 casos
        casos = [caso(L, True, True, True), caso(L, True, True, False), caso(L, False),
                 caso(P, True, True), caso(P, False), caso(P, False)]
        r = calcular(casos)
        self.assertEqual(r.termos, Termos(vp=2, fn=1, fp=1, vn=2, r=1, m=1, ip=1))
        self.assertAlmostEqual(r.detection_accuracy, 4 / 6)   # (2+2)/6
        self.assertAlmostEqual(r.repair_rate, 1 / 3)          # R/(VP+FN)
        self.assertAlmostEqual(r.safety, 2 / 3)               # (2+1-1)/(2+1)
        self.assertAlmostEqual(r.unsafe_repair_rate, 2 / 3)   # (1+1)/(2+1)
        self.assertAlmostEqual(r.referencia_sempre_repara, 3 / 6)

    def test_so_casos_legitimos_safety_indefinida(self):
        r = calcular([caso(L, True, True, True)])
        self.assertIsNone(r.safety)
        self.assertEqual(r.repair_rate, 1.0)

    def test_so_problemas_reais_repair_rate_indefinida(self):
        r = calcular([caso(P, False)])
        self.assertIsNone(r.repair_rate)
        self.assertEqual(r.safety, 1.0)

    def test_quem_nunca_repara_tem_unsafe_indefinida(self):
        r = calcular([caso(L, False), caso(P, False)])
        self.assertIsNone(r.unsafe_repair_rate)
        self.assertEqual(r.detection_accuracy, 0.5)

    def test_grupo_vazio_nao_divide_por_zero(self):
        r = calcular([])
        self.assertIsNone(r.detection_accuracy)
        self.assertIsNone(r.repair_rate)
        self.assertIsNone(r.safety)
        self.assertIsNone(r.unsafe_repair_rate)
        self.assertIsNone(r.descritivas["tempo_s"]["media"])

    def test_aviso_quando_m_maior_que_fp(self):
        self.assertEqual(len(avisos(Termos(fp=0, m=1))), 1)
        self.assertEqual(avisos(Termos(fp=1, m=1)), [])

    def test_descritivas(self):
        r = calcular([caso(L, False, tempo=t, tokens=k) for t, k in [(1, 10), (2, 30), (9, 20)]])
        self.assertEqual(r.descritivas["tempo_s"], {"media": 4.0, "mediana": 2, "minimo": 1, "maximo": 9})
        self.assertEqual(r.descritivas["tokens"]["mediana"], 20)

    def test_razao_com_denominador_zero(self):
        self.assertIsNone(razao(0, 0))
        self.assertEqual(razao(0, 4), 0.0)


class PorTratamento(unittest.TestCase):
    def test_separa_tratamentos_e_versoes(self):
        casos = [caso(L, True, True, True), caso(L, False, tratamento="agentes", versao="v1"),
                 caso(L, True, True, True, tratamento="agentes", versao="agentica")]
        res = calcular_por_tratamento(casos)
        self.assertEqual(list(res), [("agente1", "agentes", "agentica"),
                                     ("agente1", "agentes", "v1"),
                                     ("agente1", "baseline", None)])

    def test_por_categoria(self):
        casos = [caso(L, True, categoria="a"), caso(L, False, categoria="b")]
        res = calcular_por_tratamento(casos, por_categoria=True)
        self.assertEqual(sorted(k[-1] for k in res), ["a", "b"])
        self.assertEqual(res[("agente1", "baseline", None, "a")].termos.vp, 1)


if __name__ == "__main__":
    unittest.main()
