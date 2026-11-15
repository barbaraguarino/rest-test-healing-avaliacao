"""Teste de hipóteses (T20b): McNemar mid-p com Bonferroni dentro de cada agente.

    python -m avaliacao.mcnemar baseline.json agentica.json [--json saida.json]

Cada arquivo passa pela mesma validação das métricas; os registros são
juntados e pareados por caso (D81 antes, D126 depois). Se um caso faltar em
um dos tratamentos, o script para e lista os casos (nada é testado).
"""

import argparse
import dataclasses
import json
import sys

from avaliacao import agregacao, estatistica, validacao

AGENTES_NOMES = {"agente1": "Agente 1", "agente2": "Agente 2"}


def _num(p):
    return "n/d" if p is None else f"{p:.5f}".replace(".", ",")


def _lado(t):
    if t.n == 0:
        return "-"
    if t.b == t.c:
        return "empate"
    return "agêntica" if t.c > t.b else "baseline"


def _decisao(t):
    if t.rejeita is None:
        return "sem teste (só descritivo)"
    return "rejeita H0" if t.rejeita else "não rejeita H0"


def montar(registros):
    casos, excluidos = agregacao.agregar(registros)
    agentes = sorted({c.agente for c in casos})
    testes = []
    for agente in agentes:
        testes += estatistica.testar_agente(casos, agente)
    return {"alfa": estatistica.ALFA, "limiar": estatistica.LIMIAR,
            "hipoteses_por_agente": estatistica.HIPOTESES_POR_AGENTE,
            "testes": [{**dataclasses.asdict(t), "n": t.n} for t in testes]}


def formatar_texto(rel):
    from avaliacao.relatorio import _tabela  # só formatação; relatório já mesclado
    partes = [f"McNEMAR MID-P · Bonferroni dentro de cada agente: "
              f"α = {str(rel['alfa']).replace('.', ',')}, limiar por teste α/3 = "
              f"{_num(rel['limiar'])}"]
    for agente in sorted({t["agente"] for t in rel["testes"]}):
        linhas = []
        for t in (x for x in rel["testes"] if x["agente"] == agente):
            teste = estatistica.Teste(**{k: v for k, v in t.items() if k != "n"})
            linhas.append([t["nome"], t["n_pares"],
                           f"{t['acertos_baseline']}/{t['n_pares']}",
                           f"{t['acertos_agentica']}/{t['n_pares']}",
                           t["b"], t["c"], t["n"], _num(t["p"]), _num(t["limiar"]),
                           _lado(teste), _decisao(teste)])
        partes.append(f"=== {AGENTES_NOMES.get(agente, agente)} ===\n" + _tabela(
            ["Hipótese", "Pares", "Acertos baseline", "Acertos agêntica",
             "b", "c", "n", "p", "Limiar α/3", "Maior lado", "Decisão"], linhas))
    partes.append("b = só a baseline acertou; c = só a agêntica acertou; n = b + c.")
    return "\n\n".join(partes) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m avaliacao.mcnemar",
        description="McNemar mid-p (D126) com limiar de Bonferroni α/3 (D84).")
    parser.add_argument("resultados", nargs="+",
                        help="arquivos de resultados (baseline e versão agêntica)")
    parser.add_argument("--json", metavar="SAIDA", help="grava também o relatório em JSON")
    args = parser.parse_args(argv)

    registros = []
    for caminho in args.resultados:
        try:
            registros += validacao.carregar(caminho)
        except validacao.ArquivoInvalido as erro:
            print(f"Arquivo recusado: {caminho} ({len(erro.problemas)} problema(s)):",
                  file=sys.stderr)
            for problema in erro.problemas:
                print(f"  - {problema}", file=sys.stderr)
            return 2
        except (OSError, ValueError) as erro:
            print(f"Não foi possível ler {caminho}: {erro}", file=sys.stderr)
            return 2

    try:
        rel = montar(registros)
    except estatistica.CasosDesemparelhados as erro:
        print(f"PARE: {erro}", file=sys.stderr)
        return 3
    sys.stdout.write(formatar_texto(rel))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as saida:
            saida.write(json.dumps(rel, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
