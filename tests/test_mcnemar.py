import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from avaliacao import mcnemar
from tests.test_validacao import arquivo, registro


def repetidas(**campos):
    return [registro(repeticao=i, **campos) for i in (1, 2, 3)]


class Ensaio(unittest.TestCase):
    def rodar(self, base, agentica, extra=()):
        with tempfile.TemporaryDirectory() as pasta:
            caminhos = []
            for nome, regs in (("b.json", base), ("a.json", agentica)):
                caminho = os.path.join(pasta, nome)
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(arquivo(*regs), f)
                caminhos.append(caminho)
            saida, erro = io.StringIO(), io.StringIO()
            with redirect_stdout(saida), redirect_stderr(erro):
                codigo = mcnemar.main(caminhos + list(extra))
            return codigo, saida.getvalue(), erro.getvalue()

    def test_seis_legitimos_so_a_agentica_repara_corretamente(self):
        base, ag = [], []
        for i in range(6):
            base += repetidas(id_caso=f"L{i}", equivalente_oraculo=False)
            ag += repetidas(id_caso=f"L{i}", tratamento="agentes", versao_agente="agentica")
        codigo, texto, _ = self.rodar(base, ag)
        self.assertEqual(codigo, 0)
        self.assertIn("rejeita H0", texto)
        self.assertIn("0,01562", texto)

    def test_caso_faltando_para_com_codigo_3(self):
        base = repetidas(id_caso="A") + repetidas(id_caso="B")
        ag = repetidas(id_caso="A", tratamento="agentes", versao_agente="agentica")
        codigo, texto, erro = self.rodar(base, ag)
        self.assertEqual(codigo, 3)
        self.assertEqual(texto, "")
        self.assertIn("['B']", erro)


if __name__ == "__main__":
    unittest.main()
