"""Cross-check Kestrel's move generator against python-chess.

For every visited position:
  * the set of legal moves (as UCI) must be identical to python-chess,
  * the cheap legality filter must never skip a move the full test rejects,
  * each child position must equal a fresh conversion of python-chess's
    board (placement, castling rights, en passant, incremental score).

Usage: python tests/test_movegen.py [agent.py] [games]
"""
import random
import sys

import _common
import chess

K = _common.load_agent(_common.agent_path_from_argv())

TRICKY = [
    chess.STARTING_FEN,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",  # "kiwipete"
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "8/8/8/2k5/3Pp3/8/8/4K3 b - d3 0 1",   # en passant available
    "8/8/8/8/k2Pp2Q/8/8/3K4 b - d3 0 1",   # en passant pinned along the rank
    "4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1",
    "r3k2r/8/8/8/8/8/8/4K3 b kq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "4k3/1P6/8/8/8/8/6p1/4K3 w - - 0 1",    # promotions
    "n1n5/PPPk4/8/8/8/8/4Kppp/5N1N b - - 0 1",
]


def our_moves(pos, pst, white):
    board = pos[0]
    k = board.find("K")
    in_check = K.attacked(board, k)
    out = {}
    for m in K.gen_moves(board, pos[1], pos[3], k, in_check):
        i, j, pr = m
        need = in_check or board[i] == "K" or i in K.LINE[k] or (board[i] == "P" and j == pos[3])
        child = K.make_move(pos, m, k, need, pst)
        full = K.make_move(pos, m, k, True, pst)
        if (child is None) != (full is None):
            raise AssertionError(f"legality filter mismatch for {m} in\n{board}")
        if full is not None:
            uci = K.move_to_uci(m, white)
            assert uci not in out, f"duplicate move {uci}"
            out[uci] = full
    return out


def check_position(cb, pst):
    pos = K.pos_from_chess(cb, pst)
    white = cb.turn == chess.WHITE
    ours = our_moves(pos, pst, white)
    theirs = {m.uci() for m in cb.legal_moves}
    if set(ours) != theirs:
        raise AssertionError(f"move set mismatch in {cb.fen()}\n missing={theirs - set(ours)}\n"
                             f" extra={set(ours) - theirs}")
    for uci, child in ours.items():
        cb.push(chess.Move.from_uci(uci))
        ref = K.pos_from_chess(cb, pst)
        ep_square = cb.ep_square
        cb.pop()
        if child[0] != ref[0] or child[1] != ref[1] or child[2] != ref[2] or child[4] != ref[4]:
            raise AssertionError(f"child mismatch after {uci} in {cb.fen()}\n{child}\n{ref}")
        if child[3] != ref[3]:
            # Kestrel marks en passant whenever an enemy pawn is adjacent; python-chess
            # only when the capture is actually legal. That is the only allowed difference.
            assert ref[3] == 0 and ep_square is not None, f"en passant mismatch after {uci} in {cb.fen()}"
    return len(theirs)


def main(n_games=300, seed=1):
    rng = random.Random(seed)
    total = positions = 0
    for phase in (24, 12, 0):
        pst = K.build_pst(phase)
        for fen in TRICKY:
            total += check_position(chess.Board(fen), pst)
            positions += 1
    pst = K.build_pst(24)
    for _ in range(n_games):
        cb = chess.Board(rng.choice(TRICKY))
        for _ in range(rng.randint(10, 160)):
            if cb.is_game_over():
                break
            total += check_position(cb, pst)
            positions += 1
            moves = list(cb.legal_moves)
            special = [m for m in moves if cb.is_capture(m) or m.promotion or cb.is_castling(m)]
            cb.push(rng.choice(special) if special and rng.random() < 0.4 else rng.choice(moves))
    print(f"OK: {positions} positions, {total} legal moves cross-checked against python-chess")


if __name__ == "__main__":
    games = int(sys.argv[-1]) if len(sys.argv) > 1 and sys.argv[-1].isdigit() else 300
    main(games)
