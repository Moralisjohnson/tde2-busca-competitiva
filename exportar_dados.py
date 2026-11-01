"""Exporta os dados do experimento para o relatório, os slides e a ficha em LaTeX.

Lê resultados.json e verificacao_saida.txt e escreve em relatorio/dados/:
  numeros.tex          macros \\dado{chave} com todos os números citados no texto (formato pt-BR)
  resultados.dat       V/E/D, taxa de vitória e IC 95% de Wilson por adversário
  porlado.dat          V/E/D do agente avaliado começando (X) e em segundo (O)
  caixas.dat           mín, q1, mediana, q3, p95, máx e média de nós por lance, por adversário
  hist_nos.dat         histograma (bins logarítmicos) de nós por lance, fração por adversário
  ordenacao.dat        nós com e sem ordenação nas 300 posições
  duracao.dat          histograma do número de peças no fim da partida, fração por adversário
  tabuleiros.tex       posições do exemplo de zugzwang (partida d2 perdida pelo d8 jogando com O)

Uso: python3 exportar_dados.py      (só biblioteca padrão; o exemplo de zugzwang roda a busca d8,
                                     alguns segundos, e fica em cache em relatorio/dados/zugzwang.json)
"""
from __future__ import annotations

import json
import math
import os
import re
import statistics as st

from busca import Avaliacao, Contador, alfabeta, decidir, ordem_centro
from lig4 import MAX, VITORIA, Lig4

RAIZ = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(RAIZ, "relatorio", "dados")
ADVERSARIOS = [("Aleatório", "ale", "Aleatório"), ("AlfaBeta-d2", "d2", "AlfaBeta-d2"),
               ("AlfaBeta-d4", "d4", "AlfaBeta-d4"), ("AlfaBeta-d6", "d6", "AlfaBeta-d6")]
JOGO = Lig4()


# ---------------- formatação pt-BR ----------------

def inteiro(n) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def dec(x, casas=1) -> str:
    s = f"{x:,.{casas}f}"
    return s.replace(",", "_").replace(".", "{,}").replace("_", ".")


def pct(x, casas=1) -> str:
    return dec(100 * x, casas) + "\\,\\%"


def cientifico(x) -> str:
    e = math.floor(math.log10(x))
    m = x / 10 ** e
    return f"{dec(m, 1)} \\times 10^{{{e}}}"


# ---------------- estatística ----------------

def p95(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(0.95 * len(xs)))]  # mesma definição de experimento.py


def quartis(xs):
    q = st.quantiles(xs, n=4, method="inclusive")
    return q[0], q[1], q[2]


