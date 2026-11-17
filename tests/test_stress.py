"""Stress test: a full self-play game at the official 30s + 0.3s clock inside
one process. Checks that no move is illegal, no clock runs out, and reports
the slowest move, final clocks, transposition-table sizes and peak memory
(peak memory is reported on macOS/Linux only).

Usage: python tests/test_stress.py [agent.py]
"""
import sys
import time

import _common
import chess
from chess_tournament_api import Observation

K = _common.load_agent(_common.agent_path_from_argv())


def peak_memory_mib():
    try:
        import resource
    except ImportError:  # Windows
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024  # macOS: bytes, Linux: KiB


def main():
    agents = {chess.WHITE: K.KestrelAgent(), chess.BLACK: K.KestrelAgent()}
    for c, a in agents.items():
        a.initialize(color="white" if c else "black", opponent_id="o", time_control=(30.0, 0.3), seed=3)
    clock = {chess.WHITE: 30.0, chess.BLACK: 30.0}
    b = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    hist = []
    worst = 0.0
    while not b.is_game_over(claim_draw=True) and len(hist) < 500:
        c = b.turn
        obs = Observation(fen=b.fen(), move_history=tuple(hist), my_remaining_time=clock[c],
                          opponent_remaining_time=clock[not c], increment=0.3,
                          color="white" if c else "black", opponent_id="o", match_game_index=1, seed=3)
        t0 = time.perf_counter()
        mv = agents[c].choose_move(obs)
        el = time.perf_counter() - t0
        worst = max(worst, el)
        clock[c] -= el
        assert clock[c] > 0, "ran out of time"
        assert el <= 5.0, f"move took {el:.2f}s (limit 5s)"
        clock[c] += 0.3
        m = chess.Move.from_uci(mv)
        assert m in b.legal_moves, f"illegal move {mv}"
        b.push(m)
        hist.append(mv)
    mem = peak_memory_mib()
    print(f"plies={len(hist)} result={b.result(claim_draw=True)} slowest move={worst:.2f}s "
          f"final clocks W={clock[True]:.1f}s B={clock[False]:.1f}s "
          f"TT sizes={[len(a.engine.tt) for a in agents.values()]} "
          f"peak memory={'n/a' if mem is None else f'{mem:.0f} MiB (two agents)'}")


if __name__ == "__main__":
    main()
