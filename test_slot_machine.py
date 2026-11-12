#!/usr/bin/env python3
"""
Tests for slot_machine.py.

Run with:
    python -m unittest test_slot_machine -v
"""

import random
import tempfile
import unittest
from pathlib import Path

from slot_machine import (
    DEFAULT_BET,
    MAX_BET,
    MIN_BET,
    STARTING_BALANCE,
    SYMBOLS,
    SYMBOL_BY_KEY,
    LineWin,
    SlotMachine,
    SpinResult,
    evaluate_grid,
    render_grid,
    winning_cells,
)


def grid_from(keys):
    """Build a 3x3 grid from 9 symbol keys in row-major order."""
    assert len(keys) == 9
    syms = [SYMBOL_BY_KEY[k] for k in keys]
    return [syms[0:3], syms[3:6], syms[6:9]]


class EvaluateGridTests(unittest.TestCase):
    def test_three_of_a_kind_pays_multiplier(self):
        grid = grid_from(
            [
                "cherry", "cherry", "cherry",
                "lemon", "grapes", "star",
                "diamond", "lemon", "grapes",
            ]
        )
        wins = evaluate_grid(grid, bet=50)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].count, 3)
        self.assertEqual(wins[0].symbol.key, "cherry")
        self.assertEqual(wins[0].payout, 2 * 50)  # cherry pays x2

    def test_pair_pays_tenth_of_bet(self):
        grid = grid_from(
            [
                "cherry", "cherry", "lemon",
                "grapes", "star", "diamond",
                "lemon", "grapes", "star",
            ]
        )
        wins = evaluate_grid(grid, bet=50)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].count, 2)
        self.assertEqual(wins[0].payout, 5)  # 50 // 10

    def test_pair_payout_uses_integer_division(self):
        grid = grid_from(
            [
                "lemon", "lemon", "grapes",
                "cherry", "star", "diamond",
                "grapes", "cherry", "star",
            ]
        )
        wins = evaluate_grid(grid, bet=25)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].payout, 2)  # 25 // 10

    def test_pair_must_be_first_two_on_line(self):
        # Pair in positions 2-3 does NOT pay.
        grid = grid_from(
            [
                "lemon", "cherry", "cherry",
                "grapes", "star", "diamond",
                "diamond", "lemon", "grapes",
            ]
        )
        self.assertEqual(evaluate_grid(grid, bet=50), [])

    def test_no_win(self):
        grid = grid_from(
            [
                "cherry", "lemon", "grapes",
                "star", "diamond", "cherry",
                "lemon", "grapes", "star",
            ]
        )
        self.assertEqual(evaluate_grid(grid, bet=50), [])

    def test_jackpot_three_sevens_on_diagonal(self):
        grid = grid_from(
            [
                "seven", "cherry", "lemon",
                "grapes", "seven", "star",
                "diamond", "lemon", "seven",
            ]
        )
        wins = evaluate_grid(grid, bet=50)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].symbol.key, "seven")
        self.assertEqual(wins[0].count, 3)
        self.assertEqual(wins[0].payout, 100 * 50)  # jackpot x100

    def test_multiple_lines_add_up(self):
        grid = grid_from(
            [
                "cherry", "cherry", "cherry",
                "lemon", "grapes", "star",
                "cherry", "cherry", "cherry",
            ]
        )
        wins = evaluate_grid(grid, bet=50)
        self.assertEqual(len(wins), 2)
        self.assertEqual(sum(w.payout for w in wins), 2 * 2 * 50)