def main():
    os.makedirs(SAIDA, exist_ok=True)
    with open(os.path.join(RAIZ, "resultados.json"), encoding="utf-8") as f:
        R = json.load(f)
    ag, partidas = R["agregado"], R["partidas"]
    D = {}  # chave -> texto LaTeX

    # ---------- resultados por adversário ----------
    linhas_res = ["i nome V E D n taxa lo hi pontos vfrac efrac dfrac"]
    linhas_lado = ["i nome XV XE XD OV OE OD"]
    linhas_cx = ["i nome min q1 med q3 p95 max media advmedia"]
    hist = {}
    for i, (nome, k, rot) in enumerate(ADVERSARIOS):
        a, ps = ag[nome], partidas[nome]
        lo, hi = a["ic95_vitoria"]
        n = a["partidas"]
        linhas_res.append(f"{i} {k} {a['V']} {a['E']} {a['D']} {n} {a['taxa_vitoria']:.4f} {lo:.4f} {hi:.4f} "
                          f"{a['pontos']:.4f} {a['V'] / n:.4f} {a['E'] / n:.4f} {a['D'] / n:.4f}")
        x, o = a["por_lado"]["começando (X)"], a["por_lado"]["em segundo (O)"]
        linhas_lado.append(f"{i} {k} {x['V']} {x['E']} {x['D']} {o['V']} {o['E']} {o['D']}")
        lances = [v for p in ps for v in p["nos"]["avaliado"]]
        q1, med, q3 = quartis(lances)
        r, ra = a["nos_por_lance"], a["nos_por_lance_adversario"]
        assert r["max"] == max(lances) and r["p95"] == p95(lances)
        linhas_cx.append(f"{i} {k} {min(lances)} {q1:.1f} {med:.1f} {q3:.1f} {p95(lances)} {max(lances)} "
                         f"{st.mean(lances):.1f} {ra['media']:.1f}")
        hist[k] = lances
        for campo in ("V", "E", "D", "partidas"):
            D[f"{k}-{campo}"] = str(a[campo])
        D[f"{k}-taxa"] = pct(a["taxa_vitoria"])
        D[f"{k}-lo"] = pct(lo)
        D[f"{k}-hi"] = pct(hi)
        D[f"{k}-pontos"] = dec(a["pontos"], 3)
        D[f"{k}-XV"], D[f"{k}-XE"], D[f"{k}-XD"] = str(x["V"]), str(x["E"]), str(x["D"])
        D[f"{k}-OV"], D[f"{k}-OE"], D[f"{k}-OD"] = str(o["V"]), str(o["E"]), str(o["D"])
        D[f"{k}-lances"] = inteiro(r["n"])
        D[f"{k}-media"] = inteiro(r["media"])
        D[f"{k}-desvio"] = inteiro(r["desvio"])
        D[f"{k}-min"] = inteiro(r["min"])
        D[f"{k}-q1"] = inteiro(q1)
        D[f"{k}-mediana"] = inteiro(r["mediana"])
        D[f"{k}-q3"] = inteiro(q3)
        D[f"{k}-p95"] = inteiro(r["p95"])
        D[f"{k}-max"] = inteiro(r["max"])
        D[f"{k}-advmedia"] = inteiro(ra["media"])
        jp = a["jogadas_por_partida"]
        D[f"{k}-durmedia"] = dec(jp["media"], 1)
        D[f"{k}-durmin"] = str(jp["min"])
        D[f"{k}-durmediana"] = inteiro(jp["mediana"])
        D[f"{k}-durmax"] = str(jp["max"])
        npart = a["nos_por_partida"]
        D[f"{k}-partidamedia"] = inteiro(npart["media"])
        D[f"{k}-partidamax"] = inteiro(npart["max"])

    escrever("resultados.dat", linhas_res)
    escrever("porlado.dat", linhas_lado)
    escrever("caixas.dat", linhas_cx)

    # histograma log de nós por lance: 4 bins por década, de 10^0 a 10^6.5
    bordas = [10 ** (e / 4) for e in range(0, 27)]
    L = ["x " + " ".join(k for _, k, _ in ADVERSARIOS)]
    for j in range(len(bordas) - 1):
        a_, b_ = bordas[j], bordas[j + 1]
        fr = [sum(a_ <= v < b_ for v in hist[k]) / len(hist[k]) for _, k, _ in ADVERSARIOS]
        L.append(f"{a_:.1f} " + " ".join(f"{v:.4f}" for v in fr))
    L.append(f"{bordas[-1]:.1f} " + " ".join("0" for _ in ADVERSARIOS))
    fora = sum(v < bordas[0] or v >= bordas[-1] for k in hist for v in hist[k])
    assert fora == 0, f"{fora} lances fora dos bins do histograma"
    escrever("hist_nos.dat", L)

    # duração: bins de 5 peças
    L = ["x " + " ".join(k for _, k, _ in ADVERSARIOS)]
    for x0 in range(5, 45, 5):
        fr = []
        for nome, k, _ in ADVERSARIOS:
            js = [p["jogadas"] for p in partidas[nome]]
            fr.append(sum(x0 <= v < x0 + 5 for v in js) / len(js))
        L.append(f"{x0} " + " ".join(f"{v:.4f}" for v in fr))
    L.append("45 " + " ".join("0" for _ in ADVERSARIOS))
    escrever("duracao.dat", L)

    # ---------- ordenação ----------
    o = ag["_ordenacao"]
    pares = o["por_posicao"]
    escrever("ordenacao.dat", ["com sem classe"] + [f"{c} {s} {'pior' if c > s else 'melhor'}" for c, s in pares])
    for var in ("com", "sem"):
        for campo in ("media", "mediana", "p95", "max"):
            D[f"ord-{var}-{campo}"] = inteiro(o[var][campo])
    D["ord-posicoes"] = str(o["posicoes"])
    D["ord-pior"] = str(o["pior_caso_ordenacao_mais_cara"])
    D["ord-razao-media"] = dec(o["razao_com_sem"]["media"], 2)
    D["ord-razao-mediana"] = dec(o["razao_com_sem"]["mediana"], 2)
    D["ord-razao-max"] = dec(o["razao_com_sem"]["max"], 2)
    D["ord-mesmos"] = "sim" if o["mesmos_valores"] else "não"
    D["ord-reducao-media"] = pct(1 - o["com"]["media"] / o["sem"]["media"], 0)

    # ---------- b, m e tamanho do espaço ----------
    bm = ag["_b_m"]
    D["b-medio"] = dec(bm["b_medio"], 2)
    D["b-medio-1"] = dec(bm["b_medio"], 1)
    D["m-medio"] = dec(bm["m_medio"], 1)
    D["m-max"] = str(bm["m_max"])
    D["bm-max"] = cientifico(7 ** 42)
    D["bm-medido"] = cientifico(bm["b_medio"] ** bm["m_medio"])
    D["total-partidas"] = str(sum(ag[n]["partidas"] for n, _, _ in ADVERSARIOS))
    D["d6-durmedia-tab"] = D["d6-durmedia"]

    # janelas da AVAL
    janelas = JOGO.janelas()
    h = JOGO.linhas + 1
    por_casa = {(c, r): sum(m >> (c * h + r) & 1 for m in janelas) for c in range(7) for r in range(6)}
    D["janelas"] = str(len(janelas))
    D["inclusoes"] = str(sum(por_casa.values()))
    D["inclusoes-centro"] = str(sum(por_casa[(3, r)] for r in range(6)))
    D["inclusoes-borda"] = str(sum(por_casa[(0, r)] for r in range(6)))
    D["janelas-max-casa"] = str(max(por_casa.values()))
    D["janelas-canto"] = str(por_casa[(0, 0)])
    escrever("janelas_casa.dat", ["c r n"] + [f"{c} {r} {por_casa[(c, r)]}" for c in range(7) for r in range(6)])
    # mapa em TikZ: cor proporcional ao número de janelas que passam pela casa
    nmax = max(por_casa.values())
    L = ["% Gerado por exportar_dados.py. Janelas de 4 casas por casa do tabuleiro (c, r), r = 0 embaixo."]
    L.append("\\newcommand{\\mapaJanelas}[1][]{\\begin{tikzpicture}[x=6mm,y=6mm,#1]")
    for (c, r), n in sorted(por_casa.items()):
        L.append(f"\\fill[corV!{round(85 * n / nmax)}!white] ({c},{r}) rectangle ++(1,1);"
                 f"\\node[font=\\scriptsize] at ({c + 0.5},{r + 0.5}) {{{n}}};")
    L.append("\\draw[step=1,gray!60] (0,0) grid (7,6);")
    L.append("\\foreach \\k in {0,...,6} \\node[font=\\tiny,gray] at (\\k+0.5,-0.4) {\\k};")
    L.append("\\end{tikzpicture}}")
    escrever("mapa_janelas.tex", L)

    # ---------- verificação ----------
    verificacao(D)

    # ---------- exemplo de zugzwang ----------
    zugzwang(D, partidas)

    with open(os.path.join(SAIDA, "numeros.tex"), "w", encoding="utf-8") as f:
        f.write("% Gerado por exportar_dados.py a partir de resultados.json e verificacao_saida.txt. Não editar.\n")
        for k, v in sorted(D.items()):
            f.write(f"\\expandafter\\def\\csname dado@{k}\\endcsname{{{v}}}\n")
    print(f"{len(D)} números em relatorio/dados/numeros.tex")


