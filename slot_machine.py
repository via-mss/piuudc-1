#!/usr/bin/env python3
"""
🎰 Slot Machine for the command line (CMD / terminal).

A small, dependency-free slot machine game written in Python 3.

How to play
-----------
Run the game, then type commands. Pressing Enter (empty input) spins
the reels. You start with 1000 credits. Five paylines (3 rows + 2
diagonals) pay out - three of a kind pays a multiplier of your bet,
a pair (first two symbols on a line) pays bet / 10. Three Lucky
Sevens on a line is the JACKPOT (x100).

Your balance and stats are saved to an SQLite database
(``slots_save.db``) next to this file and restored on the next run.
The old ``slots_save.json`` format is still read if present and is
migrated into the database on first load.

Usage
-----
    python slot_machine.py                  # play interactively
    python slot_machine.py --demo 10        # watch 10 automatic spins
    python slot_machine.py --ascii          # plain-text symbols (old cmd)
    python slot_machine.py --no-color       # disable colors
    python slot_machine.py --no-animation   # disable spin animation
    python slot_machine.py --reset          # delete save, start fresh
    python slot_machine.py --no-save        # don't load/save progress

On Windows you can also use ``py slot_machine.py``. Emoji symbols look
best in Windows Terminal / VS Code terminal; use ``--ascii`` for the
legacy cmd.exe console.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STARTING_BALANCE = 1000
DEFAULT_BET = 50
MIN_BET = 10
MAX_BET = 1000
PAIR_PAYOUT_DIVISOR = 10  # two of a kind pays bet // 10
SLOT_DB = Path(__file__).resolve().with_name("slots_save.db")
SLOT_JSON = Path(__file__).resolve().with_name("slots_save.json")  # legacy fallback

# ---------------------------------------------------------------------------
# Symbols and paylines
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Symbol:
    """One reel symbol."""

    key: str
    emoji: str
    ascii_char: str
    name: str
    weight: int  # relative probability weight (rarer = smaller)
    payout3: int  # multiplier of the total bet for 3 of a kind on a line
    width: int = 2  # terminal display width of the emoji


SYMBOLS: list[Symbol] = [
    Symbol("cherry", "🍒", "C", "Cherry", 30, 2),
    Symbol("lemon", "🍋", "L", "Lemon", 25, 3),
    Symbol("grapes", "🍇", "G", "Grapes", 20, 4),
    Symbol("star", "⭐", "S", "Star", 15, 6),
    Symbol("diamond", "💎", "D", "Diamond", 8, 15),
    Symbol("seven", "7", "7", "Lucky Seven", 2, 100, width=1),
]
SYMBOL_BY_KEY = {s.key: s for s in SYMBOLS}

# Each payline is a list of (row, col) cells on the 3x3 grid.
PAYLINES: list[list[tuple[int, int]]] = [
    [(0, 0), (0, 1), (0, 2)],  # top row
    [(1, 0), (1, 1), (1, 2)],  # middle row
    [(2, 0), (2, 1), (2, 2)],  # bottom row
    [(0, 0), (1, 1), (2, 2)],  # diagonal down
    [(2, 0), (1, 1), (0, 2)],  # diagonal up
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LineWin:
    """A single winning payline."""

    line_index: int
    symbol: Symbol
    count: int  # 2 (pair) or 3 (three of a kind)
    payout: int  # credits won on this line


@dataclass
class SpinResult:
    """Everything that happened during one spin."""

    grid: list[list[Symbol]]
    wins: list[LineWin]
    total_win: int
    balance: int  # balance after the spin
    jackpot: bool


@dataclass
class Stats:
    """Lifetime statistics for the player."""

    spins: int = 0
    total_bet: int = 0
    total_won: int = 0
    biggest_win: int = 0
    jackpots: int = 0

    @property
    def rtp(self) -> float:
        """Return to player ratio (total won / total bet)."""
        return (self.total_won / self.total_bet) if self.total_bet else 0.0


# ---------------------------------------------------------------------------
# Persistence (SQLite database + legacy JSON fallback)
# ---------------------------------------------------------------------------


class SaveStore:
    """SQLite-backed persistence for the slot machine's progress.

    Keeps a single-row ``saves`` table (id = 1); the latest progress is
    always in that row. Create on demand and call :meth:`close` when
    done. The store transparently recreates itself if the database file
    exists but is corrupt.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS saves (
        id          INTEGER PRIMARY KEY CHECK (id = 1),
        balance     INTEGER NOT NULL,
        bet         INTEGER NOT NULL,
        spins       INTEGER NOT NULL,
        total_bet   INTEGER NOT NULL,
        total_won   INTEGER NOT NULL,
        biggest_win INTEGER NOT NULL,
        jackpots    INTEGER NOT NULL,
        updated_at  TEXT    NOT NULL
    )
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = self._connect()

    def _connect(self) -> sqlite3.Connection:
        """Open (or recreate) the database and make sure the table exists."""
        while True:
            conn = sqlite3.connect(str(self.path))
            conn.row_factory = sqlite3.Row
            try:
                conn.execute(self.SCHEMA)
                conn.commit()
                return conn
            except sqlite3.Error:
                conn.close()
                try:
                    self.path.unlink()  # corrupt / invalid database file
                except OSError:
                    pass

    def save_state(self, state: dict) -> None:
        """Write ``state`` (``balance``, ``bet``, ``stats`` dict) to the DB."""
        stats = state["stats"]
        values = (
            state["balance"],
            state["bet"],
            stats["spins"],
            stats["total_bet"],
            stats["total_won"],
            stats["biggest_win"],
            stats["jackpots"],
            time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        cur = self._conn.execute("SELECT COUNT(*) FROM saves WHERE id = 1")
        if cur.fetchone()[0]:
            self._conn.execute(
                "UPDATE saves SET balance = ?, bet = ?, spins = ?, "
                "total_bet = ?, total_won = ?, biggest_win = ?, "
                "jackpots = ?, updated_at = ? WHERE id = 1",
                values,
            )
        else:
            self._conn.execute(
                "INSERT INTO saves (id, balance, bet, spins, total_bet, "
                "total_won, biggest_win, jackpots, updated_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )
        self._conn.commit()

    def load_state(self) -> dict | None:
        """Return the saved state as a dict, or None if nothing is saved."""
        row = self._conn.execute(
            "SELECT balance, bet, spins, total_bet, total_won, "
            "biggest_win, jackpots FROM saves WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return {
            "balance": row["balance"],
            "bet": row["bet"],
            "stats": {
                "spins": row["spins"],
                "total_bet": row["total_bet"],
                "total_won": row["total_won"],
                "biggest_win": row["biggest_win"],
                "jackpots": row["jackpots"],
            },
        }

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# ---------------------------------------------------------------------------
# Game logic (pure / testable - no printing here)
# ---------------------------------------------------------------------------


def evaluate_grid(grid: list[list[Symbol]], bet: int) -> list[LineWin]:
    """Check every payline of ``grid`` and return all wins for ``bet``."""
    wins: list[LineWin] = []
    for index, line in enumerate(PAYLINES):
        a, b, c = (grid[row][col] for row, col in line)
        if a == b == c:
            wins.append(LineWin(index, a, 3, bet * a.payout3))
        elif a == b:
            wins.append(LineWin(index, a, 2, max(1, bet // PAIR_PAYOUT_DIVISOR)))
    return wins


class SlotMachine:
    """The slot machine: balance, bet, spinning and persistence."""

    def __init__(
        self,
        balance: int = STARTING_BALANCE,
        bet: int = DEFAULT_BET,
        rng: random.Random | None = None,
    ) -> None:
        self.balance = balance
        self.bet = bet
        self.rng = rng or random.Random()
        self.stats = Stats()

    # -- core ----------------------------------------------------------

    def random_symbol(self) -> Symbol:
        """Draw one symbol using the weighted probabilities."""
        return self.rng.choices(SYMBOLS, weights=[s.weight for s in SYMBOLS])[0]

    def generate_grid(self) -> list[list[Symbol]]:
        """Generate a random 3x3 grid of symbols."""
        return [[self.random_symbol() for _ in range(3)] for _ in range(3)]

    def set_bet(self, amount: int) -> None:
        """Set the bet, validating it first. Raises ValueError if invalid."""
        if amount < MIN_BET:
            raise ValueError(f"minimum bet is {MIN_BET} credits")
        if amount > MAX_BET:
            raise ValueError(f"maximum bet is {MAX_BET} credits")
        if amount > self.balance:
            raise ValueError(
                f"bet {amount} exceeds your balance of {self.balance} credits"
            )
        self.bet = amount

    def spin(self) -> SpinResult:
        """Play one spin: deduct the bet, roll the grid, pay out wins."""
        if self.balance < self.bet:
            raise ValueError(
                f"not enough credits: bet is {self.bet}, balance is {self.balance}"
            )
        self.balance -= self.bet
        self.stats.spins += 1
        self.stats.total_bet += self.bet

        grid = self.generate_grid()
        wins = evaluate_grid(grid, self.bet)
        total_win = sum(w.payout for w in wins)
        self.balance += total_win

        self.stats.total_won += total_win
        self.stats.biggest_win = max(self.stats.biggest_win, total_win)
        jackpot = any(w.symbol.key == "seven" and w.count == 3 for w in wins)
        if jackpot:
            self.stats.jackpots += 1

        return SpinResult(
            grid=grid,
            wins=wins,
            total_win=total_win,
            balance=self.balance,
            jackpot=jackpot,
        )

    def reset(self) -> None:
        """Back to a fresh start."""
        self.balance = STARTING_BALANCE
        self.bet = DEFAULT_BET
        self.stats = Stats()

    # -- persistence ---------------------------------------------------

    def _state(self) -> dict:
        return {
            "balance": self.balance,
            "bet": self.bet,
            "stats": asdict(self.stats),
        }

    def save(self, path: Path | str | None = None) -> None:
        """Save progress.

        Defaults to the SQLite database (``slots_save.db``). A path with
        a ``.json`` suffix writes the legacy JSON format instead.
        """
        if path is None:
            path = SLOT_DB
        path = Path(path)
        state = self._state()
        if path.suffix.lower() == ".json":
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        else:
            store = SaveStore(path)
            try:
                store.save_state(state)
            finally:
                store.close()

    @classmethod
    def load(cls, path: Path | str | None = None) -> "SlotMachine":
        """Load a saved game. Returns a fresh machine if there is no
        (valid) save.

        Defaults to the SQLite database; if only the legacy
        ``slots_save.json`` exists it is loaded and migrated into the
        database on first run. A path with a ``.json`` suffix reads the
        legacy JSON format directly.
        """
        if path is None:
            state = cls._load_sqlite(SLOT_DB)
            if state is None:
                state = cls._load_json(SLOT_JSON)
                if state is not None:
                    cls._from_state(state).save(SLOT_DB)  # migrate
            return cls._from_state(state) if state is not None else cls()

        path = Path(path)
        if path.suffix.lower() == ".json":
            state = cls._load_json(path)
        else:
            state = cls._load_sqlite(path)
        return cls._from_state(state) if state is not None else cls()

    @classmethod
    def _from_state(cls, state: dict) -> "SlotMachine":
        machine = cls()
        machine.balance = int(state.get("balance", STARTING_BALANCE))
        machine.bet = int(state.get("bet", DEFAULT_BET))
        stats_data = state.get("stats", {})
        machine.stats = Stats(
            **{f.name: int(stats_data.get(f.name, 0)) for f in fields(Stats)}
        )
        return machine

    @staticmethod
    def _load_sqlite(path: Path) -> dict | None:
        try:
            store = SaveStore(path)
        except sqlite3.Error:
            return None
        try:
            return store.load_state()
        except sqlite3.Error:
            return None
        finally:
            store.close()

    @staticmethod
    def _load_json(path: Path) -> dict | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        try:
            int(data.get("balance", STARTING_BALANCE))
            int(data.get("bet", DEFAULT_BET))
        except (TypeError, ValueError):
            return None  # corrupted save -> fresh machine
        return data


# ---------------------------------------------------------------------------
# Rendering (terminal output)
# ---------------------------------------------------------------------------

WIDE_CHARS = set("🎰🍒🍋🍇⭐💎")


def disp_len(text: str) -> int:
    """Display width of a string (emoji count as width 2)."""
    return sum(2 if ch in WIDE_CHARS else 1 for ch in text)


def _c(text: str, code: str, enabled: bool) -> str:
    """Wrap text in an ANSI color code if colors are enabled."""
    return f"\033[{code}m{text}\033[0m" if enabled else text


def symbol_text(symbol: Symbol, use_ascii: bool) -> str:
    return symbol.ascii_char if use_ascii else symbol.emoji


def banner(use_ascii: bool = False, color: bool = False) -> str:
    title = "SLOT MACHINE" if use_ascii else "🎰 SLOT MACHINE 🎰"
    inner = 34
    pad = inner - disp_len(title)
    left, right = pad // 2, pad - pad // 2
    if use_ascii:
        border = "+" + "-" * inner + "+"
        middle = "|" + " " * left + title + " " * right + "|"
    else:
        border = "┌" + "─" * inner + "┐"
        middle = "│" + " " * left + title + " " * right + "│"
    return _c("\n".join([border, middle, border]), "1;33", color)


def render_grid(
    grid: list[list[Symbol]],
    use_ascii: bool = False,
    color: bool = False,
    highlight: set[tuple[int, int]] | None = None,
) -> str:
    """Render the 3x3 grid as a box. Always exactly 7 lines."""
    highlight = highlight or set()
    cell_w = 1 if use_ascii else 2
    if use_ascii:
        h, v = "-", "|"
        tl = tr = bl = br = tm = bm = ml = mr = cross = "+"
    else:
        h, v = "─", "│"
        tl, tr, bl, br = "┌", "┐", "└", "┘"
        tm, bm, ml, mr, cross = "┬", "┴", "├", "┤", "┼"

    seg = h * (cell_w + 2)

    def cell(symbol: Symbol, row: int, col: int) -> str:
        text = symbol_text(symbol, use_ascii)
        width = 1 if use_ascii else symbol.width
        pad = cell_w - width
        body = " " * (pad // 2) + text + " " * (pad - pad // 2)
        if color and (row, col) in highlight:
            body = _c(body, "1;32", True)
        return " " + body + " "

    lines = [tl + tm.join([seg] * 3) + tr]
    for row_idx, row in enumerate(grid):
        lines.append(v + v.join(cell(s, row_idx, c) for c, s in enumerate(row)) + v)
        if row_idx < 2:
            lines.append(ml + cross.join([seg] * 3) + mr)
    lines.append(bl + bm.join([seg] * 3) + br)
    return "\n".join(lines)


def winning_cells(result: SpinResult) -> set[tuple[int, int]]:
    """All grid cells that belong to a winning payline."""
    cells: set[tuple[int, int]] = set()
    for win in result.wins:
        cells.update(PAYLINES[win.line_index])
    return cells


def payout_table(use_ascii: bool = False, color: bool = False) -> str:
    lines = ["Payout table (multiplier of your total bet, per winning line):", ""]
    for s in SYMBOLS:
        lines.append(f"  {symbol_text(s, use_ascii)}  {s.name:<13} 3 of a kind  x{s.payout3}")
    lines.append(f"  *  Any pair (first two on a line)  bet / {PAIR_PAYOUT_DIVISOR}")
    lines.append("")
    lines.append("  5 paylines: 3 rows + 2 diagonals. Wins on different lines add up.")
    return "\n".join(lines)


def describe_wins(result: SpinResult, use_ascii: bool, color: bool) -> list[str]:
    if not result.wins:
        return ["No win this time. Spin again!"]
    lines = []
    for win in result.wins:
        sym = symbol_text(win.symbol, use_ascii)
        if win.count == 3:
            lines.append(
                f"Line {win.line_index + 1}: 3 x {sym} {win.symbol.name}"
                f"  ->  +{win.payout} credits"
            )
        else:
            lines.append(
                f"Line {win.line_index + 1}: pair of {sym} {win.symbol.name}"
                f"  ->  +{win.payout} credits"
            )
    lines.append(_c(f"Total win: +{result.total_win} credits!", "1;32", color))
    if result.jackpot:
        lines.append(_c("*** JACKPOT! Three Lucky Sevens! ***", "1;33", color))
    return lines


def format_stats(machine: SlotMachine) -> str:
    s = machine.stats
    rtp = f"{s.rtp:.1%}" if s.total_bet else "n/a"
    return (
        "--- Stats ---\n"
        f"Spins played : {s.spins}\n"
        f"Total bet    : {s.total_bet}\n"
        f"Total won    : {s.total_won}\n"
        f"Biggest win  : {s.biggest_win}\n"
        f"Jackpots     : {s.jackpots}\n"
        f"Return (RTP) : {rtp}"
    )


def animate_spin(
    machine: SlotMachine,
    result: SpinResult,
    use_ascii: bool,
    color: bool,
    frames: int = 9,
    delay: float = 0.07,
) -> None:
    """Animate the reels cycling, then settle on the final grid.

    Falls back to just printing the final grid when stdout is not a
    terminal (e.g. piped output or tests).
    """
    highlight = winning_cells(result)
    if not sys.stdout.isatty():
        print(render_grid(result.grid, use_ascii, color, highlight))
        return

    height = 7  # render_grid always returns 7 lines
    sys.stdout.write("\033[?25l")  # hide cursor
    try:
        for i in range(frames):
            if i:
                sys.stdout.write(f"\033[{height}A")  # back to top of grid
            sys.stdout.write(render_grid(machine.generate_grid(), use_ascii, color) + "\n")
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write(f"\033[{height}A")
        sys.stdout.write(render_grid(result.grid, use_ascii, color, highlight) + "\n")
        sys.stdout.flush()
    finally:
        sys.stdout.write("\033[?25h")  # show cursor


# ---------------------------------------------------------------------------
# Interactive game loop
# ---------------------------------------------------------------------------

HELP_TEXT = """Commands:
  spin / s / <Enter>   Spin the reels
  bet <amount>         Set your bet (min {min}, max {max})
  balance              Show your balance
  payouts              Show the payout table
  stats                Show your session stats
  auto <n>             Spin n times automatically
  reset                Start again with {start} credits
  help                 Show this help
  quit                 Save and exit
""".format(min=MIN_BET, max=MAX_BET, start=STARTING_BALANCE)


def do_spin(
    machine: SlotMachine,
    use_ascii: bool,
    color: bool,
    animate: bool,
    can_save: bool = True,
) -> SpinResult | None:
    if machine.balance < machine.bet:
        if machine.balance < MIN_BET:
            print("You're out of credits! Type 'reset' to start again.")
        else:
            print(
                f"Not enough credits for a {machine.bet}-credit bet "
                f"(balance {machine.balance}). Try 'bet {MIN_BET}' or 'reset'."
            )
        return None

    result = machine.spin()
    if animate:
        animate_spin(machine, result, use_ascii, color)
    else:
        print(render_grid(result.grid, use_ascii, color, winning_cells(result)))
    for line in describe_wins(result, use_ascii, color):
        print(line)
    print(f"Balance: {machine.balance} credits")
    if can_save:
        machine.save()
    return result


def handle_bet(machine: SlotMachine, args: list[str]) -> None:
    if not args:
        print(
            f"Current bet: {machine.bet} credits. "
            f"Usage: bet <amount> (min {MIN_BET}, max {MAX_BET})."
        )
        return
    try:
        amount = int(args[0])
    except ValueError:
        print("Bet must be a whole number, e.g. 'bet 50'.")
        return
    try:
        machine.set_bet(amount)
    except ValueError as exc:
        print(f"Invalid bet: {exc}")
    else:
        print(f"Bet set to {amount} credits.")


def handle_auto(
    machine: SlotMachine,
    args: list[str],
    use_ascii: bool,
    color: bool,
    can_save: bool = True,
) -> None:
    if not args:
        print("Usage: auto <n>  (e.g. 'auto 10')")
        return
    try:
        count = int(args[0])
    except ValueError:
        print("Count must be a whole number, e.g. 'auto 10'.")
        return
    if count <= 0:
        print("Count must be at least 1.")
        return
    count = min(count, 1000)
    for i in range(1, count + 1):
        if machine.balance < machine.bet:
            print("Out of credits during auto-play. Stopping.")
            break
        result = machine.spin()
        print(f"Spin {i}/{count}: win +{result.total_win} | balance {result.balance}")
    if can_save:
        machine.save()


def run_game(
    machine: SlotMachine,
    use_ascii: bool,
    color: bool,
    animate: bool,
    can_save: bool = True,
) -> None:
    print(banner(use_ascii, color))
    print(f"Welcome! You start with {machine.balance} credits. Bet: {machine.bet}.")
    print("Press Enter to spin, type 'help' for all commands.")
    print(payout_table(use_ascii, color))

    game_over_shown = False
    while True:
        if machine.balance < MIN_BET and not game_over_shown:
            print("\n*** GAME OVER *** You are out of credits.")
            print(format_stats(machine))
            print("Type 'reset' to play again with fresh credits, or 'quit' to exit.")
            game_over_shown = True

        try:
            raw = input(f"\nBalance: {machine.balance} | Bet: {machine.bet}\n> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        raw = raw.strip()
        if not raw:  # just press Enter to spin
            do_spin(machine, use_ascii, color, animate)
            continue

        parts = raw.split()
        cmd, args = parts[0].lower(), parts[1:]

        if cmd in ("q", "quit", "exit"):
            print("Goodbye!")
            break
        elif cmd in ("s", "spin"):
            do_spin(machine, use_ascii, color, animate, can_save)
        elif cmd in ("b", "bet"):
            handle_bet(machine, args)
        elif cmd in ("bal", "balance"):
            print(f"Balance: {machine.balance} credits | Bet: {machine.bet} credits")
        elif cmd in ("pay", "payouts", "paytable"):
            print(payout_table(use_ascii, color))
        elif cmd == "stats":
            print(format_stats(machine))
        elif cmd == "auto":
            handle_auto(machine, args, use_ascii, color, can_save)
        elif cmd == "reset":
            machine.reset()
            if can_save:
                machine.save()
            game_over_shown = False
            print(f"Fresh start! Balance: {machine.balance} credits, bet: {machine.bet}.")
        elif cmd in ("h", "help", "?"):
            print(HELP_TEXT)
        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for commands.")

    print(format_stats(machine))


def run_demo(machine: SlotMachine, spins: int, use_ascii: bool, color: bool) -> None:
    """Non-interactive demo: play ``spins`` spins and print the results."""
    print(banner(use_ascii, color))
    print(f"Demo: {spins} spins, bet {machine.bet} credits each.\n")
    for i in range(1, spins + 1):
        if machine.balance < machine.bet:
            print("Out of credits - topping up to 1000 for the demo.")
            machine.balance = STARTING_BALANCE
        result = machine.spin()
        print(render_grid(result.grid, use_ascii, color, winning_cells(result)))
        print(f"Spin {i}: win +{result.total_win} | balance {result.balance}")
        for line in describe_wins(result, use_ascii, color):
            print(line)
        print()
    print(format_stats(machine))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Slot machine for the command line."
    )
    parser.add_argument(
        "--demo",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Run N non-interactive demo spins and exit (default: 10).",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use plain ASCII symbols/borders (for old Windows cmd).",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable colors.")
    parser.add_argument(
        "--no-animation", action="store_true", help="Disable spin animation."
    )
    parser.add_argument(
        "--reset", action="store_true", help="Delete the save database and start fresh."
    )
    parser.add_argument(
        "--no-save", action="store_true", help="Don't load or save progress."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    use_ascii = args.ascii
    color = (
        not args.no_color
        and sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
    )
    animate = not args.no_animation

    if args.reset:
        deleted = []
        for save_path in (SLOT_DB, SLOT_JSON):
            try:
                save_path.unlink()
                deleted.append(str(save_path))
            except FileNotFoundError:
                pass
        if deleted:
            print(f"Save deleted: {', '.join(deleted)}")
        else:
            print("No save found - nothing to reset.")

    machine = SlotMachine() if args.no_save else SlotMachine.load()

    if args.demo is not None:
        run_demo(machine, max(0, args.demo), use_ascii, color)
        if not args.no_save:
            machine.save()
        return 0

    try:
        run_game(machine, use_ascii, color, animate, can_save=not args.no_save)
    finally:
        if not args.no_save:
            machine.save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
