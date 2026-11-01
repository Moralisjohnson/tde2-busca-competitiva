"""Protocolo experimental do TDE2 (Lig 4 6x7).

Agente avaliado: AlfaBeta-d8 (alfa-beta, profundidade fixa 8, AVAL de janelas, ordenação centro-primeiro).
Adversários:
  - Aleatório (linha de base trivial)
  - O próprio agente com profundidade menor: AlfaBeta-d2, -d4, -d6 (mesmo código, mesma AVAL, mesmos pesos)

Variação das partidas (dois agentes determinísticos sempre jogariam a MESMA partida):
  - vs AlfaBeta-dX: as 2 primeiras jogadas são forçadas e percorrem as 7x7 = 49 aberturas possíveis,
    cada uma jogada 2 vezes, alternando quem começa: 98 partidas por confronto.
  - vs Aleatório: 100 partidas, semente do adversário = número da partida (0..99);
    nas partidas pares o agente avaliado começa (X), nas ímpares começa o adversário.

Unidade de custo: nós visitados por lance (ver busca.py). O tempo é registrado só como informação.
Experimento extra: ordenação de jogadas, mesmas 300 posições, AlfaBeta-d8 com e sem ordenação.

Uso: python3 experimento.py   (gera resultados.json e resultados.md)
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import time
from multiprocessing import Pool

from busca import AgenteAleatorio, AgenteAlfaBeta, Avaliacao, Contador, alfabeta, decidir, ordem_centro
from lig4 import MAX, MIN, Lig4

JOGO = Lig4(6, 7, 4)
PROF_PRINCIPAL = 8
PROFS_ADVERSARIOS = (2, 4, 6)
N_ALEATORIO = 100
N_ORDENACAO = 300


def criar(spec):
    tipo, param = spec
    if tipo == "aleatorio":
        return AgenteAleatorio(param)
    return AgenteAlfaBeta(JOGO, param)


def partida(args):
    """Joga uma partida. Retorna o resultado do ponto de vista do agente avaliado."""
    id_, spec_avaliado, spec_adv, avaliado_comeca, abertura = args
    avaliado, adv = criar(spec_avaliado), criar(spec_adv)
    lado_avaliado = MAX if avaliado_comeca else MIN
    s = JOGO.inicial()
    nos = {"avaliado": [], "adversario": []}
    estados_avaliado = []
    lances = list(abertura)  # sequência completa de colunas jogadas (para reprodução e figuras)
    for a in abertura:  # jogadas forçadas de abertura (não contam custo)
        s = JOGO.resultado(s, a)
    t0 = time.perf_counter()
    while not JOGO.terminal(s):
        if JOGO.jogador(s) == lado_avaliado:
            estados_avaliado.append(tuple(s[:2]) + (s.alturas, s.vez))
            a, n = avaliado.jogar(JOGO, s)
            nos["avaliado"].append(n)
        else:
            a, n = adv.jogar(JOGO, s)
            nos["adversario"].append(n)
        lances.append(a)
        s = JOGO.resultado(s, a)
    u = JOGO.utilidade(s)
    vencedor = None if u == 0 else (MAX if u > 0 else MIN)
    res = "E" if vencedor is None else ("V" if vencedor == lado_avaliado else "D")
    return {
        "id": id_, "avaliado_comeca": avaliado_comeca, "abertura": list(abertura),
        "resultado": res, "jogadas": sum(s.alturas), "nos": nos, "lances": lances,
        "segundos": time.perf_counter() - t0, "estados_avaliado": estados_avaliado,
    }


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def resumo(xs):
    xs = sorted(xs)
    if not xs:
        return {}
    p = lambda q: xs[min(len(xs) - 1, int(q * len(xs)))]
    return {"n": len(xs), "media": st.mean(xs), "desvio": st.pstdev(xs), "min": xs[0],
            "mediana": st.median(xs), "p95": p(0.95), "max": xs[-1]}


def nos_ordenacao(estado_tupla):
    from lig4 import Estado
    s = Estado(estado_tupla[0], estado_tupla[1], tuple(estado_tupla[2]), estado_tupla[3])
    aval = Avaliacao(JOGO)
    out = {}
    for nome, ordem in (("com", ordem_centro(JOGO)), ("sem", None)):
        c = Contador()
        _, v = decidir(JOGO, s, alfabeta, PROF_PRINCIPAL, aval, c, ordem)
        out[nome] = (c.nos, v)
    return out


def main():
    principal = ("alfabeta", PROF_PRINCIPAL)
    tarefas = {}
    tarefas["Aleatório"] = [(i, principal, ("aleatorio", i), i % 2 == 0, ()) for i in range(N_ALEATORIO)]
    aberturas = [(a, b) for a in range(JOGO.colunas) for b in range(JOGO.colunas)]
    for d in PROFS_ADVERSARIOS:
        lst, i = [], 0
        for ab in aberturas:
            for comeca in (True, False):
                lst.append((i, principal, ("alfabeta", d), comeca, ab))
                i += 1
        tarefas[f"AlfaBeta-d{d}"] = lst

    t0 = time.time()
    resultados = {}
    with Pool() as pool:
        for nome, lst in tarefas.items():
            resultados[nome] = pool.map(partida, lst, chunksize=1)
            print(f"{nome}: {len(lst)} partidas ({time.time() - t0:.0f}s)", flush=True)

        # experimento de ordenação: posições em que o agente avaliado jogou, sorteadas com semente fixa
        todos = [e for nome in resultados for p in resultados[nome] for e in p["estados_avaliado"]]
        amostra = random.Random(42).sample(todos, N_ORDENACAO)
        ordem_res = pool.map(nos_ordenacao, amostra, chunksize=4)
        print(f"Ordenação: {N_ORDENACAO} posições ({time.time() - t0:.0f}s)", flush=True)

    # ---------- agregação ----------
    agregado = {}
    for nome, ps in resultados.items():
        v = sum(p["resultado"] == "V" for p in ps)
        e = sum(p["resultado"] == "E" for p in ps)
        d = sum(p["resultado"] == "D" for p in ps)
        n = len(ps)
        lances = [x for p in ps for x in p["nos"]["avaliado"]]
        lances_adv = [x for p in ps for x in p["nos"]["adversario"]]
        por_partida = [sum(p["nos"]["avaliado"]) for p in ps]
        por_lado = {}
        for lado, comeca in (("começando (X)", True), ("em segundo (O)", False)):
            sub = [p for p in ps if p["avaliado_comeca"] == comeca]
            por_lado[lado] = {r: sum(p["resultado"] == r for p in sub) for r in "VED"}
        agregado[nome] = {
            "partidas": n, "V": v, "E": e, "D": d,
            "taxa_vitoria": v / n, "ic95_vitoria": wilson(v, n),
            "pontos": (v + 0.5 * e) / n,
            "por_lado": por_lado,
            "nos_por_lance": resumo(lances),
            "nos_por_lance_adversario": resumo(lances_adv),
            "nos_por_partida": resumo(por_partida),
            "jogadas_por_partida": resumo([p["jogadas"] for p in ps]),
        }

    com = [r["com"][0] for r in ordem_res]
    sem = [r["sem"][0] for r in ordem_res]
    mesmos_valores = all(r["com"][1] == r["sem"][1] for r in ordem_res)
    razoes = [c / s for c, s in zip(com, sem)]
    agregado["_ordenacao"] = {
        "posicoes": N_ORDENACAO, "com": resumo(com), "sem": resumo(sem),
        "razao_com_sem": resumo(razoes), "mesmos_valores": mesmos_valores,
        "pior_caso_ordenacao_mais_cara": sum(c > s for c, s in zip(com, sem)),
        "por_posicao": [[c, s] for c, s in zip(com, sem)],  # nós (com, sem) em cada posição da amostra
    }

    # fator de ramificação efetivo observado: média de ações legais por estado visto nas partidas
    ramos, profundidades = [], []
    for ps in resultados.values():
        for p in ps:
            profundidades.append(p["jogadas"])
    from lig4 import Estado
    for ps in resultados.values():
        for p in ps:
            for e in p["estados_avaliado"]:
                ramos.append(len(JOGO.acoes(Estado(e[0], e[1], tuple(e[2]), e[3]))))
    agregado["_b_m"] = {"b_medio": st.mean(ramos), "m_medio": st.mean(profundidades),
                        "m_max": max(profundidades)}

    with open("resultados.json", "w") as f:
        json.dump({"agregado": agregado,
                   "partidas": {k: [{kk: vv for kk, vv in p.items() if kk != "estados_avaliado"} for p in v]
                                for k, v in resultados.items()}}, f, ensure_ascii=False, indent=1)
    escrever_md(agregado)
    print(open("resultados.md").read())


def escrever_md(ag):
    L = []
    L.append(f"# Resultados: AlfaBeta-d{PROF_PRINCIPAL} no Lig 4 6x7\n")
    L.append("Custo medido em **nós visitados** por lance do agente avaliado.\n")
    L.append("## Resultados das partidas\n")
    L.append("| Adversário | Partidas | V | E | D | Taxa de vitória (IC 95%) | Pontos (V=1, E=½) |")
    L.append("|---|---|---|---|---|---|---|")
    for nome, a in ag.items():
        if nome.startswith("_"):
            continue
        lo, hi = a["ic95_vitoria"]
        L.append(f"| {nome} | {a['partidas']} | {a['V']} | {a['E']} | {a['D']} | "
                 f"{a['taxa_vitoria']:.1%} ({lo:.1%} a {hi:.1%}) | {a['pontos']:.3f} |")
    L.append("\n### Resultado por lado (V/E/D)\n")
    L.append("| Adversário | Avaliado começando (X) | Avaliado em segundo (O) |")
    L.append("|---|---|---|")
    for nome, a in ag.items():
        if nome.startswith("_"):
            continue
        f = lambda d: f"{d['V']}/{d['E']}/{d['D']}"
        L.append(f"| {nome} | {f(a['por_lado']['começando (X)'])} | {f(a['por_lado']['em segundo (O)'])} |")
    L.append("\n## Custo: nós visitados por lance do agente avaliado\n")
    L.append("| Adversário | Lances | Média | Desvio | Mediana | p95 | Máx | Nós/lance do adversário (média) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for nome, a in ag.items():
        if nome.startswith("_"):
            continue
        r, ra = a["nos_por_lance"], a["nos_por_lance_adversario"]
        L.append(f"| {nome} | {r['n']} | {r['media']:,.0f} | {r['desvio']:,.0f} | {r['mediana']:,.0f} | "
                 f"{r['p95']:,} | {r['max']:,} | {ra['media']:,.0f} |")
    L.append("\n## Duração das partidas (número de peças no fim)\n")
    L.append("| Adversário | Média | Mín | Mediana | Máx |")
    L.append("|---|---|---|---|---|")
    for nome, a in ag.items():
        if nome.startswith("_"):
            continue
        r = a["jogadas_por_partida"]
        L.append(f"| {nome} | {r['media']:.1f} | {r['min']} | {r['mediana']:.0f} | {r['max']} |")
    o = ag["_ordenacao"]
    L.append(f"\n## Ordenação de jogadas ({o['posicoes']} posições, AlfaBeta-d{PROF_PRINCIPAL})\n")
    L.append("| Variante | Média | Mediana | p95 | Máx |")
    L.append("|---|---|---|---|---|")
    for nome in ("com", "sem"):
        r = o[nome]
        L.append(f"| {nome} ordenação centro-primeiro | {r['media']:,.0f} | {r['mediana']:,.0f} | {r['p95']:,} | {r['max']:,} |")
    rz = o["razao_com_sem"]
    L.append(f"\nRazão nós(com)/nós(sem): média {rz['media']:.2f}, mediana {rz['mediana']:.2f}, máx {rz['max']:.2f}. "
             f"Em {o['pior_caso_ordenacao_mais_cara']} das {o['posicoes']} posições a ordenação custou MAIS nós. "
             f"Mesmo valor na raiz nas duas variantes: {'sim' if o['mesmos_valores'] else 'NÃO'}.")
    bm = ag["_b_m"]
    L.append(f"\n## b e m observados\n\nb médio (ações legais nos estados em que o agente jogou): {bm['b_medio']:.2f}; "
             f"m médio (peças no fim da partida): {bm['m_medio']:.1f}; m máximo: {bm['m_max']}.")
    with open("resultados.md", "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