def verificacao(D):
    caminho = os.path.join(RAIZ, "verificacao_saida.txt")
    txt = open(caminho, encoding="utf-8").read() if os.path.exists(caminho) else ""
    num = lambda s: int(s.replace(",", "").replace(".", ""))
    m = re.findall(r"^\s*(Minimax|Alfa-beta \(sem ordenação\)|Alfa-beta \(centro primeiro\))\s+valor=\s*(-?\d+)\s+nós=\s*([\d,.]+)",
                   txt, re.M)
    rot = {"Minimax": "t1-mm", "Alfa-beta (sem ordenação)": "t1-ab-sem", "Alfa-beta (centro primeiro)": "t1-ab"}
    for nome, v, n in m:
        D[rot[nome] + "-valor"] = v
        D[rot[nome] + "-nos"] = inteiro(num(n))
    blocos = re.split(r"^Teste (\d+):", txt, flags=re.M)
    for i in range(1, len(blocos), 2):
        t, corpo = blocos[i], blocos[i + 1]
        mm = re.search(r"minimax=([\d,.]+)\s+alfa-beta=([\d,.]+)\s+\(([\d.]+)%\)", corpo)
        if mm:
            D[f"t{t}-mm"] = inteiro(num(mm.group(1)))
            D[f"t{t}-ab"] = inteiro(num(mm.group(2)))
            D[f"t{t}-pct"] = dec(float(mm.group(3)), 1) + "\\,\\%"
        mc = re.search(r"(\d+)\s+comparações", corpo)
        if mc:
            D[f"t{t}-comparacoes"] = mc.group(1)
    D["teste5"] = "1" if "t5-comparacoes" in D else "0"
    D["verificacao-status"] = ("APROVADO" if "APROVADO" in txt else "REPROVADO" if "REPROVADO" in txt
                               else "não executada")


