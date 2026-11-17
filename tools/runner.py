"""Parallel local match runner built on the official starter-kit controller.

Every game uses fresh agent processes, real clocks and the official rules
(illegal moves, timeouts and crashes lose). Games are played in pairs from a
set of common openings with colors reversed.

Usage (from the starter-kit root):
    uv run python kestrel-chess-agent/tools/runner.py A.py B.py --games 40 --time 30 --inc 0.3
B (or A) may also be "random" or "greedy" for the starter kit's public agents.
"""
import argparse
import json
import math
import multiprocessing as mp
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.environ.get("CHESS_KIT", os.path.dirname(REPO))
sys.path.insert(0, KIT)

import chess  # noqa: E402

from chess_student_app.controller import GameConfig, LocalEndpoint, WorkerEndpoint, play_game  # noqa: E402
from public_agents import GreedyAgent, RandomAgent  # noqa: E402

OPENINGS = [
    "e2e4 e7e5 g1f3 b8c6 f1b5",
    "e2e4 e7e5 g1f3 b8c6 f1c4",
    "e2e4 c7c5 g1f3 d7d6",
    "e2e4 c7c5 g1f3 b8c6 d2d4 c5d4 f3d4",
    "e2e4 c7c5 b1c3",
    "e2e4 e7e6 d2d4 d7d5",
    "e2e4 c7c6 d2d4 d7d5",
    "d2d4 d7d5 c2c4 e7e6",
    "d2d4 d7d5 c2c4 c7c6",
    "d2d4 g8f6 c2c4 g7g6",
    "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4",
    "c2c4 e7e5",
    "g1f3 d7d5 g2g3",
    "e2e4 d7d5 e4d5 d8d5",
    "e2e4 g8f6",
    "d2d4 f7f5",
    "e2e4 e7e5 f2f4",
    "e2e4 g7g6 d2d4 f8g7",
    "d2d4 d7d5 c1f4",
    "e2e4 e7e5 g1f3 g8f6",
]


def opening_fen(line):
    b = chess.Board()
    for u in line.split():
        b.push_uci(u)
    return b.fen()


def make_endpoint(spec):
    if spec == "random":
        return LocalEndpoint(RandomAgent())
    if spec == "greedy":
        return LocalEndpoint(GreedyAgent())
    return WorkerEndpoint(os.path.abspath(spec))


def run_game(args):
    a, b, idx, fen, a_white, t, inc, seed = args
    config = GameConfig(initial_time=t, increment=inc)
    ea = make_endpoint(a)
    eb = make_endpoint(b)
    try:
        if a_white:
            white, black, wid, bid = ea, eb, "agent-a", "agent-b"
        else:
            white, black, wid, bid = eb, ea, "agent-b", "agent-a"
        rec = play_game(
            white, black, white_id=wid, black_id=bid,
            white_opponent_id="opp-" + bid, black_opponent_id="opp-" + wid,
            match_id="local", match_game_index=idx, seed=seed, config=config, starting_fen=fen,
        )
    finally:
        ea.close()
        eb.close()
    r = rec["result"]
    a_times = [c["elapsed_seconds"] for c in rec["move_callbacks"] if c["agent_id"] == "agent-a"]
    return {
        "idx": idx, "a_white": a_white,
        "a_score": r["white_score"] if a_white else r["black_score"],
        "term": r["termination_code"], "fault": r["fault_agent_id"], "plies": len(r["moves"]),
        "a_time_left": r["white_time"] if a_white else r["black_time"],
        "b_time_left": r["black_time"] if a_white else r["white_time"],
        "a_max_move": max(a_times) if a_times else 0.0,
        "pgn": r["pgn"],
    }


def elo(score, n):
    """Elo difference and approximate 95% half-width from a match score."""
    if n == 0:
        return 0.0, 0.0
    p = min(max(score / n, 1e-3), 1 - 1e-3)
    se = math.sqrt(p * (1 - p) / n)
    lo = min(max(p - 1.96 * se, 1e-3), 1 - 1e-3)
    hi = min(max(p + 1.96 * se, 1e-3), 1 - 1e-3)

    def to_elo(x):
        return -400 * math.log10(1 / x - 1)

    return to_elo(p), (to_elo(hi) - to_elo(lo)) / 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a", help="agent file (or random/greedy)")
    ap.add_argument("b", help="agent file (or random/greedy)")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--time", type=float, default=30.0, help="initial clock in seconds")
    ap.add_argument("--inc", type=float, default=0.3, help="increment per move in seconds")
    ap.add_argument("--jobs", type=int, default=2, help="games played in parallel (about one CPU core each)")
    ap.add_argument("--offset", type=int, default=0, help="start at a different opening")
    ap.add_argument("--out", default=None, help="write per-game results (with PGN) to this JSON file")
    args = ap.parse_args()

    tasks = []
    for g in range(args.games):
        line = OPENINGS[((g // 2) + args.offset) % len(OPENINGS)]
        tasks.append((args.a, args.b, g + 1, opening_fen(line), g % 2 == 0, args.time, args.inc, 1000 + g))
    t0 = time.time()
    results = []
    with mp.get_context("spawn").Pool(args.jobs) as pool:
        for res in pool.imap_unordered(run_game, tasks):
            results.append(res)
            s = sum(r["a_score"] for r in results)
            print(f"[{len(results):3d}/{args.games}] game {res['idx']:3d} A {'W' if res['a_white'] else 'B'} "
                  f"score={res['a_score']} {res['term']:22s} plies={res['plies']:3d} "
                  f"A_left={res['a_time_left']:.1f}s B_left={res['b_time_left']:.1f}s | total {s}/{len(results)}",
                  flush=True)
    n = len(results)
    s = sum(r["a_score"] for r in results)
    w = sum(r["a_score"] == 1 for r in results)
    d = sum(r["a_score"] == 0.5 for r in results)
    lost = sum(r["a_score"] == 0 for r in results)
    e, err = elo(s, n)
    terms = {}
    for r in results:
        terms[r["term"]] = terms.get(r["term"], 0) + 1
    print(f"\nA = {args.a}\nB = {args.b}")
    print(f"Score A: {s}/{n} (+{w} ={d} -{lost})  Elo difference ~ {e:+.0f} +/- {err:.0f}")
    print(f"Faults A={sum(r['fault'] == 'agent-a' for r in results)} "
          f"B={sum(r['fault'] == 'agent-b' for r in results)}  terminations={terms}")
    print(f"A slowest move {max(r['a_max_move'] for r in results):.2f}s, "
          f"A lowest final clock {min(r['a_time_left'] for r in results):.2f}s, wall time {time.time() - t0:.0f}s")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f)


if __name__ == "__main__":
    main()
