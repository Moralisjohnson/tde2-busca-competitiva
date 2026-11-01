"""Versões instrumentadas da busca, usadas pelo visualizador.

Nada aqui altera o algoritmo: `alfabeta_rastreado` e `minimax_rastreado` são espelhos linha a linha de
`busca.alfabeta` e `busca.minimax` que, além do valor, registram a árvore explorada e a sequência de
eventos (entra, folha, atualiza, poda, sai). `decidir_detalhado` repete o laço de `busca.decidir` chamando
o próprio `busca.alfabeta`, e devolve também o valor de cada coluna da raiz.

O Teste 5 de verificacao.py confere que valor, jogada e número de nós são idênticos aos de busca.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from busca import Avaliacao, Contador, acoes_ordenadas, alfabeta
from lig4 import MAX, VITORIA, Estado, Lig4


# ---------------- contador que pode ser interrompido ----------------

class Cancelado(Exception):
    """Levantada dentro da busca quando a interface pede para parar."""


class ContadorCancelavel(Contador):
    """Contador de nós que outra thread pode ler (para o contador ao vivo) e interromper.

    `busca.alfabeta` faz `cont.nos += 1` a cada nó; aqui esse incremento passa por um setter que
    verifica a bandeira `cancelar`. O número contado é o mesmo do Contador comum."""

    def __init__(self):
        self.cancelar = False
        self._nos = 0
        super().__init__()

    @property
    def nos(self):
        return self._nos

    @nos.setter
    def nos(self, v):
        if self.cancelar:
            raise Cancelado
        self._nos = v


# ---------------- decisão na raiz com o valor de cada coluna ----------------

@dataclass
class ValorRaiz:
    acao: int
    valor: float
    alfa: float
    beta: float
    nos: int  # nós visitados na subárvore desta coluna

    @property
    def exato(self) -> bool:
        """Dentro da janela (alfa, beta) o valor devolvido é exato; fora dela é só um limite."""
        return self.alfa < self.valor < self.beta

    def limite(self) -> str:
        """'' se exato, '≤' se é limite superior, '≥' se é limite inferior (do ponto de vista de MAX)."""
        if self.exato:
            return ""
        return "≤" if self.valor <= self.alfa else "≥"


def decidir_detalhado(jogo: Lig4, s: Estado, prof, aval, cont, ordem):
    """Igual a busca.decidir com busca=alfabeta (mesma jogada, mesmo valor, mesmos nós),
    mas devolve também a lista de ValorRaiz, uma por coluna examinada."""
    cont.nos += 1
    maximiza = jogo.jogador(s) == MAX
    melhor_a, melhor_v = None, -math.inf if maximiza else math.inf
    p = None if prof is None else prof - 1
    raiz = []
    for a in acoes_ordenadas(jogo, s, ordem):
        filho = jogo.resultado(s, a)
        alfa, beta = (melhor_v, math.inf) if maximiza else (-math.inf, melhor_v)
        antes = cont.nos
        v = alfabeta(jogo, filho, p, aval, cont, ordem, alfa, beta)
        raiz.append(ValorRaiz(a, v, alfa, beta, cont.nos - antes))
        if (maximiza and v > melhor_v) or (not maximiza and v < melhor_v):
            melhor_a, melhor_v = a, v
    return melhor_a, melhor_v, raiz


# ---------------- árvore e eventos ----------------

@dataclass
class No:
    caminho: tuple            # colunas jogadas desde a raiz; identifica o nó
    estado: Estado
    jogador: int              # MAX ou MIN (quem joga em `estado`)
    prof: int                 # distância até a raiz
    alfa: float = -math.inf   # janela na entrada
    beta: float = math.inf
    valor: float | None = None
    tipo: str = "interno"     # 'interno', 'terminal' ou 'aval'
    filhos: list = field(default_factory=list)   # caminhos dos filhos visitados, na ordem
    podados: list = field(default_factory=list)  # colunas não examinadas por causa de uma poda


class Rastro:
    """Árvore explorada (dict caminho -> No) e lista ordenada de eventos.

    Eventos (tuplas):
      ('entra', caminho, alfa, beta)
      ('folha', caminho, valor, tipo)          tipo: 'terminal' ou 'aval'
      ('atualiza', caminho, v, alfa, beta)     depois que um filho devolveu seu valor
      ('poda', caminho, v, [colunas])          v >= beta (MAX) ou v <= alfa (MIN)
      ('sai', caminho, valor)
    """

    def __init__(self):
        self.nos: dict[tuple, No] = {}
        self.eventos: list[tuple] = []

    def novo(self, jogo, s, caminho, alfa, beta):
        n = No(caminho, s, jogo.jogador(s), len(caminho), alfa, beta)
        self.nos[caminho] = n
        if caminho:
            self.nos[caminho[:-1]].filhos.append(caminho)
        self.eventos.append(("entra", caminho, alfa, beta))
        return n


def alfabeta_rastreado(jogo: Lig4, s: Estado, prof=None, aval=None, cont: Contador | None = None,
                       ordem=None, alfa=-math.inf, beta=math.inf, rastro: Rastro | None = None,
                       caminho=()):
    """Espelho de busca.alfabeta (mesmo valor e mesma contagem de nós) que preenche `rastro`."""
    if cont is not None:
        cont.nos += 1
    no = rastro.novo(jogo, s, caminho, alfa, beta)
    if jogo.terminal(s):
        no.tipo, no.valor = "terminal", jogo.utilidade(s)
        rastro.eventos.append(("folha", caminho, no.valor, "terminal"))
        return no.valor
    if prof == 0:
        no.tipo, no.valor = "aval", aval(s)
        rastro.eventos.append(("folha", caminho, no.valor, "aval"))
        return no.valor
    p = None if prof is None else prof - 1
    acoes = acoes_ordenadas(jogo, s, ordem)
    if jogo.jogador(s) == MAX:
        v = -math.inf
        for i, a in enumerate(acoes):
            v = max(v, alfabeta_rastreado(jogo, jogo.resultado(s, a), p, aval, cont, ordem, alfa, beta,
                                          rastro, caminho + (a,)))
            if v >= beta:
                no.podados = acoes[i + 1:]
                rastro.eventos.append(("atualiza", caminho, v, alfa, beta))
                if no.podados:
                    rastro.eventos.append(("poda", caminho, v, list(no.podados)))
                no.valor = v
                rastro.eventos.append(("sai", caminho, v))
                return v
            alfa = max(alfa, v)
            rastro.eventos.append(("atualiza", caminho, v, alfa, beta))
        no.valor = v
        rastro.eventos.append(("sai", caminho, v))
        return v
    v = math.inf
    for i, a in enumerate(acoes):
        v = min(v, alfabeta_rastreado(jogo, jogo.resultado(s, a), p, aval, cont, ordem, alfa, beta,
                                      rastro, caminho + (a,)))
        if v <= alfa:
            no.podados = acoes[i + 1:]
            rastro.eventos.append(("atualiza", caminho, v, alfa, beta))
            if no.podados:
                rastro.eventos.append(("poda", caminho, v, list(no.podados)))
            no.valor = v
            rastro.eventos.append(("sai", caminho, v))
            return v
        beta = min(beta, v)
        rastro.eventos.append(("atualiza", caminho, v, alfa, beta))
    no.valor = v
    rastro.eventos.append(("sai", caminho, v))
    return v


def minimax_rastreado(jogo: Lig4, s: Estado, prof=None, aval=None, cont: Contador | None = None,
                      ordem=None, rastro: Rastro | None = None, caminho=()):
    """Espelho de busca.minimax que registra a árvore completa (usada como 'fundo' do desenho)."""
    if cont is not None:
        cont.nos += 1
    no = rastro.novo(jogo, s, caminho, -math.inf, math.inf)
    if jogo.terminal(s):
        no.tipo, no.valor = "terminal", jogo.utilidade(s)
        rastro.eventos.append(("folha", caminho, no.valor, "terminal"))
        return no.valor
    if prof == 0:
        no.tipo, no.valor = "aval", aval(s)
        rastro.eventos.append(("folha", caminho, no.valor, "aval"))
        return no.valor
    p = None if prof is None else prof - 1
    vals = [minimax_rastreado(jogo, jogo.resultado(s, a), p, aval, cont, ordem, rastro, caminho + (a,))
            for a in acoes_ordenadas(jogo, s, ordem)]
    no.valor = max(vals) if jogo.jogador(s) == MAX else min(vals)
    rastro.eventos.append(("sai", caminho, no.valor))
    return no.valor


def contar_minimax(jogo: Lig4, s: Estado, prof=None, limite=None) -> int:
    """Número de nós que Minimax visitaria (para checar o tamanho antes de desenhar).
    Para assim que passar de `limite` e devolve limite + 1."""
    h = [0]

    def rec(s, p):
        h[0] += 1
        if limite is not None and h[0] > limite:
            raise StopIteration
        if jogo.terminal(s) or p == 0:
            return
        for a in jogo.acoes(s):
            rec(jogo.resultado(s, a), None if p is None else p - 1)

    try:
        rec(s, prof)
    except StopIteration:
        return limite + 1
    return h[0]


# ---------------- auxiliares de exibição ----------------

def decodificar(v, pecas_agora: int | None = None) -> str:
    """Texto curto para um valor da busca, do ponto de vista de MAX (X)."""
    if v is None:
        return "?"
    if v in (math.inf, -math.inf):
        return "+∞" if v > 0 else "−∞"
    if abs(v) >= VITORIA - 42:
        n = VITORIA - abs(v)
        quem = "X" if v > 0 else "O"
        if pecas_agora is not None:
            return f"{quem} vence em {n - pecas_agora}"
        return f"{quem} vence (peça {n})"
    return f"{v:+d}" if isinstance(v, int) else f"{v:+.0f}"


def eh_vitoria(v) -> bool:
    return v is not None and abs(v) >= VITORIA - 42 and abs(v) != math.inf


def componentes_aval(aval: Avaliacao, s: Estado) -> dict:
    """Decompõe AVAL(s) nas características da função de avaliação (mesma regra de busca.Avaliacao)."""
    k = aval.jogo.k
    c = {"k1_x": 0, "k1_o": 0, "k2_x": 0, "k2_o": 0,
         "centro_x": (s.x & aval.centro).bit_count(), "centro_o": (s.o & aval.centro).bit_count()}
    for m in aval.janelas:
        nx, no = (s.x & m).bit_count(), (s.o & m).bit_count()
        if nx and no:
            continue
        if nx == k - 1:
            c["k1_x"] += 1
        elif nx == k - 2:
            c["k2_x"] += 1
        elif no == k - 1:
            c["k1_o"] += 1
        elif no == k - 2:
            c["k2_o"] += 1
    c["bruto"] = (aval.PESO_K1 * (c["k1_x"] - c["k1_o"]) + aval.PESO_K2 * (c["k2_x"] - c["k2_o"])
                  + aval.PESO_CENTRO * (c["centro_x"] - c["centro_o"]))
    c["total"] = aval(s)
    return c


def janelas_por_casa(jogo: Lig4) -> dict:
    """Quantas janelas de K casas passam por cada casa (c, r): justifica o peso do centro."""
    h = jogo.linhas + 1
    cont = {}
    for m in jogo.janelas():
        for c in range(jogo.colunas):
            for r in range(jogo.linhas):
                if m >> (c * h + r) & 1:
                    cont[(c, r)] = cont.get((c, r), 0) + 1
    return cont


def casas_vencedoras(jogo: Lig4, s: Estado) -> list[tuple[int, int]]:
    """Casas (c, r) de todos os alinhamentos de K completos no estado."""
    h = jogo.linhas + 1
    res = set()
    for b in (s.x, s.o):
        for m in jogo.janelas():
            if b & m == m:
                for c in range(jogo.colunas):
                    for r in range(jogo.linhas):
                        if m >> (c * h + r) & 1:
                            res.add((c, r))
    return sorted(res)


def peca(jogo: Lig4, s: Estado, c: int, r: int):
    """'X', 'O' ou None na casa (c, r); r = 0 é a linha de baixo."""
    bit = 1 << (c * (jogo.linhas + 1) + r)
    return "X" if s.x & bit else "O" if s.o & bit else None


def estado_de_lances(jogo: Lig4, lances) -> Estado:
    s = jogo.inicial()
    for a in lances:
        s = jogo.resultado(s, a)
    return s
