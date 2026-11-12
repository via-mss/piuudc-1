# piuudc-1
Programmatūras izstrādes un uzturēšanas dzīves cikls 1. repo.

## Šeit mēs darām lektora urbāna uzdotos uzdevumus.

Šeit būs random komentāri

 cucumber
 bread
juice
sweets
kaput

## Slots Machine (cmd)

A working command-line slot machine written in pure Python 3 (no external
dependencies). Progress is persisted in an SQLite database
(`slots_save.db`, auto-generated, ignored by git); the old
`slots_save.json` format is still read if present and migrated to SQLite
on first load.

### How to run

```bat
py slot_machine.py
```

or on Linux/macOS:

```sh
python3 slot_machine.py
```

### Options

```
--demo N      Run N demo spins non-interactively and exit (default 10)
--ascii       Plain ASCII symbols/borders (for old Windows cmd.exe)
--no-color    Disable colored output
--no-animation Disable the spinning animation
--reset       Delete the save database and start fresh
--no-save     Don't load or save progress
```

### Controls

| Command          | Action                                    |
|------------------|-------------------------------------------|
| spin / Enter     | Spin the reels                            |
| bet <amount>     | Set bet (min 10, max 1000)                |
| balance          | Show balance                              |
| payouts          | Show payout table                         |
| stats            | Show session stats / RTP                   |
| auto <n>         | Spin n times automatically                |
| reset            | Restart with 1000 fresh credits           |
| quit             | Save and exit                             |

### Payouts

- 🍒 Cherry 3-of-a-kind ×2, 🍋 Lemon ×3, 🍇 Grapes ×4, ⭐ Star ×6, 💎 Diamond ×15
- 7 Lucky Seven 3-of-a-kind ×100 (jackpot)
- Any pair on the first two reels of a line pays bet/10
- 5 paylines: 3 rows + 2 diagonals; wins on different lines add up

### Persistence

Progress (balance, bet, lifetime stats) is saved to an SQLite database
after every spin / auto-play / reset and on exit, and restored on the
next run. `--reset` deletes the database; `--no-save` ignores it
entirely. A legacy `slots_save.json` is read once and migrated into the
database.

### Tests

```sh
python -m unittest test_slot_machine -v
```