def tabuleiro(s, jogo=JOGO) -> str:
    h = jogo.linhas + 1
    linhas = []
    for r in reversed(range(jogo.linhas)):
        ln = ""
        for c in range(jogo.colunas):
            bit = 1 << (c * h + r)
            ln += "X" if s.x & bit else "O" if s.o & bit else "."
        linhas.append(ln)
    return "/".join(linhas)


def vencedoras(s, jogo=JOGO) -> str:
    h = jogo.linhas + 1
    casas = set()
    for b in (s.x, s.o):
        for m in jogo.janelas():
            if b & m == m:
                for c in range(jogo.colunas):
                    for r in range(jogo.linhas):
                        if m >> (c * h + r) & 1:
                            casas.add((c, r))
    return ",".join(f"{c}/{r}" for c, r in sorted(casas))


def zugzwang(D, partidas):
    """Escolhe a primeira partida contra o d2 que o d8 perdeu jogando com O e registra, a cada lance do d8,
    a AVAL da posição e o valor da busca d8 (mesma chamada de busca.decidir usada no experimento)."""
    cache = os.path.join(SAIDA, "zugzwang.json")
    perdidas = [p for p in partidas["AlfaBeta-d2"] if p["resultado"] == "D" and not p["avaliado_comeca"]]
    D["d2-perdidas-O"] = str(len(perdidas))
    D["d2-perdidas-O-min"] = str(min(p["jogadas"] for p in perdidas))
    D["d2-perdidas-O-max"] = str(max(p["jogadas"] for p in perdidas))
    p = perdidas[0]
    dados = None
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            dados = json.load(f)
        if dados.get("lances") != p["lances"]:
            dados = None
    if dados is None:
        aval, ordem = Avaliacao(JOGO), ordem_centro(JOGO)
        s, traco = JOGO.inicial(), []
        for i, a in enumerate(p["lances"]):
            if i >= 2 and s.vez != MAX:  # lance do d8 (O)
                c = Contador()
                aa, v = decidir(JOGO, s, alfabeta, 8, aval, c, ordem)
                assert aa == a, "a reprodução divergiu da partida registrada"
                traco.append({"pecas": sum(s.alturas), "aval": aval(s), "valor": v, "nos": c.nos, "coluna": a})
            s = JOGO.resultado(s, a)
        dados = {"id": p["id"], "lances": p["lances"], "traco": traco}
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=1)
    traco = dados["traco"]
    # último lance em que a busca ainda não via a derrota e o primeiro em que já via
    perdido = next(t for t in traco if t["valor"] >= VITORIA - 42)
    antes = [t for t in traco if t["pecas"] < perdido["pecas"]][-1]
    D["zz-id"] = str(dados["id"])
    D["zz-abertura"] = f"{p['abertura'][0]}, {p['abertura'][1]}"
    D["zz-jogadas"] = str(p["jogadas"])
    D["zz-antes-pecas"] = str(antes["pecas"])
    D["zz-antes-valor"] = f"{antes['valor']:+d}".replace("-", "$-$")
    D["zz-antes-aval"] = f"{antes['aval']:+d}".replace("-", "$-$")
    D["zz-perdido-pecas"] = str(perdido["pecas"])
    D["zz-perdido-valor"] = f"+{perdido['valor']}"
    D["zz-perdido-final"] = str(VITORIA - perdido["valor"])
    D["zz-lances-d8"] = str(len(traco))
    D["zz-favoravel-O"] = str(sum(t["valor"] < 0 for t in traco))
    escrever("zugzwang.dat", ["pecas aval valor nos"] +
             [f"{t['pecas']} {t['aval']} {max(-30, min(30, t['valor']))} {t['nos']}" for t in traco])

    s, estados = JOGO.inicial(), {0: JOGO.inicial()}
    for i, a in enumerate(p["lances"], 1):
        s = JOGO.resultado(s, a)
        estados[i] = s
    L = ["% Gerado por exportar_dados.py. Tabuleiros: linhas de cima para baixo separadas por /."]
    for nome, n in (("ZzAntes", antes["pecas"]), ("ZzPerdido", perdido["pecas"]), ("ZzFinal", p["jogadas"])):
        L.append(f"\\def\\tab{nome}{{{tabuleiro(estados[n])}}}")
    L.append(f"\\def\\tabZzFinalVence{{{vencedoras(estados[p['jogadas']])}}}")
    # coluna jogada pelo d8 em cada um dos dois lances destacados (0-based)
    L.append(f"\\def\\colZzAntes{{{antes['coluna']}}}")
    L.append(f"\\def\\colZzPerdido{{{perdido['coluna']}}}")
    escrever("tabuleiros.tex", L)


def escrever(nome, linhas):
    with open(os.path.join(SAIDA, nome), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


if __name__ == "__main__":
    main()
