# Kestrel — a chess agent for the Chess Agent Competition

Kestrel is a pure-Python chess agent written for the Chess Agent Competition
(30 s + 0.3 s per move, one CPU, 512 MiB, Python 3.12 with only the standard
library and `python-chess`). It uses its own fast board representation and an
alpha-beta search with standard pruning. On top of that it adds some
game-theoretic logic for series play: it remembers earlier games in a matchup
and decides how much a draw is worth from the series score.

The agent is a single file, [`kestrel_v3.py`](kestrel_v3.py). Everything else
in this repository is testing tooling.

> The course starter kit is **not** included. The tools and tests need it,
> because they use its official game controller and agent API.

## Repository layout

| Path | What it is |
|---|---|
| `kestrel_v3.py` | The agent |
| `tools/runner.py` | Parallel match runner using the official controller, real clocks and fault rules |
| `tools/series_runner.py` | 4-game series with both agents kept alive (W, B, B, W; paired openings) |
| `tools/make_clones.py` | Generates deterministic, fixed-node clones of Kestrel for series experiments |
| `tools/sparring/typical_ai.py` | Sparring bot: a typical AI-written python-chess engine |
| `tools/sparring/sunfish_agent.py` | Sparring wrapper for [Sunfish](https://github.com/thomasahle/sunfish) (clone it separately) |
| `tests/test_movegen.py` | Cross-checks the move generator against python-chess on thousands of positions |
| `tests/test_search.py` | Tactical puzzles plus a depth/speed report |
| `tests/test_series.py` | Unit checks for series memory and series-aware draw valuation |
| `tests/test_stress.py` | Full self-play game at the real clock: legality, timing, memory |
| `tests/bench_depth.py` | Fixed-depth speed comparison between agent versions |

## Setup

1. Get the course starter kit and run it once (`START_HERE_WINDOWS.cmd` or
   `START_HERE_MACOS_LINUX.sh`), so that `uv` creates its environment.
2. Put this folder inside the starter-kit root, next to `workspace/`:

   ```
   Chess_Agent_Tournament_Student_v1.1/
   ├── chess_student_app/
   ├── chess_tournament_api/
   ├── workspace/
   └── kestrel-chess-agent/      <- this repository
   ```

   (Or keep it elsewhere and set the `CHESS_KIT` environment variable to the
   starter-kit folder.)
3. Run every command below from the starter-kit root.

## Validate

The starter kit's validator checks the file's imports, size, loading and a
few test games. It expects a NetID-style filename (letters followed by
digits), so validate a copy with such a name, for example `abc123.py`:

```bash
copy kestrel-chess-agent\kestrel_v3.py workspace\abc123.py          # Windows
cp kestrel-chess-agent/kestrel_v3.py workspace/abc123.py            # macOS/Linux
uv run python -m chess_student_app.cli validate workspace/abc123.py
```

It should end with `PASSED — SUBMISSION READY`.

## Tests

```bash
uv run python kestrel-chess-agent/tests/test_movegen.py        # move generator vs python-chess
uv run python kestrel-chess-agent/tests/test_search.py         # tactics + depth/speed
uv run python kestrel-chess-agent/tests/test_series.py         # series memory + draw valuation
uv run python kestrel-chess-agent/tests/test_stress.py         # full game at 30 s + 0.3 s
uv run python kestrel-chess-agent/tests/bench_depth.py 6 kestrel-chess-agent/kestrel_v3.py
```

Each test takes an optional agent file as its first argument, so you can
test a modified copy.

## Matches

```bash
# 40 games vs the starter kit's greedy agent, real time control
uv run python kestrel-chess-agent/tools/runner.py kestrel-chess-agent/kestrel_v3.py greedy --games 40

# 40 faster games vs the typical-AI sparring bot
uv run python kestrel-chess-agent/tools/runner.py kestrel-chess-agent/kestrel_v3.py kestrel-chess-agent/tools/sparring/typical_ai.py --time 10 --inc 0.1

# compare two versions of your own agent
uv run python kestrel-chess-agent/tools/runner.py my_new_version.py kestrel-chess-agent/kestrel_v3.py --games 60 --time 10 --inc 0.1

# series experiments against deterministic clones
uv run python kestrel-chess-agent/tools/make_clones.py
uv run python kestrel-chess-agent/tools/series_runner.py kestrel-chess-agent/kestrel_v3.py kestrel-chess-agent/tools/sparring/clone_copycat.py --series 10
```

`--jobs` sets how many games run in parallel. Keep it at or below your CPU
core count, because each game needs about one core and the clocks are real.
The runner prints an Elo estimate with a 95% margin. With 40–60 games that
margin is roughly ±90–110 Elo, so only large differences are conclusive.

For Sunfish, clone https://github.com/thomasahle/sunfish and set
`SUNFISH_PATH` to its `sunfish.py` before using
`tools/sparring/sunfish_agent.py`.

## How Kestrel works

**Board.** The board is a 120-character string (a 10×12 "mailbox"), rotated
180° after every move so the side to move is always uppercase and always moves
"up". Slicing, reversing and `swapcase` run in C, so making a move is much
cheaper than python-chess's `push`/`pop`. The rotated-string idea comes from
Sunfish; this is an independent implementation. Move generation is fully
legal: a cheap pin/check filter runs the attack test only for moves that could
expose the king.

**Search.** Iterative deepening with principal-variation alpha-beta and
aspiration windows. It uses a transposition table, null-move pruning,
late-move reductions, reverse-futility and futility pruning, and a check
extension. Moves are ordered by MVV-LVA, killer moves and history. A
quiescence search handles captures, check evasions, delta pruning and a
filter for captures onto pawn-defended squares.

**Evaluation.** Material and piece-square tables are designed by hand from
basic chess principles and generated by explicit formulas. The principles are
centralization, development, king shelter, pawn advancement and rooks on the
seventh rank. Middlegame and endgame values are blended by game phase. Further
terms cover:

- the bishop pair;
- pawn structure (passed, doubled and isolated pawns), cached per pawn
  configuration;
- rooks on open and half-open files;
- the pawn shelter in front of a castled king;
- endgame knowledge: "mop-up" to convert won endings, plus scaling for
  insufficient material and drawish endings.

No value is fitted to game data or engine output.

**Game-level logic.**

- **Repetition-aware search.** The FEN in each observation carries no
  history, so Kestrel tracks the real game history itself. It avoids
  repetitions when ahead and steers into them when behind. It is also aware
  of the fifty-move rule and the 500-ply cap.
- **Time management.** Soft and hard time limits keep each move well under
  the 5 s cap, and the clock never runs low at 30 s + 0.3 s.
- **Contempt.** How much a draw is worth depends on results earlier in the
  matchup and on the opponent's clock.
- **Series memory.** Games in a pair share a starting position with colors
  reversed. When a game retraces an earlier one move for move, Kestrel favors
  the moves that won for the side it is now playing ("strategy stealing").
  It deviates only at the single move where its stored evaluations show the
  losing side went wrong. This also defends against opponents who copy
  Kestrel's winning lines.
- **Series-aware draw value.** From game 3 of a series, the draw value
  follows the series score, because knockout series are decided on score and
  ties go to the higher seed.
- **Reliability.** Every move is verified with python-chess before it is
  returned, and any internal error falls back to a safe legal move.

## Rules compliance

- **No offline-trained weights.** Every evaluation and move-ordering value
  was chosen by hand. (An earlier version used the PeSTO tables, which were
  fitted with Texel tuning. It was replaced after the course clarified the
  rule.)
- **Learning stays within a matchup.** All learned state lives in the agent
  instance, and nothing is written to disk. It resets with the fresh instance
  created for each matchup.
- **Allowed imports only.** Only the standard library and `python-chess`;
  no threads and no thinking on the opponent's time.

## Results (local testing)

Measured on a 2-core machine. Scores are from Kestrel's side.

| Opponent / experiment | Time control | Result |
|---|---|---|
| Typical AI-written python-chess bot (uses PeSTO tables) | 10 s + 0.1 s | 19.5 / 20 |
| Sunfish | 30 s + 0.3 s | 16 / 20 (+13 =6 −1) |
| Hand-made tables vs the earlier PeSTO version (cost of compliance) | 10 s + 0.1 s | 19.5 / 60 (≈ −127 ± 97 Elo) |
| Pawn structure + rook files + king shelter vs without | 10 s + 0.1 s | 33 / 60 (≈ +35 ± 90 Elo) |
| Series memory vs a copycat clone (earlier build) | 10 s + 0.1 s | 67% vs 60% without |

Experiments that did not help and were left out:

- late-move pruning plus internal iterative reduction (≈ −161 ± 102 Elo);
- spending more of the clock (≈ −41 ± 91);
- pawn structure on its own (neutral).

No test game ended in a fault.

## Acknowledgements

- Rotated-string board idea: [Sunfish](https://github.com/thomasahle/sunfish)
  by Thomas Ahle.
- Search techniques: the
  [Chess Programming Wiki](https://www.chessprogramming.org/).
