"""Unit checks for series memory and series-aware draw valuation.

1) After losing game 1, the agent copies the winner's moves in the
   color-reversed game 2 (when its own search agrees within a margin).
2) After winning game 1, it deviates from the loser's line only at the move
   its stored evaluations mark as the mistake.
3) No bias when the game does not retrace an earlier one.
4) Draw value shifts with the series score from game 3 on.

Usage: python tests/test_series.py [agent.py]
"""
import _common
import chess
from chess_tournament_api import GameResult, Observation

K = _common.load_agent(_common.agent_path_from_argv())

START = chess.STARTING_FEN
# A Caro-Kann line; pretend Black won this game.
LINE = "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4 c8f5 e4g3 f5g6".split()


def result(my_color, white_score, moves, idx):
    my = white_score if my_color == "white" else 1 - white_score
    return GameResult(
        game_id=f"g{idx}", opponent_id="opp", my_color=my_color,
        outcome="win" if my == 1 else ("loss" if my == 0 else "draw"),
        my_score=my, opponent_score=1 - my, termination_code="checkmate", fault_side=None,
        moves=tuple(moves), my_remaining_time=10.0, opponent_remaining_time=10.0,
        starting_fen=START, seed=1, match_game_index=idx,
    )


def obs_after(moves, idx, color):
    b = chess.Board(START)
    for u in moves:
        b.push_uci(u)
    return b, Observation(
        fen=b.fen(), move_history=tuple(moves), my_remaining_time=20.0, opponent_remaining_time=20.0,
        increment=0.3, color=color, opponent_id="opp", match_game_index=idx, seed=7,
    )


ok = True

# 1) We lost game 1 as White; in game 2 we are Black -> copy Black's winning moves.
a = K.KestrelAgent()
a.initialize(color="white", opponent_id="opp", time_control=(30.0, 0.3), seed=1)
a.on_game_end(result("white", 0.0, LINE, 1))
a.initialize(color="black", opponent_id="opp", time_control=(30.0, 0.3), seed=2)
picks = []
for ply in (1, 3, 5, 7, 9):
    b, o = obs_after(LINE[:ply], 2, "black")
    mv = a.choose_move(o)
    picks.append((LINE[ply], mv, a.last_bias))
print("copy test (want our move == winner's move where the search agrees):")
for want, got, bias in picks:
    print(f"   winner played {want}  we played {got}  bias={bias}")
ok &= all(bias == {want: K.SERIES_BIAS} for want, _, bias in picks)
copied = sum(want == got for want, got, _ in picks)
print(f"   copied {copied}/5 moves")

# Without memory, how often does the engine pick those moves anyway?
a0 = K.KestrelAgent()
a0.initialize(color="black", opponent_id="opp", time_control=(30.0, 0.3), seed=2)
base = sum(a0.choose_move(obs_after(LINE[:ply], 2, "black")[1]) == LINE[ply] for ply in (1, 3, 5, 7, 9))
print(f"   without series memory the engine plays {base}/5 of them on its own")

# 2) We won game 1 as White; in game 2 we are Black -> avoid only the losing mistake.
a = K.KestrelAgent()
a.initialize(color="white", opponent_id="opp", time_control=(30.0, 0.3), seed=1)
a.cur_evals = {0: 20, 2: 25, 4: 150, 6: 160, 8: 170}   # our eval jumped after Black's ply-3 move
a.on_game_end(result("white", 1.0, LINE, 1))
b, o = obs_after(LINE[:1], 2, "black")
mv = a.choose_move(o)
print(f"no-mistake ply: loser played {LINE[1]}, bias={a.last_bias}, we played {mv}")
ok &= a.last_bias is None
b, o = obs_after(LINE[:3], 2, "black")
mv = a.choose_move(o)
print(f"mistake ply: loser played {LINE[3]}, bias={a.last_bias}, we played {mv}")
ok &= a.last_bias == {LINE[3]: -K.SERIES_AVOID} and mv != LINE[3]

# 3) Trajectory mismatch -> no bias.
b, o = obs_after(["d2d4"], 2, "black")
a.choose_move(o)
print("mismatch test: bias =", a.last_bias)
ok &= a.last_bias is None

# 4) Series-aware contempt.
c = K.KestrelAgent()
c.record["x"] = (1, 0, 0)
early, late = c._base_contempt("x", 2), c._base_contempt("x", 3)
c.record["y"] = (0, 0, 1)
early_b, late_b = c._base_contempt("y", 2), c._base_contempt("y", 3)
print(f"contempt ahead: game2={early} game3={late}; behind: game2={early_b} game3={late_b}")
ok &= late < early and late_b > early_b

print("ALL OK" if ok else "FAILED")
raise SystemExit(0 if ok else 1)
