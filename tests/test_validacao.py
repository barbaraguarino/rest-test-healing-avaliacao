import copy
import unittest

from avaliacao import validacao
from avaliacao.validacao import ArquivoInvalido, validar


def registro(**mudancas):
    """Baseline legítima reparada com sucesso; cada teste altera só o que importa."""
    base = {
        "id_caso": "A1-001", "agente": "agente1", "tratamento": "baseline",
        "versao_agente": None, "categoria": "renomeacao",
        "rotulo_oraculo": "legitima", "decisao": "reparar", "compilou": True,
        "passou": True, "equivalente_oraculo": True,
        "assercoes_enfraquecidas": False, "cenario_alterado": False,
        "repeticao": 1, "tempo_s": 0.5, "tokens": 0, "custo_usd": 0, "erro": None,
    }
    base.update(mudancas)
    return base


def arquivo(*registros, versao_api="linha-de-base-2"):
    return {"versao_api": versao_api, "execucoes": list(registros)}


class ValidacaoDoArquivo(unittest.TestCase):
    def problemas(self, dados):
        with self.assertRaises(ArquivoInvalido) as ctx:
            validar(dados)
        return "\n".join(ctx.exception.problemas)

    def test_arquivo_valido_devolve_os_registros(self):
        r = registro()
        self.assertEqual(validar(arquivo(r)), [r])

    def test_arquivo_vazio_e_valido(self):
        self.assertEqual(validar(arquivo()), [])

    def test_estrutura_sem_execucoes(self):
        self.assertIn("objeto com", self.problemas({"versao_api": "linha-de-base-2"}))

    def test_versao_api_diferente(self):
        self.assertIn("versao_api", self.problemas(arquivo(registro(), versao_api="linha-de-base-1")))

    def test_lista_todos_os_campos_ausentes(self):
        r = registro()
        del r["passou"], r["tokens"]
        texto = self.problemas(arquivo(r))
        self.assertIn("passou", texto)
        self.assertIn("tokens", texto)

    def test_chave_repetida(self):
        self.assertIn("chave repetida", self.problemas(arquivo(registro(), registro())))

    def test_mesma_repeticao_em_versoes_diferentes_nao_repete(self):
        a = registro(tratamento="agentes", versao_agente="v1")
        b = registro(tratamento="agentes", versao_agente="agentica")
        self.assertEqual(len(validar(arquivo(a, b))), 2)

    def test_valores_fora_do_dominio(self):
        for campo, valor in [("agente", "agente3"), ("tratamento", "x"),
                             ("rotulo_oraculo", "talvez"), ("decisao", "sim"),
                             ("erro", "falhou"), ("repeticao", 0),
                             ("repeticao", True), ("tokens", -1),
                             ("tempo_s", "rapido"), ("passou", None),
                             ("passou", 1), ("id_caso", "")]:
            with self.subTest(campo=campo, valor=valor):
                self.problemas(arquivo(registro(**{campo: valor})))

    def test_baseline_com_versao_agente(self):
        self.assertIn("baseline exige", self.problemas(arquivo(registro(versao_agente="v1"))))

    def test_agentes_sem_versao_agente(self):
        self.assertIn("agentes exige", self.problemas(arquivo(registro(tratamento="agentes"))))

    def test_agente_unico_so_aceita_agentica(self):
        r = registro(tratamento="agente_unico", versao_agente="v1")
        self.assertIn("D87", self.problemas(arquivo(r)))

    def test_nao_reparar_exige_campos_do_reparo_nulos(self):
        r = registro(decisao="nao_reparar", passou=False)  # compilou=True ficou
        self.assertIn("deve ser nulo", self.problemas(arquivo(r)))

    def test_nao_reparar_com_nulos_e_valido(self):
        r = registro(decisao="nao_reparar", passou=False, compilou=None,
                     equivalente_oraculo=None, assercoes_enfraquecidas=None,
                     cenario_alterado=None)
        self.assertEqual(validar(arquivo(r)), [r])

    def test_reparar_com_campo_nulo(self):
        self.assertIn("nulo com decisao=reparar", self.problemas(arquivo(registro(compilou=None))))

    def test_legitima_reparada_sem_equivalencia_fica_pendente(self):
        self.assertIn("pendente", self.problemas(arquivo(registro(equivalente_oraculo=None))))

    def test_regressao_reparada_aceita_equivalencia_nula(self):
        r = registro(rotulo_oraculo="problema_real", passou=False, equivalente_oraculo=None)
        self.assertEqual(validar(arquivo(r)), [r])

    def test_numero_par_de_repeticoes_validas(self):
        rs = [registro(repeticao=1), registro(repeticao=2)]
        self.assertIn("número par", self.problemas(arquivo(*rs)))

    def test_erro_de_infraestrutura_nao_conta_na_paridade(self):
        rs = [registro(repeticao=1), registro(repeticao=2),
              registro(repeticao=3, erro="erro_llm", decisao="nao_reparar",
                       passou=False, compilou=None, equivalente_oraculo=None,
                       assercoes_enfraquecidas=None, cenario_alterado=None)]
        # 2 válidas (par) + 1 de infraestrutura: recusa e manda reexecutar.
        self.assertIn("número par", self.problemas(arquivo(*rs)))

    def test_grupo_so_com_infraestrutura_nao_e_erro_de_paridade(self):
        r = registro(erro="erro_execucao", decisao="nao_reparar", passou=False,
                     compilou=None, equivalente_oraculo=None,
                     assercoes_enfraquecidas=None, cenario_alterado=None)
        self.assertEqual(validar(arquivo(r)), [r])

    def test_rotulo_diferente_entre_repeticoes_do_mesmo_caso(self):
        rs = [registro(repeticao=1), registro(repeticao=2),
              registro(repeticao=3, rotulo_oraculo="problema_real", passou=False)]
        self.assertIn("diferem de outra repetição", self.problemas(arquivo(*rs)))

    def test_acumula_problemas_de_varios_registros(self):
        a = registro(agente="x")
        b = registro(id_caso="A1-002", decisao="sim")
        self.assertEqual(len(self.problemas(arquivo(a, b)).splitlines()), 2)

    def test_nao_altera_a_entrada(self):
        dados = arquivo(registro())
        copia = copy.deepcopy(dados)
        validar(dados)
        self.assertEqual(dados, copia)


if __name__ == "__main__":
    unittest.main()
