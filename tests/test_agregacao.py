import unittest

from avaliacao.agregacao import agregar, maioria, reparo_correto
from tests.test_validacao import registro

NULOS = dict(decisao="nao_reparar", passou=False, compilou=None,
             equivalente_oraculo=None, assercoes_enfraquecidas=None,
             cenario_alterado=None)


class ReparoCorreto(unittest.TestCase):
    def test_reparo_completo_e_correto(self):
        self.assertTrue(reparo_correto(registro()))

    def test_cada_condicao_quebra_o_reparo(self):
        for campo, valor in [("decisao", "nao_reparar"), ("compilou", False),
                             ("passou", False), ("equivalente_oraculo", False),
                             ("equivalente_oraculo", None),
                             ("assercoes_enfraquecidas", True),
                             ("cenario_alterado", True)]:
            with self.subTest(campo=campo, valor=valor):
                self.assertFalse(reparo_correto(registro(**{campo: valor})))


class Maioria(unittest.TestCase):
    def test_tres_repeticoes(self):
        self.assertTrue(maioria([True, True, False]))
        self.assertFalse(maioria([True, False, False]))

    def test_uma_repeticao(self):
        self.assertTrue(maioria([True]))
        self.assertFalse(maioria([False]))

    def test_vazio_ou_par_falha_alto(self):
        for valores in ([], [True, False]):
            with self.subTest(valores=valores):
                with self.assertRaises(ValueError):
                    maioria(valores)


class Agregar(unittest.TestCase):
    def test_maioria_de_cada_resultado_e_independente(self):
        rs = [registro(repeticao=1),
              registro(repeticao=2, passou=False),            # decisão e correto divergem de passou
              registro(repeticao=3, **NULOS)]
        (caso,), excluidos = agregar(rs)
        self.assertEqual(excluidos, [])
        self.assertTrue(caso.reparou)          # 2 de 3 reparam
        self.assertFalse(caso.passou)          # 1 de 3 passa
        self.assertFalse(caso.reparo_correto)  # 1 de 3 é correto

    def test_infraestrutura_sai_antes_da_maioria_e_das_medias(self):
        rs = [registro(repeticao=1, tempo_s=1.0),
              registro(repeticao=2, erro="erro_llm", tempo_s=99.0, **NULOS),
              registro(repeticao=3, tempo_s=3.0),
              registro(repeticao=4, tempo_s=5.0)]
        (caso,), _ = agregar(rs)
        self.assertEqual(caso.repeticoes, 3)
        self.assertAlmostEqual(caso.tempo_s, 3.0)

    def test_falha_do_tratamento_conta(self):
        rs = [registro(repeticao=i, erro="max_tokens", **NULOS) for i in (1, 2, 3)]
        (caso,), _ = agregar(rs)
        self.assertFalse(caso.reparou)
        self.assertFalse(caso.passou)

    def test_caso_sem_execucao_valida_e_excluido_e_listado(self):
        rs = [registro(erro="erro_execucao", **NULOS), registro(id_caso="A1-002")]
        casos, excluidos = agregar(rs)
        self.assertEqual([c.id_caso for c in casos], ["A1-002"])
        self.assertEqual(excluidos, [("agente1", "baseline", None, "A1-001")])

    def test_tratamentos_e_versoes_ficam_separados(self):
        rs = [registro(),
              registro(tratamento="agentes", versao_agente="v1"),
              registro(tratamento="agentes", versao_agente="agentica")]
        casos, _ = agregar(rs)
        self.assertEqual(len(casos), 3)

    def test_zero_registros(self):
        self.assertEqual(agregar([]), ([], []))

    def test_medias_de_tokens_e_custo(self):
        rs = [registro(repeticao=i, tokens=t, custo_usd=c)
              for i, (t, c) in enumerate([(100, 0.01), (200, 0.02), (300, 0.03)], 1)]
        (caso,), _ = agregar(rs)
        self.assertEqual(caso.tokens, 200)
        self.assertAlmostEqual(caso.custo_usd, 0.02)


if __name__ == "__main__":
    unittest.main()
