"""Deterministic daily 5x5 mini crossword.

Grid pattern (# = black square):

    . . . # #
    . . . . #
    . . . . .
    # . . . .
    # # . . .

Every white square belongs to both an across and a down entry, so any letter
can always be confirmed from its crossing word.

The grid is filled by seeded backtracking search over the curated word bank in
clues.py. The seed comes from the date, so everyone opening the site on the
same day gets the same puzzle without anything being stored.
"""
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from clues import CLUES

SIZE = 5
BLOCKS = [[0, 3], [0, 4], [1, 4], [3, 0], [4, 0], [4, 1]]
TIMEZONE = ZoneInfo("America/New_York")

_BLOCK_SET = {(r, c) for r, c in BLOCKS}

WORDS_BY_LEN = {}
for _word in CLUES:
    WORDS_BY_LEN.setdefault(len(_word), set()).add(_word)
WORDS_BY_LEN = {n: frozenset(words) for n, words in WORDS_BY_LEN.items()}

# (length, position, letter) -> every word of that length with that letter there.
# Candidate lookup is then a set intersection instead of a full scan.
_INDEX = {}
for _length, _words in WORDS_BY_LEN.items():
    for _word in _words:
        for _i, _ch in enumerate(_word):
            _INDEX.setdefault((_length, _i, _ch), set()).add(_word)
_INDEX = {_k: frozenset(_v) for _k, _v in _INDEX.items()}
_EMPTY = frozenset()


def is_block(r, c):
    return (r, c) in _BLOCK_SET


def _build_slots():
    """Find every across/down run of 2+ cells and assign crossword numbers."""
    across, down = [], []
    number = 0
    for r in range(SIZE):
        for c in range(SIZE):
            if is_block(r, c):
                continue
            open_left = c > 0 and not is_block(r, c - 1)
            open_right = c + 1 < SIZE and not is_block(r, c + 1)
            open_above = r > 0 and not is_block(r - 1, c)
            open_below = r + 1 < SIZE and not is_block(r + 1, c)
            starts_across = not open_left and open_right
            starts_down = not open_above and open_below
            if not (starts_across or starts_down):
                continue
            number += 1
            if starts_across:
                cells = []
                cc = c
                while cc < SIZE and not is_block(r, cc):
                    cells.append((r, cc))
                    cc += 1
                across.append({"num": number, "row": r, "col": c, "cells": cells})
            if starts_down:
                cells = []
                rr = r
                while rr < SIZE and not is_block(rr, c):
                    cells.append((rr, c))
                    rr += 1
                down.append({"num": number, "row": r, "col": c, "cells": cells})
    return across, down


ACROSS_SLOTS, DOWN_SLOTS = _build_slots()
ALL_SLOTS = ACROSS_SLOTS + DOWN_SLOTS


def _fill(rng):
    """Fill every slot with a distinct word, using MRV backtracking."""
    letters = {}
    used = set()
    remaining = list(range(len(ALL_SLOTS)))

    def candidates(slot):
        length = len(slot["cells"])
        pool = None
        for i, cell in enumerate(slot["cells"]):
            ch = letters.get(cell)
            if ch is None:
                continue
            matches = _INDEX.get((length, i, ch))
            if not matches:
                return _EMPTY
            pool = matches if pool is None else pool & matches
            if not pool:
                return _EMPTY
        if pool is None:
            pool = WORDS_BY_LEN[length]
        return pool - used

    def backtrack():
        if not remaining:
            return True
        best_i, best_cands = None, None
        for i in remaining:
            cands = candidates(ALL_SLOTS[i])
            if best_cands is None or len(cands) < len(best_cands):
                best_i, best_cands = i, cands
                if len(cands) <= 1:
                    break
        if not best_cands:
            return False
        # Sort first: set iteration order depends on the per-process hash seed,
        # so shuffling the raw set would give a different puzzle every restart.
        words = sorted(best_cands)
        rng.shuffle(words)
        slot = ALL_SLOTS[best_i]
        remaining.remove(best_i)
        for word in words:
            saved = {cell: letters.get(cell) for cell in slot["cells"]}
            for cell, ch in zip(slot["cells"], word):
                letters[cell] = ch
            used.add(word)
            # Forward check: bail early if any open slot now has no options.
            if all(candidates(ALL_SLOTS[j]) for j in remaining) and backtrack():
                return True
            used.discard(word)
            for cell, prev in saved.items():
                if prev is None:
                    letters.pop(cell, None)
                else:
                    letters[cell] = prev
        remaining.append(best_i)
        return False

    return letters if backtrack() else None


def _generate(day):
    """Build the puzzle for an ISO date string. Retries seeds until one fills."""
    for attempt in range(50):
        rng = random.Random(f"{day}#{attempt}")
        letters = _fill(rng)
        if letters is None:
            continue

        solution = [[None] * SIZE for _ in range(SIZE)]
        for (r, c), ch in letters.items():
            solution[r][c] = ch
        for r, c in BLOCKS:
            solution[r][c] = "#"

        numbers = [[None] * SIZE for _ in range(SIZE)]
        for slot in ALL_SLOTS:
            numbers[slot["row"]][slot["col"]] = slot["num"]

        def entries(slots):
            out = []
            for slot in slots:
                word = "".join(letters[cell] for cell in slot["cells"])
                out.append({
                    "num": slot["num"],
                    "clue": CLUES[word],
                    "row": slot["row"],
                    "col": slot["col"],
                    "len": len(slot["cells"]),
                })
            return sorted(out, key=lambda e: e["num"])

        return {
            "date": day,
            "size": SIZE,
            "blocks": BLOCKS,
            "numbers": numbers,
            "solution": solution,
            "across": entries(ACROSS_SLOTS),
            "down": entries(DOWN_SLOTS),
        }
    raise RuntimeError(f"could not generate a puzzle for {day}")


_cache = {}


def today():
    return datetime.now(TIMEZONE).date().isoformat()


def get_puzzle(day=None):
    day = day or today()
    if day not in _cache:
        # Only today's puzzle is ever needed, so don't let old days pile up.
        _cache.clear()
        _cache[day] = _generate(day)
    return _cache[day]


def puzzle_payload(day=None):
    """What the client needs to render the empty grid + clues (no answers)."""
    puzzle = get_puzzle(day)
    return {k: v for k, v in puzzle.items() if k != "solution"}
