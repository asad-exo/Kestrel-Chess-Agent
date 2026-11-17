"""Generate deterministic sparring clones of Kestrel.

The clones search a fixed number of nodes per move instead of using the
clock, so they always play the same move in the same situation. That models
an opponent whose engine "thinks like us", the setting in which copying a
winning line in the color-reversed game of a pair can work.

    clone_plain.py    - fixed-node Kestrel with series memory switched off
    clone_copycat.py  - fixed-node Kestrel with series memory on (copies
                        winning lines from earlier games of the series)

Usage:
    python kestrel-chess-agent/tools/make_clones.py [--nodes 24576]
Files are written to tools/sparring/.
"""
import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SOURCE = os.path.join(REPO, "kestrel_v3.py")
OUT = os.path.join(HERE, "sparring")

TIME_CHECK = "        if not self.nodes & 1023 and time.perf_counter() > self.deadline:\n            raise TimeUp\n"
NODE_CHECK = ("        if not self.nodes & 1023 and (time.perf_counter() > self.deadline"
              " or self.nodes >= NODE_LIMIT):\n            raise TimeUp\n")


def patch(src, nodes, copycat, name):
    def sub(old, new, count=1):
        nonlocal src
        assert src.count(old) == count, f"pattern not found {count}x: {old[:60]!r}"
        src = src.replace(old, new)

    sub(TIME_CHECK, NODE_CHECK, count=2)  # main search and quiescence
    sub("                if elapsed > soft * 0.5:\n                    break",
        "                if self.nodes > NODE_LIMIT * 0.4:\n                    break")
    sub("        if opp_time < 5.0 and remaining > 2.0 * opp_time:", "        if False:  # clock-independent")
    sub("MATE = 30000\n", f"MATE = 30000\nNODE_LIMIT = {nodes}\n")
    sub('    name = "Kestrel"', f'    name = "{name}"')
    if not copycat:
        sub("        bias = self._series_bias(board, obs)", "        bias = None  # series memory off")
    return src


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nodes", type=int, default=24576, help="nodes searched per move")
    args = ap.parse_args()
    with open(SOURCE) as f:
        src = f.read()
    os.makedirs(OUT, exist_ok=True)
    for fname, copycat, name in (("clone_plain.py", False, "Clone"), ("clone_copycat.py", True, "Clone Copycat")):
        path = os.path.join(OUT, fname)
        with open(path, "w") as f:
            f.write(patch(src, args.nodes, copycat, name))
        print("wrote", os.path.relpath(path, REPO))


if __name__ == "__main__":
    main()
