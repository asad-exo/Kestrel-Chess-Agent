"""Tactics and speed check: the agent must find known mates/wins, then report
search depth and speed on a few middlegame and endgame positions.

Usage: python tests/test_search.py [agent.py]
"""
import time

import _common
import chess
from chess_tournament_api import Observation

K = _common.load_agent(_common.agent_path_from_argv())

# (fen, acceptable moves or None for "any legal move", description)
PUZZLES = [
    ("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", {"d1d8"}, "back-rank mate in 1"),
    ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", {"h5f7"}, "scholar's mate"),
    ("2r3k1/p4p2/3Rp2p/1p2P1pK/8/1P4P1/P3Q2P/1q6 b - - 0 1", {"b1g6"}, "mate in 2 (Qg6+)"),
    ("r1b1kb1r/pppp1ppp/5q2/4n3/3KP3/2N3PN/PPP4P/R1BQ1B1R b kq - 0 1", {"f8c5"}, "mate in 2 (Bc5+)"),
    ("8/8/8/8/8/2k5/2q5/K7 b - - 0 1", None, "don't stalemate"),
    ("4k3/8/8/8/8/8/8/R3K3 w Q - 0 1", None, "KR vs K makes a move"),
    ("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 3", {"f3f7"}, "mate in 1 (Qxf7)"),
    ("r2qkb1r/pp2nppp/3p4/2pNN1B1/2BnP3/3P4/PPP2PPP/R2bK2R w KQkq - 1 1", {"d5f6"}, "Nf6+ mating attack"),
    ("6k1/pp4p1/2p5/2bp4/8/P5Pb/1P3rrP/2BRRN1K b - - 0 1", {"g2g1"}, "mate (Rg1+)"),
]

SPEED = [
    chess.STARTING_FEN,
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "r2q1rk1/pp2bppp/2n1bn2/3p4/3P4/2NBBN2/PP3PPP/R2Q1RK1 w - - 0 11",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "8/5pk1/6p1/3R4/1r6/6P1/5PK1/8 w - - 0 40",
]


def obs_for(fen, remaining=30.0):
    b = chess.Board(fen)
    return Observation(fen=fen, move_history=(), my_remaining_time=remaining, opponent_remaining_time=remaining,
                       increment=0.3, color="white" if b.turn else "black", opponent_id="opp",
                       match_game_index=1, seed=1)


def main():
    agent = K.KestrelAgent()
    agent.initialize(color="white", opponent_id="opp", time_control=(30.0, 0.3), seed=1)
    fails = 0
    for fen, want, desc in PUZZLES:
        b = chess.Board(fen)
        agent._new_game()
        mv = agent.choose_move(obs_for(fen))
        ok = (chess.Move.from_uci(mv) in b.legal_moves) if want is None else mv in want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {desc:28s} played {mv}")
    print(f"puzzle failures: {fails}\n")
    for fen in SPEED:
        agent._new_game()
        t0 = time.perf_counter()
        mv = agent.choose_move(obs_for(fen))
        el = time.perf_counter() - t0
        score, depth, nodes, _ = agent.last_info
        print(f"{mv:6s} depth {depth:2d}  score {score:6d}  nodes {nodes:7d}  {el:.2f}s  {nodes / el:,.0f} nodes/s")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
