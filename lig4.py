"""Lig 4 (Connect Four) generalizado: tabuleiro LINHAS x COLUNAS, vence quem alinhar K.

Representação em bitboard: cada coluna ocupa (LINHAS + 1) bits; o bit extra no topo
é uma sentinela que impede que um alinhamento "vaze" de uma coluna para a próxima.

Estado s = (x, o, alturas, vez)
  x, o     inteiros com os bits ocupados por X (MAX) e por O (MIN)
  alturas  tupla com quantas peças há em cada coluna
  vez      0 se é a vez de X (MAX), 1 se é a vez de O (MIN)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

MAX, MIN = 0, 1
VITORIA = 1000  # base de |UTILIDADE| com vencedor; |AVAL| fica sempre abaixo de qualquer vitória


class Estado(NamedTuple):
    x: int
    o: int
    alturas: tuple
    vez: int


@dataclass(frozen=True)
class Lig4:
    linhas: int = 6
    colunas: int = 7
    k: int = 4

    # ---------- os seis componentes da formalização ----------

    def inicial(self) -> Estado:
        """s0: tabuleiro vazio, X (MAX) começa."""
        return Estado(0, 0, (0,) * self.colunas, MAX)

    def jogador(self, s: Estado) -> int:
        return s.vez

    def acoes(self, s: Estado) -> list[int]:
        """Colunas que ainda não estão cheias (vazio se o estado é terminal)."""
        if self.vencedor(s) is not None:
            return []
        return [c for c in range(self.colunas) if s.alturas[c] < self.linhas]

    def resultado(self, s: Estado, c: int) -> Estado:
        """Solta uma peça de quem tem a vez na coluna c; a peça cai até a posição livre mais baixa."""
        if s.alturas[c] >= self.linhas:
            raise ValueError(f"coluna {c} cheia")
        bit = 1 << (c * (self.linhas + 1) + s.alturas[c])
        alturas = s.alturas[:c] + (s.alturas[c] + 1,) + s.alturas[c + 1:]
        if s.vez == MAX:
            return Estado(s.x | bit, s.o, alturas, MIN)
        return Estado(s.x, s.o | bit, alturas, MAX)

    def terminal(self, s: Estado) -> bool:
        """Alguém alinhou K peças, ou o tabuleiro está cheio (empate)."""
        return self.vencedor(s) is not None or self.cheio(s)

    def utilidade(self, s: Estado) -> int:
        """UTILIDADE(s, MAX): +(VITORIA - n) se X venceu, -(VITORIA - n) se O venceu, 0 se empate,
        onde n é o número de peças no tabuleiro. Um único número, do ponto de vista de MAX;
        o desconto por n faz vitórias mais rápidas (e derrotas mais lentas) valerem mais."""
        v = self.vencedor(s)
        if v is None:
            return 0
        n = sum(s.alturas)
        return VITORIA - n if v == MAX else -(VITORIA - n)

    # ---------- auxiliares ----------

    def cheio(self, s: Estado) -> bool:
        return all(h == self.linhas for h in s.alturas)

    def vencedor(self, s: Estado):
        # só quem acabou de jogar pode ter acabado de alinhar, mas checar os dois é barato
        if self._alinhou(s.x):
            return MAX
        if self._alinhou(s.o):
            return MIN
        return None

    def _alinhou(self, b: int) -> bool:
        h = self.linhas + 1
        for d in (1, h, h - 1, h + 1):  # vertical, horizontal, diagonal \, diagonal /
            m = b
            for i in range(1, self.k):
                m &= b >> (i * d)
            if m:
                return True
        return False

    def janelas(self) -> list[int]:
        """Todas as máscaras de K casas consecutivas em linha (usadas pela avaliação)."""
        h = self.linhas + 1
        res = []
        for c in range(self.colunas):
            for r in range(self.linhas):
                for dc, dr in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    casas = [(c + i * dc, r + i * dr) for i in range(self.k)]
                    if all(0 <= cc < self.colunas and 0 <= rr < self.linhas for cc, rr in casas):
                        res.append(sum(1 << (cc * h + rr) for cc, rr in casas))
        return res

    def texto(self, s: Estado) -> str:
        h = self.linhas + 1
        linhas = []
        for r in reversed(range(self.linhas)):
            ln = ""
            for c in range(self.colunas):
                bit = 1 << (c * h + r)
                ln += "X" if s.x & bit else "O" if s.o & bit else "."
            linhas.append(" ".join(ln))
        linhas.append(" ".join(str(c) for c in range(self.colunas)))
        return "\n".join(linhas)
