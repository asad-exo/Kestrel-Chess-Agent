"""Sparring wrapper around classic Sunfish (local testing only, not a submission).

Sunfish (https://github.com/thomasahle/sunfish, GPLv3) is not included here.
Clone it yourself and point SUNFISH_PATH at its sunfish.py, e.g.
    git clone https://github.com/thomasahle/sunfish
    set SUNFISH_PATH=C:\\path\\to\\sunfish\\sunfish.py        (Windows)
    export SUNFISH_PATH=/path/to/sunfish/sunfish.py          (macOS/Linux)
"""
import importlib.util
import os
import time

import chess

from chess_tournament_api import ChessAgent, Observation

_path = os.environ.get("SUNFISH_PATH")
if not _path or not os.path.exists(_path):
    raise RuntimeError("Set SUNFISH_PATH to the location of Sunfish's sunfish.py (see this file's docstring).")
_spec = importlib.util.spec_from_file_location("sunfish_engine", _path)
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)


def to_position(cb):
    rows = ["         \n", "         \n"]
    for rank in range(7, -1, -1):
        row = " "
        for f in range(8):
            p = cb.piece_at(chess.square(f, rank))
            row += p.symbol() if p else "."
        rows.append(row + "\n")
    rows += ["         \n", "         \n"]
    board = "".join(rows)
    score = 0
    for i, c in enumerate(board):
        if c.isupper():
            score += sf.pst[c][i]
        elif c.islower():
            score -= sf.pst[c.upper()][119 - i]
    wc = (cb.has_queenside_castling_rights(chess.WHITE), cb.has_kingside_castling_rights(chess.WHITE))
    bc = (cb.has_kingside_castling_rights(chess.BLACK), cb.has_queenside_castling_rights(chess.BLACK))
    ep = 0
    if cb.ep_square is not None and cb.has_legal_en_passant():
        ep = (9 - chess.square_rank(cb.ep_square)) * 10 + chess.square_file(cb.ep_square) + 1
    pos = sf.Position(board, score, wc, bc, ep, 0)
    return pos if cb.turn == chess.WHITE else pos.rotate()


class SunfishAgent(ChessAgent):
    name = "Sunfish"

    def __init__(self):
        self.searcher = sf.Searcher()

    def initialize(self, *, color, opponent_id, time_control, seed):
        self.searcher = sf.Searcher()

    def choose_move(self, observation: Observation) -> str:
        cb = chess.Board(observation.fen)
        legal = list(cb.legal_moves)
        if len(legal) == 1:
            return legal[0].uci()
        pos = to_position(cb)
        wtime = observation.my_remaining_time
        winc = observation.increment
        delay = 0.05
        budget = wtime / 40 + winc - delay
        soft = max(min(budget, wtime / 4 - delay), 0.05)
        think = max(min(5 * budget, wtime / 2 - delay), 0.1)
        start = time.time()
        self.searcher.deadline, self.searcher.soft = start + think, start + soft
        best, cand, d0 = None, None, 1
        white = cb.turn == chess.WHITE
        try:
            for depth, gamma, score, move in self.searcher.search([pos]):
                if depth > d0:
                    best, d0 = cand or best, depth
                if score >= gamma and move is not None:
                    i, j = move.i, move.j
                    if not white:
                        i, j = 119 - i, 119 - j
                    cand = sf.render(i) + sf.render(j) + move.prom.lower()
        except sf.Stop:
            cand = best or cand
        uci = cand or best
        try:
            if uci and chess.Move.from_uci(uci) in cb.legal_moves:
                return uci
        except ValueError:
            pass
        return legal[0].uci()
