"""Play a local game against a full-strength UCI chess engine."""
import argparse
import math
import os
from pathlib import Path
import shutil
import sys

import chess
import chess.engine


def engine_path(override):
    if override:
        path = shutil.which(os.path.expanduser(override))
        if path:
            return path
        raise ValueError(f"Cannot execute the selected engine: {override}")
    path = shutil.which("stockfish")
    if path:
        return path
    for candidate in (Path("/opt/homebrew/bin/stockfish"), Path("/usr/local/bin/stockfish"),
                      Path(__file__).resolve().parent / ".engine" / "stockfish"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise ValueError("Install Stockfish with 'brew install stockfish' or supply --engine PATH.")


def start_engine(args):
    engine = chess.engine.SimpleEngine.popen_uci(engine_path(args.engine))
    try:
        options = {}
        for name, value in (("Threads", args.threads), ("Hash", args.hash_mb),
                            ("Skill Level", None), ("UCI_LimitStrength", False)):
            if name in engine.options:
                spec = engine.options[name]
                if name == "Skill Level":
                    value = spec.max
                if value is not None:
                    if spec.max is not None:
                        value = min(value, spec.max)
                    if spec.min is not None:
                        value = max(value, spec.min)
                    options[name] = value
        engine.configure(options)
        engine.ping()
        return engine
    except BaseException:
        engine.close()
        raise


def game_result(board):
    outcome = board.outcome()
    if outcome:
        reason = outcome.termination.name.replace("_", " ").lower()
        return f"{outcome.result()} · {reason}"
    return None


def can_claim(board, move=None):
    """A claim may use the current position or a specific intended legal move."""
    if move is None:
        return board.is_fifty_moves() or board.is_repetition(3)
    if move not in board.legal_moves:
        return False
    board.push(move)
    try:
        return can_claim(board)
    finally:
        board.pop()


def reply(engine, board, seconds, game):
    result = engine.play(board, chess.engine.Limit(time=seconds),
                         info=chess.engine.INFO_SCORE, game=game)
    if result.move not in board.legal_moves:
        raise ValueError("The engine returned an illegal move.")
    score = result.info.get("score")
    claim = (score is not None and score.pov(board.turn).score(mate_score=100000) <= 0
             and (can_claim(board) or can_claim(board, result.move)))
    return result.move, claim


def play_terminal(engine, args):
    board = chess.Board()
    human = args.side == "white"
    print(f"Playing {engine.id.get('name', 'UCI engine')}. Enter e4, Nf3, or e2e4. "
          "Commands: claim [move], resign, quit.")
    while True:
        print(board.unicode(borders=True, orientation=human))
        outcome = game_result(board)
        if outcome:
            print(outcome)
            return
        if board.turn != human:
            move, claim = reply(engine, board, args.seconds, game=board)
            if claim:
                print("½–½ · Engine claimed a draw.")
                return
            print(f"Engine plays {board.san(move)}")
            board.push(move)
            continue
        try:
            entry = input("Your move > ").strip()
        except EOFError:
            return
        if entry.lower() in ("quit", "resign"):
            if entry.lower() == "resign":
                print("0–1" if human else "1–0", "· resignation")
            return
        try:
            parts = entry.split(maxsplit=1)
            if parts and parts[0].lower() == "claim":
                move = board.parse_san(parts[1]) if len(parts) == 2 else None
                if can_claim(board, move):
                    print("½–½ · Draw claimed.")
                    return
                print("No draw claim is available for that position.")
            else:
                move = board.parse_san(entry)
                if move not in board.legal_moves:
                    raise ValueError
                board.push(move)
        except ValueError:
            print("Enter a legal move, for example e4 or Nf3.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", action="store_true", help="play in the terminal")
    parser.add_argument("--side", choices=("white", "black"), default="white")
    parser.add_argument("--seconds", type=float, default=5, help="engine thinking time per move")
    parser.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--hash-mb", type=int, default=256, help="engine hash table size in MiB")
    parser.add_argument("--engine", default=os.environ.get("STOCKFISH_EXECUTABLE"),
                        help="path to a Stockfish or compatible UCI executable")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or min(args.seconds, args.threads, args.hash_mb) <= 0:
        parser.error("seconds, threads and hash size must be positive and finite")
    try:
        with start_engine(args) as engine:
            if args.cli:
                play_terminal(engine, args)
            else:
                from board_ui import play_window
                play_window(engine, args)
    except (ValueError, OSError, chess.engine.EngineError, TimeoutError) as exc:
        print(f"ChessAI: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
