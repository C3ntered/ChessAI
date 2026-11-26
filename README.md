# ChessAI

Double-click **Play.command** on this Mac to play Stockfish. Click a piece to see its legal destinations, then click a square to move. You can also type a move such as `Nf3`, `O-O`, or `e2e4` and press Return. Choose **Black** under **Play next game as** and click **New game** to let the engine open.

For a terminal game, run `./Play.command --cli`. Enter `resign` or `quit` to finish. Both interfaces handle castling, en passant, underpromotion, checkmate, stalemate, and repetition. To claim a draw based on your intended move, type the move and click **Claim draw**, or enter `claim Ng8` in the terminal.

## Engine strength

ChessAI runs Stockfish at maximum skill with strength limiting disabled. The default gives the engine five seconds per move, 256 MiB of hash memory and all but one logical CPU. For a longer search, run:

```sh
./Play.command --side black --seconds 30
```

The prepared Mac workspace includes a native Stockfish 11 build. To play the current Homebrew version, run `brew install stockfish` and reopen ChessAI. If Homebrew already manages your engine, use `brew upgrade stockfish`. The app prefers Stockfish on your PATH or in Homebrew over the project-local build. The board displays the engine's reported name. You can select a specific executable with `--engine /path/to/stockfish`. Use `--help` for CPU and memory settings.

## Set up a fresh checkout

Install Python 3.9 or later with Tk support for desktop play, then run the following from the repository directory on macOS:

```sh
brew install stockfish
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./Play.command
```

On another platform, install Stockfish on your PATH and run `python chessai.py` from a Python environment with the dependencies in `requirements.txt`. Terminal play with `--cli` works without Tk.

[Stockfish](https://stockfishchess.org/download/) · [Stockfish 11 source](https://github.com/official-stockfish/Stockfish/tree/sf_11) · [python-chess](https://github.com/niklasf/python-chess)
