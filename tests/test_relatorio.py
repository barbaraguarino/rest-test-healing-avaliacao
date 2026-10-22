import contextlib
import io
import json
import os
import tempfile
import unittest

from avaliacao import __main__ as cli
from avaliacao import relatorio
from tests.test_validacao import arquivo, registro

NULOS = dict(decisao="nao_reparar", passou=False, compilou=None,
             equivalente_oraculo=None, assercoes_enfraquecidas=None,
             cenario_alterado=None)


def tres(**campos):
    return [registro(repeticao=i, **campos) for i in (1, 2, 3)]


class Montagem(unittest.TestCase):
    def test_estrutura_e_valores(self):
        regs = (tres(id_caso="A") + tres(id_caso="B", rotulo_oraculo="problema_real",
                                         passou=False, equivalente_oraculo=None))
        rel = relatorio.montar(regs)
        (b,) = rel["tratamentos"]
        self.assertEqual(b["termos"], {"vp": 1, "fn": 0, "fp": 1, "vn": 0, "r": 1, "m": 0, "ip": 0})
        self.assertEqual(b["metricas"]["detection_accuracy"],
                         {"valor": 0.5, "numerador": 1, "denominador": 2})
        self.assertEqual(rel["excluidos"], [])
        json.dumps(rel)  # tudo serializável

    def test_metrica_indefinida_vira_null_e_nd(self):
        rel = relatorio.montar(tres())  # só caso legítimo: Safety indefinida
        self.assertIsNone(rel["tratamentos"][0]["metricas"]["safety"]["valor"])
        linha = [l for l in relatorio.formatar_texto(rel).splitlines() if l.strip().startswith("Safety")]
        self.assertTrue(linha)
        self.assertTrue(all("n/d" in l for l in linha))

    def test_excluidos_aparecem_no_texto(self):
        regs = tres(id_caso="A") + [registro(id_caso="B", erro="erro_llm", **NULOS)]
        texto = relatorio.formatar_texto(relatorio.montar(regs))
        self.assertIn("sem nenhuma execução válida", texto)
        self.assertIn("B", texto.split("sem nenhuma execução válida")[1])

    def test_piloto_v1_vem_marcado_como_parcial(self):
        regs = tres(tratamento="agentes", versao_agente="v1")
        self.assertIn("resultado parcial", relatorio.formatar_texto(relatorio.montar(regs)))

    def test_sem_registros(self):
        rel = relatorio.montar([])
        self.assertEqual(rel["tratamentos"], [])
        self.assertIn("MÉTRICAS", relatorio.formatar_texto(rel))


class LinhaDeComando(unittest.TestCase):
    def rodar(self, conteudo, *extra):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "r.json")
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            saida, erro = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
                codigo = cli.main([caminho, *extra])
            return codigo, saida.getvalue(), erro.getvalue()

    def test_arquivo_valido(self):
        codigo, saida, _ = self.rodar(json.dumps(arquivo(*tres())))
        self.assertEqual(codigo, 0)
        self.assertIn("Detection Accuracy", saida)

    def test_arquivo_recusado_lista_problemas_e_sai_com_2(self):
        codigo, saida, erro = self.rodar(json.dumps(arquivo(registro(agente="x"), versao_api="v0")))
        self.assertEqual(codigo, 2)
        self.assertEqual(saida, "")
        self.assertIn("versao_api", erro)
        self.assertIn("agente", erro)

    def test_json_malformado(self):
        codigo, _, erro = self.rodar("{nao e json")
        self.assertEqual(codigo, 2)
        self.assertIn("Não foi possível ler", erro)

    def test_grava_json_opcional(self):
        with tempfile.TemporaryDirectory() as pasta:
            origem, destino = os.path.join(pasta, "r.json"), os.path.join(pasta, "m.json")
            with open(origem, "w", encoding="utf-8") as f:
                json.dump(arquivo(*tres()), f)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main([origem, "--json", destino]), 0)
            with open(destino, encoding="utf-8") as f:
                self.assertIn("tratamentos", json.load(f))


PILOTO = os.environ.get("PILOTO_AGENTE1") or os.path.join(
    os.path.dirname(__file__), "..", "..", "rest-test-healing-agente-contrato",
    "resultados", "piloto", "resultados-agente1.json")


@unittest.skipUnless(os.path.exists(PILOTO),
                     "defina PILOTO_AGENTE1 ou deixe o agente-contrato ao lado deste repositório")
class SanidadeComOPiloto(unittest.TestCase):
    """Compara o script com uma contagem direta nos registros brutos do piloto."""

    def test_baseline_do_piloto(self):
        with open(PILOTO, encoding="utf-8") as f:
            brutos = json.load(f)["execucoes"]
        por_caso = {}
        for r in brutos:
            por_caso.setdefault(r["id_caso"], []).append(r)
        # No piloto as repetições são idênticas; confirma, para a contagem direta valer.
        for repeticoes in por_caso.values():
            self.assertEqual(len({(r["decisao"], r["passou"], r["equivalente_oraculo"])
                                  for r in repeticoes}), 1)
        primeiros = [rs[0] for rs in por_caso.values()]
        legitimas = [r for r in primeiros if r["rotulo_oraculo"] == "legitima"]
        reais = [r for r in primeiros if r["rotulo_oraculo"] == "problema_real"]

        esperado = {
            "vp": sum(r["decisao"] == "reparar" for r in legitimas),
            "fn": sum(r["decisao"] == "nao_reparar" for r in legitimas),
            "fp": sum(r["decisao"] == "reparar" for r in reais),
            "vn": sum(r["decisao"] == "nao_reparar" for r in reais),
            "m": sum(r["passou"] for r in reais),
        }
        from avaliacao import validacao
        rel = relatorio.montar(validacao.carregar(PILOTO))
        (b,) = [x for x in rel["tratamentos"] if x["tratamento"] == "baseline"]
        for termo, valor in esperado.items():
            self.assertEqual(b["termos"][termo], valor, termo)
        self.assertEqual(b["n_casos"], len(primeiros))
        self.assertEqual(b["metricas"]["detection_accuracy"]["valor"],
                         (esperado["vp"] + esperado["vn"]) / len(primeiros))
        self.assertEqual(rel["excluidos"], [])


if __name__ == "__main__":
    unittest.main()
