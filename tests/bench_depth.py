"""Fixed-depth benchmark: time and nodes to finish depth D on a set of
positions. Two versions with the same search logic give the same node count,
so this isolates raw speed; different node counts show search changes.

Usage: python tests/bench_depth.py DEPTH agent1.py [agent2.py ...]
"""
import sys
import time

import _common
import chess

FENS = [
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "r2q1rk1/pp2bppp/2n1bn2/3p4/3P4/2NBBN2/PP3PPP/R2Q1RK1 w - - 0 11",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "8/5pk1/6p1/3R4/1r6/6P1/5PK1/8 w - - 0 40",
    "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R w KQ - 3 9",
    "2rq1rk1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PN2/PB2BPPP/2RQ1RK1 w - - 0 11",
    "r3r1k1/pp3pbp/1qp3p1/2B5/2BP2b1/Q1n2N2/P4PPP/3R1K1R b - - 0 17",
    "8/pp3k2/2p1rp2/4p1p1/2P1P1P1/1P3K2/P4P2/3R4 w - - 0 33",
]


def run(path, depth):
    K = _common.load_agent(path)
    total_t = total_n = 0
    for fen in FENS:
        e = K.Engine()
        cb = chess.Board(fen)
        phase = min(24, sum(K.PHASE_W[p.symbol().upper()] for p in cb.piece_map().values()))
        e.pst = K.build_pst(phase)
        e.eg_mode = phase <= 12
        e.contempt = 0
        e.game_ply = 20
        e.game_rep = set()
        e.path = set()
        e.deadline = time.perf_counter() + 1e9
        root = K.pos_from_chess(cb, e.pst)
        e.nodes = 0
        t0 = time.perf_counter()
        for d in range(1, depth + 1):
            e.search(root, d, -K.INF, K.INF, 0, 0, True)
        total_t += time.perf_counter() - t0
        total_n += e.nodes
    return total_t, total_n


if __name__ == "__main__":
    depth = int(sys.argv[1])
    for p in sys.argv[2:]:
        t, n = run(p, depth)
        print(f"{p}: depth {depth} in {t:.2f}s, {n} nodes, {n / t:,.0f} nodes/s")