class SlotMachineTests(unittest.TestCase):
    def test_spin_updates_balance_and_stats(self):
        machine = SlotMachine(rng=random.Random(42))
        result = machine.spin()
        self.assertEqual(
            machine.balance, STARTING_BALANCE - DEFAULT_BET + result.total_win
        )
        self.assertEqual(machine.stats.spins, 1)
        self.assertEqual(machine.stats.total_bet, DEFAULT_BET)
        self.assertEqual(machine.stats.total_won, result.total_win)
        self.assertEqual(machine.stats.biggest_win, result.total_win)
        self.assertEqual(result.balance, machine.balance)

    def test_spin_raises_without_enough_credits(self):
        machine = SlotMachine(balance=5, bet=50)
        with self.assertRaises(ValueError):
            machine.spin()

    def test_spin_jackpot_updates_stats(self):
        machine = SlotMachine(rng=random.Random(1))
        machine.generate_grid = lambda: grid_from(
            [
                "seven", "cherry", "lemon",
                "grapes", "seven", "star",
                "diamond", "lemon", "seven",
            ]
        )
        result = machine.spin()
        self.assertTrue(result.jackpot)
        self.assertEqual(machine.stats.jackpots, 1)
        self.assertEqual(
            machine.balance, STARTING_BALANCE - DEFAULT_BET + 100 * DEFAULT_BET
        )

    def test_set_bet_ok(self):
        machine = SlotMachine()
        machine.set_bet(100)
        self.assertEqual(machine.bet, 100)

    def test_set_bet_too_low(self):
        machine = SlotMachine()
        with self.assertRaises(ValueError):
            machine.set_bet(MIN_BET - 1)

    def test_set_bet_too_high(self):
        machine = SlotMachine(balance=100_000)
        with self.assertRaises(ValueError):
            machine.set_bet(MAX_BET + 1)

    def test_set_bet_above_balance(self):
        machine = SlotMachine(balance=30)
        with self.assertRaises(ValueError):
            machine.set_bet(50)

    def test_reset(self):
        machine = SlotMachine(balance=12, bet=10)
        machine.stats.spins = 99
        machine.reset()
        self.assertEqual(machine.balance, STARTING_BALANCE)
        self.assertEqual(machine.bet, DEFAULT_BET)
        self.assertEqual(machine.stats.spins, 0)

    def test_random_symbol_always_valid(self):
        machine = SlotMachine(rng=random.Random(7))
        for _ in range(1000):
            self.assertIn(machine.random_symbol(), SYMBOLS)

    def test_generate_grid_shape(self):
        machine = SlotMachine(rng=random.Random(7))
        grid = machine.generate_grid()
        self.assertEqual(len(grid), 3)
        self.assertTrue(all(len(row) == 3 for row in grid))


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.json"
            machine = SlotMachine(balance=777, bet=25)
            machine.stats.spins = 3
            machine.stats.total_won = 500
            machine.save(path)

            loaded = SlotMachine.load(path)
            self.assertEqual(loaded.balance, 777)
            self.assertEqual(loaded.bet, 25)
            self.assertEqual(loaded.stats.spins, 3)
            self.assertEqual(loaded.stats.total_won, 500)

    def test_load_missing_file_gives_fresh_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            loaded = SlotMachine.load(Path(tmp) / "does-not-exist.json")
            self.assertEqual(loaded.balance, STARTING_BALANCE)
            self.assertEqual(loaded.bet, DEFAULT_BET)

    def test_load_corrupt_file_gives_fresh_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.json"
            path.write_text("this is not json", encoding="utf-8")
            loaded = SlotMachine.load(path)
            self.assertEqual(loaded.balance, STARTING_BALANCE)


class SqlitePersistenceTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.db"
            machine = SlotMachine(balance=777, bet=25)
            machine.stats.spins = 3
            machine.stats.total_won = 500
            machine.save(path)

            loaded = SlotMachine.load(path)
            self.assertEqual(loaded.balance, 777)
            self.assertEqual(loaded.bet, 25)
            self.assertEqual(loaded.stats.spins, 3)
            self.assertEqual(loaded.stats.total_won, 500)

    def test_load_missing_db_gives_fresh_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            loaded = SlotMachine.load(Path(tmp) / "does-not-exist.db")
            self.assertEqual(loaded.balance, STARTING_BALANCE)
            self.assertEqual(loaded.bet, DEFAULT_BET)

    def test_load_corrupt_db_gives_fresh_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.db"
            path.write_text("this is not a sqlite database", encoding="utf-8")
            loaded = SlotMachine.load(path)
            self.assertEqual(loaded.balance, STARTING_BALANCE)

    def test_save_overwrites_previous_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.db"
            SlotMachine(balance=100).save(path)
            machine = SlotMachine(balance=999, bet=77)
            machine.stats.spins = 5
            machine.save(path)

            loaded = SlotMachine.load(path)
            self.assertEqual(loaded.balance, 999)
            self.assertEqual(loaded.bet, 77)
            self.assertEqual(loaded.stats.spins, 5)

    def test_default_load_reads_sqlite(self):
        import slot_machine as sm

        with tempfile.TemporaryDirectory() as tmp:
            old_db, old_json = sm.SLOT_DB, sm.SLOT_JSON
            try:
                sm.SLOT_DB = Path(tmp) / "save.db"
                sm.SLOT_JSON = Path(tmp) / "save.json"
                SlotMachine(balance=4242).save()
                self.assertTrue(sm.SLOT_DB.exists())
                self.assertFalse(sm.SLOT_JSON.exists())

                loaded = SlotMachine.load()
                self.assertEqual(loaded.balance, 4242)
            finally:
                sm.SLOT_DB, sm.SLOT_JSON = old_db, old_json

    def test_default_load_migrates_legacy_json(self):
        import slot_machine as sm

        with tempfile.TemporaryDirectory() as tmp:
            old_db, old_json = sm.SLOT_DB, sm.SLOT_JSON
            try:
                sm.SLOT_DB = Path(tmp) / "save.db"
                sm.SLOT_JSON = Path(tmp) / "save.json"
                SlotMachine(balance=666, bet=15).save(sm.SLOT_JSON)
                self.assertFalse(sm.SLOT_DB.exists())

                loaded = SlotMachine.load()
                self.assertEqual(loaded.balance, 666)
                self.assertEqual(loaded.bet, 15)
                self.assertTrue(sm.SLOT_DB.exists())  # migrated to SQLite

                sm.SLOT_JSON.unlink()  # after migration JSON is not needed
                loaded2 = SlotMachine.load()
                self.assertEqual(loaded2.balance, 666)
            finally:
                sm.SLOT_DB, sm.SLOT_JSON = old_db, old_json

    def test_database_contains_expected_row(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.db"
            machine = SlotMachine(balance=123, bet=45)
            machine.stats.spins = 2
            machine.stats.jackpots = 1
            machine.save(path)

            conn = sqlite3.connect(str(path))
            try:
                row = conn.execute(
                    "SELECT balance, bet, spins, jackpots, updated_at "
                    "FROM saves WHERE id = 1"
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], 123)
                self.assertEqual(row[1], 45)
                self.assertEqual(row[2], 2)
                self.assertEqual(row[3], 1)
                self.assertTrue(row[4])
            finally:
                conn.close()


class RenderTests(unittest.TestCase):
    def test_render_grid_emoji(self):
        grid = grid_from(["cherry"] * 9)
        output = render_grid(grid, use_ascii=False)
        self.assertIn("🍒", output)
        self.assertEqual(len(output.splitlines()), 7)

    def test_render_grid_ascii(self):
        grid = grid_from(["cherry"] * 9)
        output = render_grid(grid, use_ascii=True)
        self.assertIn("C", output)
        self.assertIn("+", output)
        self.assertEqual(len(output.splitlines()), 7)

    def test_render_grid_highlight_keeps_line_count(self):
        grid = grid_from(["cherry"] * 9)
        output = render_grid(grid, color=True, highlight={(0, 0), (0, 1), (0, 2)})
        self.assertEqual(len(output.splitlines()), 7)

    def test_winning_cells(self):
        cherry = SYMBOL_BY_KEY["cherry"]
        result = SpinResult(
            grid=grid_from(["cherry"] * 9),
            wins=[LineWin(0, cherry, 3, 100)],
            total_win=100,
            balance=1000,
            jackpot=False,
        )
        self.assertEqual(winning_cells(result), {(0, 0), (0, 1), (0, 2)})

    def test_winning_cells_diagonal(self):
        cherry = SYMBOL_BY_KEY["cherry"]
        result = SpinResult(
            grid=grid_from(["cherry"] * 9),
            wins=[LineWin(3, cherry, 3, 100)],
            total_win=100,
            balance=1000,
            jackpot=False,
        )
        self.assertEqual(winning_cells(result), {(0, 0), (1, 1), (2, 2)})


if __name__ == "__main__":
    unittest.main()
