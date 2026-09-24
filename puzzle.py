SIZE = 5
BLOCKS = [[0, 3], [0, 4], [4, 0], [4, 1]]

ACROSS = [
    {"num": 1, "row": 0, "col": 0, "len": 3, "answer": "EAR", "clue": "Where you whisper sweet nothings"},
    {"num": 4, "row": 1, "col": 0, "len": 5, "answer": "DRAWN", "clue": "Pulled, like curtains at movie night"},
    {"num": 7, "row": 2, "col": 0, "len": 5, "answer": "GENRE", "clue": "Rom-com or horror, for instance"},
    {"num": 8, "row": 3, "col": 0, "len": 5, "answer": "EAGER", "clue": "How you feel for date night"},
    {"num": 9, "row": 4, "col": 2, "len": 3, "answer": "END", "clue": "Where happily-ever-after leads"},
]

DOWN = [
    {"num": 1, "row": 0, "col": 0, "len": 4, "answer": "EDGE", "clue": "Sofa spot you fight over during scary movies"},
    {"num": 2, "row": 0, "col": 1, "len": 4, "answer": "AREA", "clue": "Your shared living space"},
    {"num": 3, "row": 0, "col": 2, "len": 5, "answer": "RANGE", "clue": "What your voices cover during karaoke night"},
    {"num": 5, "row": 1, "col": 3, "len": 4, "answer": "WREN", "clue": "A small songbird"},
    {"num": 6, "row": 1, "col": 4, "len": 4, "answer": "NERD", "clue": "What you both are about this game"},
]

def build_solution_grid():
    grid = [[None] * SIZE for _ in range(SIZE)]
    for r, c in BLOCKS:
        grid[r][c] = "#"
    for e in ACROSS:
        for i, ch in enumerate(e["answer"]):
            grid[e["row"]][e["col"] + i] = ch
    for e in DOWN:
        for i, ch in enumerate(e["answer"]):
            grid[e["row"] + i][e["col"]] = ch
    return grid

def build_numbers_grid():
    nums = [[None] * SIZE for _ in range(SIZE)]
    for e in ACROSS:
        nums[e["row"]][e["col"]] = e["num"]
    for e in DOWN:
        nums[e["row"]][e["col"]] = e["num"]
    return nums

SOLUTION = build_solution_grid()
NUMBERS = build_numbers_grid()

def is_block(r, c):
    return [r, c] in BLOCKS

def puzzle_payload():
    """What the client needs to render the empty grid + clues (no answers)."""
    return {
        "size": SIZE,
        "blocks": BLOCKS,
        "numbers": NUMBERS,
        "across": [{"num": e["num"], "clue": e["clue"], "row": e["row"], "col": e["col"], "len": e["len"]} for e in ACROSS],
        "down": [{"num": e["num"], "clue": e["clue"], "row": e["row"], "col": e["col"], "len": e["len"]} for e in DOWN],
    }
