"""Series runner: both agents stay alive across a 4-game series, as in the
student league. The first agent plays White, Black, Black, White; games 1-2
share one opening and games 3-4 another (colors reversed within each pair).
This is the setting where in-matchup learning (series memory) matters.

Usage (from the starter-kit root):
    uv run python kestrel-chess-agent/tools/series_runner.py A.py B.py --series 10 --time 10 --inc 0.1
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
KIT = os.environ.get("CHESS_KIT", os.path.dirname(REPO))
sys.path.insert(0, KIT)
sys.path.insert(0, HERE)

from chess_student_app.controller import GameConfig, WorkerEndpoint, play_game  # noqa: E402
from runner import OPENINGS, opening_fen  # noqa: E402


def run_series(args):
    a, b, k, t, inc = args
    config = GameConfig(initial_time=t, increment=inc)
    fens = [opening_fen(OPENINGS[(2 * k) % len(OPENINGS)]), opening_fen(OPENINGS[(2 * k + 1) % len(OPENINGS)])]
    ea, eb = WorkerEndpoint(a), WorkerEndpoint(b)
    out = []
    try:
        schedule = ((True, fens[0]), (False, fens[0]), (False, fens[1]), (True, fens[1]))
        for g, (a_white, fen) in enumerate(schedule, 1):
            if not ea.alive:  # the tournament restarts an agent after a fault
                ea = WorkerEndpoint(a)
            if not eb.alive:
                eb = WorkerEndpoint(b)
            if a_white:
                white, black, wid, bid, wopp, bopp = ea, eb, "agent-a", "agent-b", "opp-b", "opp-a"
            else:
                white, black, wid, bid, wopp, bopp = eb, ea, "agent-b", "agent-a", "opp-a", "opp-b"
            rec = play_game(white, black, white_id=wid, black_id=bid, white_opponent_id=wopp,
                            black_opponent_id=bopp, match_id=f"series{k}", match_game_index=g,
                            seed=5000 + 10 * k + g, config=config, starting_fen=fen)
            r = rec["result"]
            out.append({
                "series": k, "game": g, "a_white": a_white,
                "a_score": r["white_score"] if a_white else r["black_score"],
                "term": r["termination_code"], "fault": r["fault_agent_id"],
                "plies": len(r["moves"]), "moves": r["moves"],
                "a_left": r["white_time"] if a_white else r["black_time"],
            })
    finally:
        ea.close()
        eb.close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--series", type=int, default=10)
    ap.add_argument("--time", type=float, default=10.0)
    ap.add_argument("--inc", type=float, default=0.1)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    a, b = os.path.abspath(args.a), os.path.abspath(args.b)
    tasks = [(a, b, k, args.time, args.inc) for k in range(args.series)]
    t0 = time.time()
    games = []
    with mp.get_context("spawn").Pool(args.jobs) as pool:
        for res in pool.imap_unordered(run_series, tasks):
            games.extend(res)
            s = sum(x["a_score"] for x in res)
            shared = 0  # how long game 2 retraced game 1 (same opening, colors reversed)
            for x, y in zip(res[0]["moves"], res[1]["moves"]):
                if x != y:
                    break
                shared += 1
            print(f"series {res[0]['series']:2d}: A scored {s}/4 "
                  f"[{' '.join(str(x['a_score']) for x in res)}]  game 2 retraced game 1 for {shared} plies",
                  flush=True)
    n = len(games)
    s = sum(g["a_score"] for g in games)
    by_game = {i: sum(g["a_score"] for g in games if g["game"] == i) for i in range(1, 5)}
    print(f"\nA = {args.a}\nB = {args.b}")
    print(f"A total {s}/{n}  by game number {by_game}  A faults={sum(g['fault'] == 'agent-a' for g in games)}  "
          f"A lowest final clock {min(g['a_left'] for g in games):.1f}s  wall time {time.time() - t0:.0f}s")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(games, f)


if __name__ == "__main__":
    main()
