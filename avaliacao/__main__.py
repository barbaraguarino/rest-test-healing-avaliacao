"""Linha de comando: python -m avaliacao resultados.json [--json saida.json]"""

import argparse
import sys

from avaliacao import relatorio, validacao


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m avaliacao",
        description="Calcula as métricas do acordo de avaliação comum a partir de um arquivo de resultados.")
    parser.add_argument("resultados", help="arquivo resultados-agenteN.json")
    parser.add_argument("--json", metavar="SAIDA", help="grava também o relatório em JSON")
    args = parser.parse_args(argv)

    try:
        registros = validacao.carregar(args.resultados)
    except validacao.ArquivoInvalido as erro:
        print(f"Arquivo recusado ({len(erro.problemas)} problema(s)):", file=sys.stderr)
        for problema in erro.problemas:
            print(f"  - {problema}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as erro:  # arquivo ausente ou JSON malformado
        print(f"Não foi possível ler {args.resultados}: {erro}", file=sys.stderr)
        return 2

    dados = relatorio.montar(registros)
    sys.stdout.write(relatorio.formatar_texto(dados))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as saida:
            saida.write(relatorio.formatar_json(dados))
    return 0


if __name__ == "__main__":
    sys.exit(main())
