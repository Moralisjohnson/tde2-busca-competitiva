# Resultados: AlfaBeta-d8 no Lig 4 6x7

Custo medido em **nós visitados** por lance do agente avaliado.

## Resultados das partidas

| Adversário | Partidas | V | E | D | Taxa de vitória (IC 95%) | Pontos (V=1, E=½) |
|---|---|---|---|---|---|---|
| Aleatório | 100 | 100 | 0 | 0 | 100.0% (96.3% a 100.0%) | 1.000 |
| AlfaBeta-d2 | 98 | 77 | 5 | 16 | 78.6% (69.5% a 85.5%) | 0.811 |
| AlfaBeta-d4 | 98 | 61 | 14 | 23 | 62.2% (52.4% a 71.2%) | 0.694 |
| AlfaBeta-d6 | 98 | 38 | 26 | 34 | 38.8% (29.7% a 48.7%) | 0.520 |

### Resultado por lado (V/E/D)

| Adversário | Avaliado começando (X) | Avaliado em segundo (O) |
|---|---|---|
| Aleatório | 50/0/0 | 50/0/0 |
| AlfaBeta-d2 | 43/4/2 | 34/1/14 |
| AlfaBeta-d4 | 25/9/15 | 36/5/8 |
| AlfaBeta-d6 | 15/15/19 | 23/11/15 |

## Custo: nós visitados por lance do agente avaliado

| Adversário | Lances | Média | Desvio | Mediana | p95 | Máx | Nós/lance do adversário (média) |
|---|---|---|---|---|---|---|---|
| Aleatório | 571 | 19,727 | 25,383 | 13,149 | 53,476 | 414,620 | 0 |
| AlfaBeta-d2 | 1384 | 17,980 | 60,145 | 8,296 | 68,122 | 1,942,939 | 20 |
| AlfaBeta-d4 | 1664 | 18,132 | 57,694 | 6,296 | 60,550 | 1,554,522 | 196 |
| AlfaBeta-d6 | 1788 | 15,332 | 42,276 | 4,732 | 51,179 | 1,170,289 | 1,643 |

## Duração das partidas (número de peças no fim)

| Adversário | Média | Mín | Mediana | Máx |
|---|---|---|---|---|
| Aleatório | 10.9 | 7 | 9 | 30 |
| AlfaBeta-d2 | 29.9 | 7 | 34 | 42 |
| AlfaBeta-d4 | 35.8 | 19 | 38 | 42 |
| AlfaBeta-d6 | 38.5 | 15 | 39 | 42 |

## Ordenação de jogadas (300 posições, AlfaBeta-d8)

| Variante | Média | Mediana | p95 | Máx |
|---|---|---|---|---|
| com ordenação centro-primeiro | 15,031 | 6,754 | 53,969 | 172,133 |
| sem ordenação centro-primeiro | 71,884 | 13,623 | 272,818 | 540,669 |

Razão nós(com)/nós(sem): média 0.60, mediana 0.47, máx 3.41. Em 41 das 300 posições a ordenação custou MAIS nós. Mesmo valor na raiz nas duas variantes: sim.

## b e m observados

b médio (ações legais nos estados em que o agente jogou): 5.11; m médio (peças no fim da partida): 28.7; m máximo: 42.
