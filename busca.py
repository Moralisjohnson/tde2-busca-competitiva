"""Minimax, alfa-beta, função de avaliação e agentes para o Lig 4.

Unidade de custo: NÓS VISITADOS = número de chamadas à função recursiva de busca
(cada estado examinado conta 1, inclusive folhas e estados terminais).
"""
from __future__ import annotations

import math
import random

from lig4 import MAX, Estado, Lig4

LIMITE_AVAL = 900  # |AVAL(s)| <= 900 < 958 <= |UTILIDADE| de qualquer vitória em 6x7


class Contador:
    def __init__(self):
        self.nos = 0


# ---------------- avaliação e ordenação ----------------

class Avaliacao:
    """AVAL(s) = sum_janelas [ P(k-1)*(3 em linha abertas) + P(k-2)*(2 em linha abertas) ] (X - O)
               + P_CENTRO * (peças de X - peças de O na coluna central)

    Uma "janela" é um segmento de K casas em linha. Ela só conta se tiver peças de um único jogador:
    se já tem peças dos dois, ninguém mais pode vencer por ela.
    """

    PESO_K1 = 5   # K-1 peças + 1 vazia: ameaça direta, a uma jogada da vitória
    PESO_K2 = 2   # K-2 peças + 2 vazias: ameaça em construção
    PESO_CENTRO = 3  # coluna central participa do maior número de janelas

    def __init__(self, jogo: Lig4):
        self.jogo = jogo
        self.janelas = jogo.janelas()
        h = jogo.linhas + 1
        cc = jogo.colunas // 2
        self.centro = sum(1 << (cc * h + r) for r in range(jogo.linhas))

    def __call__(self, s: Estado) -> int:
        k = self.jogo.k
        x, o = s.x, s.o
        v = self.PESO_CENTRO * ((x & self.centro).bit_count() - (o & self.centro).bit_count())
        for m in self.janelas:
            nx = (x & m).bit_count()
            no = (o & m).bit_count()
            if nx and no:
                continue
            if nx == k - 1:
                v += self.PESO_K1
            elif nx == k - 2:
                v += self.PESO_K2
            elif no == k - 1:
                v -= self.PESO_K1
            elif no == k - 2:
                v -= self.PESO_K2
        return max(-LIMITE_AVAL, min(LIMITE_AVAL, v))


def ordem_centro(jogo: Lig4) -> list[int]:
    """Ordenação de jogadas: colunas do centro para as bordas (custo zero, tabela fixa)."""
    meio = (jogo.colunas - 1) / 2
    return sorted(range(jogo.colunas), key=lambda c: (abs(c - meio), c))


def acoes_ordenadas(jogo: Lig4, s: Estado, ordem):
    acoes = jogo.acoes(s)
    if ordem is None:
        return acoes
    disp = set(acoes)
    return [c for c in ordem if c in disp]


# ---------------- Minimax ----------------

def minimax(jogo: Lig4, s: Estado, prof=None, aval=None, cont: Contador | None = None, ordem=None):
    """Valor minimax de s. prof=None busca até os terminais (profundidade completa)."""
    if cont is not None:
        cont.nos += 1
    if jogo.terminal(s):
        return jogo.utilidade(s)
    if prof == 0:
        return aval(s)
    p = None if prof is None else prof - 1
    vals = (minimax(jogo, jogo.resultado(s, a), p, aval, cont, ordem) for a in acoes_ordenadas(jogo, s, ordem))
    return max(vals) if jogo.jogador(s) == MAX else min(vals)


# ---------------- Alfa-beta ----------------

def alfabeta(jogo: Lig4, s: Estado, prof=None, aval=None, cont: Contador | None = None,
             ordem=None, alfa=-math.inf, beta=math.inf):
    """Valor minimax de s com poda alfa-beta (fail-hard dentro de [alfa, beta])."""
    if cont is not None:
        cont.nos += 1
    if jogo.terminal(s):
        return jogo.utilidade(s)
    if prof == 0:
        return aval(s)
    p = None if prof is None else prof - 1
    if jogo.jogador(s) == MAX:
        v = -math.inf
        for a in acoes_ordenadas(jogo, s, ordem):
            v = max(v, alfabeta(jogo, jogo.resultado(s, a), p, aval, cont, ordem, alfa, beta))
            if v >= beta:
                return v
            alfa = max(alfa, v)
        return v
    v = math.inf
    for a in acoes_ordenadas(jogo, s, ordem):
        v = min(v, alfabeta(jogo, jogo.resultado(s, a), p, aval, cont, ordem, alfa, beta))
        if v <= alfa:
            return v
        beta = min(beta, v)
    return v


def decidir(jogo: Lig4, s: Estado, busca, prof, aval, cont, ordem):
    """Escolhe a ação de maior valor para quem tem a vez. Empates: a primeira na ordem de exame.
    A raiz conta como nó visitado, como em qualquer outro nível."""
    cont.nos += 1
    maximiza = jogo.jogador(s) == MAX
    melhor_a, melhor_v = None, -math.inf if maximiza else math.inf
    p = None if prof is None else prof - 1
    for a in acoes_ordenadas(jogo, s, ordem):
        filho = jogo.resultado(s, a)
        if busca is alfabeta:
            # a janela da raiz só melhora valores estritamente melhores que o atual
            alfa, beta = (melhor_v, math.inf) if maximiza else (-math.inf, melhor_v)
            v = alfabeta(jogo, filho, p, aval, cont, ordem, alfa, beta)
        else:
            v = minimax(jogo, filho, p, aval, cont, ordem)
        if (maximiza and v > melhor_v) or (not maximiza and v < melhor_v):
            melhor_a, melhor_v = a, v
    return melhor_a, melhor_v


# ---------------- Agentes ----------------

class AgenteAleatorio:
    def __init__(self, semente: int):
        self.rng = random.Random(semente)
        self.nome = "Aleatório"

    def jogar(self, jogo: Lig4, s: Estado):
        return self.rng.choice(jogo.acoes(s)), 0  # não visita nenhum nó de busca


class AgenteAlfaBeta:
    """Alfa-beta com profundidade fixa, avaliação heurística e ordenação centro-primeiro."""

    def __init__(self, jogo: Lig4, prof: int, ordenar: bool = True):
        self.prof = prof
        self.aval = Avaliacao(jogo)
        self.ordem = ordem_centro(jogo) if ordenar else None
        self.nome = f"AlfaBeta-d{prof}" + ("" if ordenar else "-sem-ordem")

    def jogar(self, jogo: Lig4, s: Estado):
        cont = Contador()
        a, _ = decidir(jogo, s, alfabeta, self.prof, self.aval, cont, self.ordem)
        return a, cont.nos
