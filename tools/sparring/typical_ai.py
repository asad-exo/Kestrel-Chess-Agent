"""Sparring partner (local testing only, not a submission).

Models what a classmate might get by asking an AI for a "strong chess bot"
with the starter kit: python-chess board, iterative-deepening negamax with
alpha-beta, transposition table, quiescence search, MVV-LVA + killer move
ordering and simple time management.

Its evaluation uses the PeSTO piece-square tables (Ronald Friederich, via
the Chess Programming Wiki). Those were fitted to game data, so they are NOT
allowed in an official competition submission; here they only make the
sparring partner a tougher test.
"""
import time

import chess

from chess_tournament_api import ChessAgent, Observation

MG = {1: 82, 2: 337, 3: 365, 4: 477, 5: 1025, 6: 0}
EG = {1: 94, 2: 281, 3: 297, 4: 512, 5: 936, 6: 0}
PH = {1: 0, 2: 1, 3: 1, 4: 2, 5: 4, 6: 0}

# PeSTO tables, a8 first (white's view)
_mg = {
    1: [0]*8 + [98,134,61,95,68,126,34,-11,-6,7,26,31,65,56,25,-20,-14,13,6,21,23,12,17,-23,-27,-2,-5,12,17,6,10,-25,-26,-4,-4,-10,3,3,33,-12,-35,-1,-20,-23,-15,24,38,-22] + [0]*8,
    2: [-167,-89,-34,-49,61,-97,-15,-107,-73,-41,72,36,23,62,7,-17,-47,60,37,65,84,129,73,44,-9,17,19,53,37,69,18,22,-13,4,16,13,28,19,21,-8,-23,-9,12,10,19,17,25,-16,-29,-53,-12,-3,-1,18,-14,-19,-105,-21,-58,-33,-17,-28,-19,-23],
    3: [-29,4,-82,-37,-25,-42,7,-8,-26,16,-18,-13,30,59,18,-47,-16,37,43,40,35,50,37,-2,-4,5,19,50,37,37,7,-2,-6,13,13,26,34,12,10,4,0,15,15,15,14,27,18,10,4,15,16,0,7,21,33,1,-33,-3,-14,-21,-13,-12,-39,-21],
    4: [32,42,32,51,63,9,31,43,27,32,58,62,80,67,26,44,-5,19,26,36,17,45,61,16,-24,-11,7,26,24,35,-8,-20,-36,-26,-12,-1,9,-7,6,-23,-45,-25,-16,-17,3,0,-5,-33,-44,-16,-20,-9,-1,11,-6,-71,-19,-13,1,17,16,7,-37,-26],
    5: [-28,0,29,12,59,44,43,45,-24,-39,-5,1,-16,57,28,54,-13,-17,7,8,29,56,47,57,-27,-27,-16,-16,-1,17,-2,1,-9,-26,-9,-10,-2,-4,3,-3,-14,2,-11,-2,-5,2,14,5,-35,-8,11,2,8,15,-3,1,-1,-18,-9,10,-15,-25,-31,-50],
    6: [-65,23,16,-15,-56,-34,2,13,29,-1,-20,-7,-8,-4,-38,-29,-9,24,2,-16,-20,6,22,-22,-17,-20,-12,-27,-30,-25,-14,-36,-49,-1,-27,-39,-46,-44,-33,-51,-14,-14,-22,-46,-44,-30,-15,-27,1,7,-8,-64,-43,-16,9,8,-15,36,12,-54,8,-28,24,14],
}
_eg = {
    1: [0]*8 + [178,173,158,134,147,132,165,187,94,100,85,67,56,53,82,84,32,24,13,5,-2,4,17,17,13,9,-3,-7,-7,-8,3,-1,4,7,-6,1,0,-5,-1,-8,13,8,8,10,13,0,2,-7] + [0]*8,
    2: [-58,-38,-13,-28,-31,-27,-63,-99,-25,-8,-25,-2,-9,-25,-24,-52,-24,-20,10,9,-1,-9,-19,-41,-17,3,22,22,22,11,8,-18,-18,-6,16,25,16,17,4,-18,-23,-3,-1,15,10,-3,-20,-22,-42,-20,-10,-5,-2,-20,-23,-44,-29,-51,-23,-15,-22,-18,-50,-64],
    3: [-14,-21,-11,-8,-7,-9,-17,-24,-8,-4,7,-12,-3,-13,-4,-14,2,-8,0,-1,-2,6,0,4,-3,9,12,9,14,10,3,2,-6,3,13,19,7,10,-3,-9,-12,-3,8,10,13,3,-7,-15,-14,-18,-7,-1,4,-9,-15,-27,-23,-9,-23,-5,-9,-16,-5,-17],
    4: [13,10,18,15,12,12,8,5,11,13,13,11,-3,3,8,3,7,7,7,5,4,-3,-5,-3,4,3,13,1,2,1,-1,2,3,5,8,4,-5,-6,-8,-11,-4,0,-5,-1,-7,-12,-8,-16,-6,-6,0,2,-9,-9,-11,-3,-9,2,3,-1,-5,-13,4,-20],
    5: [-9,22,22,27,27,19,10,20,-17,20,32,41,58,25,30,0,-20,6,9,49,47,35,19,9,3,22,24,45,57,40,57,36,-18,28,19,47,31,34,39,23,-16,-27,15,6,9,17,10,5,-22,-23,-30,-16,-16,-23,-36,-32,-33,-28,-22,-43,-5,-32,-20,-41],
    6: [-74,-35,-18,-18,-11,15,4,-17,-12,17,14,17,17,38,23,11,10,17,23,15,20,45,44,13,-8,22,24,27,26,33,26,3,-18,-4,21,24,27,23,9,-11,-19,-3,11,21,23,16,7,-9,-27,-11,4,13,14,4,-5,-17,-53,-34,-21,-11,-28,-14,-24,-43],
}


