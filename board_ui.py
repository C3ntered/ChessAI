"""Desktop chessboard for local human-versus-engine play."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import chess

from chessai import can_claim, game_result, reply


INK, MUTED, PAPER = "#192a24", "#53665c", "#f6f4ea"
DARK, LIGHT = "#799383", "#e4e4cc"
PIECES = " ♟♞♝♜♛♚"


class ChessWindow:
    def __init__(self, root, engine, args):
        self.root, self.engine, self.seconds = root, engine, args.seconds
        self.side = tk.StringVar(value=args.side.title())
        self.results = queue.Queue()
        self.busy = False
        self.board = chess.Board()
        self.root.title("ChessAI")
        self.root.configure(bg=PAPER)
        self.root.minsize(680, 460)
        self.root.geometry("930x650")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(root, bg=PAPER, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<Button-1>", self.click)

        panel = tk.Frame(root, bg=PAPER, width=225)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 22), pady=24)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(4, weight=1)
        def label(text, font, color=INK):
            return tk.Label(panel, text=text, bg=PAPER, fg=color, font=font, anchor="w")

        label("ChessAI", ("Georgia", 32, "bold")).grid(row=0, sticky="ew")
        label(engine.id.get("name", "UCI engine"), ("Helvetica", 12), MUTED).grid(row=1, sticky="ew")
        self.status = label("", ("Helvetica", 16, "bold"))
        self.status.config(wraplength=215, justify="left")
        self.status.grid(row=2, sticky="ew", pady=(22, 10))
        label("Moves", ("Helvetica", 12, "bold")).grid(row=3, sticky="ew", pady=4)
        self.history = tk.Listbox(panel, width=22, height=5, bg=PAPER, fg=INK,
                                  font=("Courier", 14), borderwidth=0, highlightthickness=0,
                                  activestyle="none", takefocus=False)
        self.history.grid(row=4, sticky="nsew")
        self.entry = ttk.Entry(panel, width=19)
        self.entry.grid(row=6, sticky="ew")
        self.entry.bind("<Return>", self.enter_move)
        label("Enter a move (e.g. Nf3)", ("Helvetica", 12), MUTED).grid(row=5, sticky="ew", pady=(8, 4))
        self.claim = ttk.Button(panel, text="Claim draw", command=self.claim_draw)
        self.claim.grid(row=7, sticky="ew", pady=6)
        label("Play next game as", ("Helvetica", 12), MUTED).grid(row=8, sticky="ew", pady=(10, 4))
        ttk.Combobox(panel, values=("White", "Black"), textvariable=self.side,
                     state="readonly", width=12).grid(row=9, sticky="ew")
        self.restart = ttk.Button(panel, text="New game", command=self.new_game)
        self.restart.grid(row=10, sticky="ew", pady=6)
        self.new_game()
        self.root.after(50, self.poll)

    def new_game(self):
        self.board.reset()
        self.human = self.side.get() == "White"
        self.game_id = object()
        self.selected = None
        self.finished = None
        self.history.delete(0, tk.END)
        self.entry.configure(state="normal")
        self.entry.delete(0, tk.END)
        self.advance()

    def advance(self):
        self.finished = self.finished or game_result(self.board)
        self.busy = self.finished is None and self.board.turn != self.human
        playable = not self.finished and not self.busy
        self.entry.configure(state="normal" if playable else "disabled")
        self.restart.configure(state="disabled" if self.busy else "normal")
        self.claim.configure(state="normal" if playable and self.board.can_claim_draw() else "disabled")
        status = self.finished or ("Engine thinking…" if self.busy else "Your move")
        if not self.finished and self.board.is_check():
            status += " · check"
        self.status.configure(text=status)
        self.draw()
        if self.busy:
            board, game = self.board.copy(), self.game_id
            def think():
                try:
                    answer = reply(self.engine, board, self.seconds, game)
                except Exception as exc:
                    answer = exc
                self.results.put(answer)
            threading.Thread(target=think, daemon=True).start()

    def poll(self):
        try:
            response = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            if isinstance(response, Exception):
                self.finished = f"Engine stopped: {response}"
            elif response[1]:
                self.finished = "½–½ · Engine claimed a draw"
            else:
                self.push(response[0])
            self.advance()
        self.root.after(50, self.poll)

    def push(self, move):
        san = self.board.san(move)
        if self.board.turn:
            self.history.insert(tk.END, f"{self.board.fullmove_number:>3}. {san:<8}")
        else:
            line = self.history.get(tk.END)
            self.history.delete(tk.END)
            self.history.insert(tk.END, line + san)
        self.history.see(tk.END)
        self.board.push(move)
        self.selected = None

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        self.cell = max(1, (min(w, h) - 40) // 8)
        s = self.cell
        self.x0, self.y0 = (w - 8*s)//2, (h - 8*s)//2
        last = self.board.peek() if self.board.move_stack else None
        targets = {m.to_square for m in self.board.legal_moves if m.from_square == self.selected}
        for row in range(8):
            for col in range(8):
                sq = self.square(row, col)
                x, y = self.x0 + col*s, self.y0 + row*s
                color = DARK if (row + col) % 2 else LIGHT
                if last and sq in (last.from_square, last.to_square):
                    color = "#bbbd78" if (row + col) % 2 else "#d3d398"
                if sq == self.selected:
                    color = "#e0b461"
                canvas.create_rectangle(x, y, x+s, y+s, fill=color, outline="")
                cx, cy = x+s/2, y+s/2
                piece = self.board.piece_at(sq)
                if piece:
                    # Use the filled glyph with an offset outline so white stays legible.
                    font = ("Apple Symbols", -int(max(8, s * .83)))
                    glyph = PIECES[piece.piece_type]
                    if piece.color:
                        for dx, dy in ((-1,0), (1,0), (0,-1), (0,1)):
                            canvas.create_text(cx+dx, cy+dy, text=glyph, font=font, fill=INK)
                    canvas.create_text(cx, cy, text=glyph, font=font,
                                       fill="#fffcf1" if piece.color else "#192722")
                if sq in targets:
                    r = s * (.44 if piece else .10)
                    canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=INK,
                                       fill="" if piece else INK, width=2)
                if col == 0:
                    canvas.create_text(x-11, cy, text=chess.square_rank(sq)+1, fill=MUTED)
                if row == 7:
                    canvas.create_text(cx, y+s+11, text=chess.FILE_NAMES[chess.square_file(sq)], fill=MUTED)

    def square(self, row, col):
        return chess.square(col, 7-row) if self.human else chess.square(7-col, row)

    def click(self, event):
        if self.busy or self.finished:
            return
        row = (event.y-self.y0)//self.cell
        col = (event.x-self.x0)//self.cell
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        sq = self.square(row, col)
        matches = [m for m in self.board.legal_moves
                   if m.from_square == self.selected and m.to_square == sq]
        if matches:
            if len(matches) == 1:
                self.move(matches[0])
            else:
                menu = tk.Menu(self.root, tearoff=False)
                for m in matches:
                    menu.add_command(label=chess.piece_name(m.promotion).title(),
                                     command=lambda move=m: self.move(move))
                menu.tk_popup(event.x_root, event.y_root)
        else:
            self.selected = sq if self.board.color_at(sq) == self.human and sq != self.selected else None
            self.draw()

    def move(self, move):
        self.entry.delete(0, tk.END)
        self.push(move)
        self.advance()

    def enter_move(self, _event):
        if self.busy or self.finished:
            return
        try:
            move = self.board.parse_san(self.entry.get().strip())
            if move not in self.board.legal_moves:
                raise ValueError
        except ValueError:
            self.status.configure(text="Enter a legal move")
            return
        self.move(move)

    def claim_draw(self):
        if can_claim(self.board):
            self.finished = "½–½ · Draw claimed"
        else:
            try:
                move = self.board.parse_san(self.entry.get().strip())
            except ValueError:
                move = None
            if move is None or not can_claim(self.board, move):
                self.status.configure(text="Type the intended drawing move, then claim")
                return
            self.finished = "½–½ · Draw claimed"
        self.advance()


def play_window(engine, args):
    root = tk.Tk()
    ChessWindow(root, engine, args)
    root.mainloop()
