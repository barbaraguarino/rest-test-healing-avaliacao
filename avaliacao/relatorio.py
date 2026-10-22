"""Montagem e formatação do relatório de métricas (texto e JSON)."""

import json

from avaliacao import agregacao, metricas, validacao

NOMES = (
    ("detection_accuracy", "Detection Accuracy"),
    ("repair_rate", "Repair Rate"),
    ("safety", "Safety"),
    ("unsafe_repair_rate", "Unsafe Repair Rate"),
)


def _bloco(chave, resultado):
    t = resultado.termos
    agente, tratamento, versao = chave[:3]
    bloco = {
        "agente": agente,
        "tratamento": tratamento,
        "versao_agente": versao,
        "n_casos": resultado.n_casos,
        "termos": {"vp": t.vp, "fn": t.fn, "fp": t.fp, "vn": t.vn,
                   "r": t.r, "m": t.m, "ip": t.ip},
        "metricas": {nome: {"valor": getattr(resultado, nome),
                            "numerador": resultado.fracoes[nome][0],
                            "denominador": resultado.fracoes[nome][1]}
                     for nome, _ in NOMES},
        "referencia_sempre_repara": resultado.referencia_sempre_repara,
        "descritivas": resultado.descritivas,
        "avisos": list(resultado.avisos),
    }
    if len(chave) == 4:
        bloco["categoria"] = chave[3]
    return bloco


def montar(registros):
    """Relatório estruturado (serializável em JSON) a partir de registros validados."""
    casos, excluidos = agregacao.agregar(registros)
    return {
        "versao_api": validacao.VERSAO_API_ACORDADA,
        "tratamentos": [_bloco(k, r) for k, r in
                        metricas.calcular_por_tratamento(casos).items()],
        "por_categoria": [_bloco(k, r) for k, r in
                          metricas.calcular_por_tratamento(casos, por_categoria=True).items()],
        "excluidos": [{"agente": a, "tratamento": t, "versao_agente": v, "id_caso": i}
                      for a, t, v, i in excluidos],
    }


def _num(valor):
    return "n/d" if valor is None else f"{valor:.4f}".replace(".", ",")


def _tabela(cabecalho, linhas):
    """Tabela de texto alinhada: primeira coluna à esquerda, as demais à direita."""
    todas = [cabecalho] + linhas
    larguras = [max(len(str(l[i])) for l in todas) for i in range(len(cabecalho))]

    def formatar(linha):
        celulas = [str(linha[0]).ljust(larguras[0])]
        celulas += [str(c).rjust(w) for c, w in zip(linha[1:], larguras[1:])]
        return "  " + "   ".join(celulas)

    separador = "  " + "---".join("-" * w for w in larguras)
    return "\n".join([formatar(cabecalho), separador] + [formatar(l) for l in linhas])


def _titulo(b):
    versao = b["versao_agente"] or "-"
    extra = f" · categoria {b['categoria']}" if "categoria" in b else ""
    return f"{b['agente']} · {b['tratamento']} · versão {versao}{extra}"


def _texto_bloco(b):
    t = b["termos"]
    partes = [f"=== {_titulo(b)} ==="]
    if b["versao_agente"] == "v1":
        partes.append("Piloto (v1): resultado parcial, fora do teste de hipóteses.")
    partes.append(f"Casos: {b['n_casos']}")
    partes.append("Matriz de confusão\n" + _tabela(
        ["Situação real", "Reparar", "Não reparar"],
        [["Legítima", f"VP = {t['vp']}", f"FN = {t['fn']}"],
         ["Problema real", f"FP = {t['fp']}", f"VN = {t['vn']}"]]))
    partes.append(f"Termos adicionais: R = {t['r']}   M = {t['m']}   Ip = {t['ip']}")
    linhas = [[rotulo, _num(b["metricas"][nome]["valor"]),
               f"{b['metricas'][nome]['numerador']}/{b['metricas'][nome]['denominador']}"]
              for nome, rotulo in NOMES]
    linhas.append(["Referência (sempre repara)", _num(b["referencia_sempre_repara"]), ""])
    partes.append("Métricas\n" + _tabela(["Métrica", "Valor", "Cálculo"], linhas))
    linhas = [[nome, _num(d["media"]), _num(d["mediana"]), _num(d["minimo"]), _num(d["maximo"])]
              for nome, d in b["descritivas"].items()]
    partes.append("Descritivas, por caso\n" + _tabela(
        ["", "Média", "Mediana", "Mínimo", "Máximo"], linhas))
    partes.extend(f"AVISO: {a}" for a in b["avisos"])
    return "\n\n".join(partes)


def formatar_texto(relatorio):
    partes = [f"MÉTRICAS · versao_api {relatorio['versao_api']}"]
    partes += [_texto_bloco(b) for b in relatorio["tratamentos"]]
    if relatorio["por_categoria"]:
        partes.append("POR CATEGORIA DE MUDANÇA (descritivo)")
        partes += [_texto_bloco(b) for b in relatorio["por_categoria"]]
    if relatorio["excluidos"]:
        linhas = [[e["agente"], e["tratamento"], e["versao_agente"] or "-", e["id_caso"]]
                  for e in relatorio["excluidos"]]
        partes.append("Casos sem nenhuma execução válida (fora das métricas)\n" + _tabela(
            ["Agente", "Tratamento", "Versão", "Caso"], linhas))
    return "\n\n".join(partes) + "\n"


def formatar_json(relatorio):
    return json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n"