def evaluate(board):
    mg = [0, 0]
    eg = [0, 0]
    phase = 0
    for sq, piece in board.piece_map().items():
        pt = piece.piece_type
        if piece.color == chess.WHITE:
            idx = sq ^ 56
            c = 0
        else:
            idx = sq
            c = 1
        mg[c] += MG[pt] + _mg[pt][idx]
        eg[c] += EG[pt] + _eg[pt][idx]
        phase += PH[pt]
    phase = min(phase, 24)
    mg_s = mg[0] - mg[1]
    eg_s = eg[0] - eg[1]
    score = (mg_s * phase + eg_s * (24 - phase)) // 24
    return score if board.turn == chess.WHITE else -score


INF = 10 ** 9
MATE = 100000
VAL = {1: 100, 2: 320, 3: 330, 4: 500, 5: 900, 6: 20000}


class Timeout(Exception):
    pass


class TypicalAIAgent(ChessAgent):
    name = "Typical AI"

    def initialize(self, *, color, opponent_id, time_control, seed):
        self.tt = {}

    def __init__(self):
        self.tt = {}

    def order(self, board, moves, tt_move, ply):
        def key(m):
            if m == tt_move:
                return 10 ** 7
            if board.is_capture(m):
                victim = board.piece_type_at(m.to_square) or 1
                attacker = board.piece_type_at(m.from_square)
                return 10 ** 6 + VAL[victim] * 10 - VAL[attacker] // 10
            if m.promotion:
                return 9 * 10 ** 5
            if m in self.killers.get(ply, ()):
                return 8 * 10 ** 5
            return 0
        return sorted(moves, key=key, reverse=True)

    def quiesce(self, board, alpha, beta):
        self.nodes += 1
        if self.nodes % 1024 == 0 and time.perf_counter() > self.deadline:
            raise Timeout
        stand = evaluate(board)
        if stand >= beta:
            return beta
        if alpha < stand:
            alpha = stand
        for m in self.order(board, list(board.generate_legal_captures()), None, 0):
            board.push(m)
            score = -self.quiesce(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def negamax(self, board, depth, alpha, beta, ply):
        self.nodes += 1
        if self.nodes % 1024 == 0 and time.perf_counter() > self.deadline:
            raise Timeout
        if board.is_checkmate():
            return -MATE + ply
        if board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100:
            return 0
        if ply > 0 and board.is_repetition(2):
            return 0
        key = board._transposition_key()
        entry = self.tt.get(key)
        tt_move = None
        if entry:
            d, flag, val, tt_move = entry
            if d >= depth and ply > 0:
                if flag == 0:
                    return val
                if flag == 1 and val >= beta:
                    return val
                if flag == 2 and val <= alpha:
                    return val
        if depth <= 0:
            return self.quiesce(board, alpha, beta)
        orig = alpha
        best = -INF
        best_move = None
        for m in self.order(board, list(board.legal_moves), tt_move, ply):
            board.push(m)
            score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.pop()
            if score > best:
                best = score
                best_move = m
            if score > alpha:
                alpha = score
            if alpha >= beta:
                if not board.is_capture(m):
                    ks = self.killers.setdefault(ply, [])
                    if m not in ks:
                        ks.insert(0, m)
                        del ks[2:]
                break
        flag = 0 if orig < best < beta else (1 if best >= beta else 2)
        self.tt[key] = (depth, flag, best, best_move)
        return best

    def choose_move(self, observation: Observation) -> str:
        board = chess.Board(observation.fen)
        legal = list(board.legal_moves)
        if len(legal) == 1:
            return legal[0].uci()
        budget = observation.my_remaining_time / 30 + observation.increment * 0.5
        budget = min(budget, observation.my_remaining_time * 0.2)
        self.deadline = time.perf_counter() + budget
        self.nodes = 0
        self.killers = {}
        if len(self.tt) > 200000:
            self.tt.clear()
        best = legal[0]
        try:
            for depth in range(1, 64):
                alpha, beta = -INF, INF
                cur_best = None
                cur_score = -INF
                key = board._transposition_key()
                entry = self.tt.get(key)
                tt_move = entry[3] if entry else None
                for m in self.order(board, legal, tt_move, 0):
                    board.push(m)
                    score = -self.negamax(board, depth - 1, -beta, -alpha, 1)
                    board.pop()
                    if score > cur_score:
                        cur_score = score
                        cur_best = m
                    if score > alpha:
                        alpha = score
                self.tt[key] = (depth, 0, cur_score, cur_best)
                best = cur_best
                if abs(cur_score) > MATE - 100:
                    break
        except Timeout:
            pass
        return best.uci()
