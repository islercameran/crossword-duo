const socket = io();
let puzzle = null;
let myName = "";
let pendingState = null; // state that arrived before the puzzle finished loading
const inputs = {}; // "r-c" -> input element
const dots = {}; // "r-c" -> dot element

function key(r, c) { return `${r}-${c}`; }

async function loadPuzzle() {
  const res = await fetch("/api/puzzle");
  puzzle = await res.json();
  buildGrid();
  buildClues();
  showDate();
  if (pendingState) {
    const data = pendingState;
    pendingState = null;
    applyStateEvent(data);
  }
}

function showDate() {
  const [y, m, d] = puzzle.date.split("-").map(Number);
  document.getElementById("puzzle-date").textContent =
    new Date(y, m - 1, d).toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric",
    });
}

function isBlock(r, c) {
  return puzzle.blocks.some(([br, bc]) => br === r && bc === c);
}

function buildGrid() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  for (let r = 0; r < puzzle.size; r++) {
    for (let c = 0; c < puzzle.size; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      if (isBlock(r, c)) {
        cell.classList.add("block");
        grid.appendChild(cell);
        continue;
      }
      const num = puzzle.numbers[r][c];
      if (num) {
        const numEl = document.createElement("div");
        numEl.className = "num";
        numEl.textContent = num;
        cell.appendChild(numEl);
      }
      const input = document.createElement("input");
      input.maxLength = 1;
      input.dataset.row = r;
      input.dataset.col = c;
      input.addEventListener("input", onCellInput);
      input.addEventListener("keydown", onKeyDown);
      input.addEventListener("focus", () => {
        socket.emit("cursor_move", { row: r, col: c });
      });
      cell.appendChild(input);

      const dot = document.createElement("div");
      dot.className = "cursor-dot";
      dot.style.display = "none";
      cell.appendChild(dot);
      dots[key(r, c)] = dot;

      inputs[key(r, c)] = input;
      grid.appendChild(cell);
    }
  }
}

function buildClues() {
  const acrossList = document.getElementById("across-list");
  const downList = document.getElementById("down-list");
  acrossList.innerHTML = "";
  downList.innerHTML = "";
  for (const e of puzzle.across) {
    const li = document.createElement("li");
    li.innerHTML = `<b>${e.num}.</b> ${e.clue}`;
    acrossList.appendChild(li);
  }
  for (const e of puzzle.down) {
    const li = document.createElement("li");
    li.innerHTML = `<b>${e.num}.</b> ${e.clue}`;
    downList.appendChild(li);
  }
}

function onCellInput(ev) {
  const input = ev.target;
  const r = Number(input.dataset.row);
  const c = Number(input.dataset.col);
  const value = input.value.toUpperCase().slice(-1);
  input.value = value;
  socket.emit("cell_input", { row: r, col: c, value });
  if (value) focusNext(r, c);
}

function onKeyDown(ev) {
  const input = ev.target;
  const r = Number(input.dataset.row);
  const c = Number(input.dataset.col);
  if (ev.key === "Backspace" && !input.value) {
    focusPrev(r, c);
  } else if (ev.key === "ArrowRight") {
    focusCell(r, c + 1);
  } else if (ev.key === "ArrowLeft") {
    focusCell(r, c - 1);
  } else if (ev.key === "ArrowDown") {
    focusCell(r + 1, c);
  } else if (ev.key === "ArrowUp") {
    focusCell(r - 1, c);
  }
}

function focusCell(r, c) {
  const input = inputs[key(r, c)];
  if (input) input.focus();
}

function focusNext(r, c) {
  for (let nc = c + 1; nc < puzzle.size; nc++) {
    if (!isBlock(r, nc)) { focusCell(r, nc); return; }
  }
}

function focusPrev(r, c) {
  for (let pc = c - 1; pc >= 0; pc--) {
    if (!isBlock(r, pc)) { focusCell(r, pc); return; }
  }
}

function applyState(cells) {
  for (let r = 0; r < puzzle.size; r++) {
    for (let c = 0; c < puzzle.size; c++) {
      if (isBlock(r, c)) continue;
      const input = inputs[key(r, c)];
      if (input) input.value = cells[r][c] || "";
    }
  }
}

function showWin() {
  document.getElementById("win-screen").classList.remove("hidden");
}

function hideWin() {
  document.getElementById("win-screen").classList.add("hidden");
}

function applyStateEvent(data) {
  // The board rolls over at midnight ET; pick up the new puzzle and clues.
  if (data.date !== puzzle.date) {
    location.reload();
    return;
  }
  applyState(data.cells);
  if (data.solved) showWin(); else hideWin();
}

socket.on("state", (data) => {
  if (!puzzle) {
    pendingState = data;
    return;
  }
  applyStateEvent(data);
});

socket.on("cell_update", (data) => {
  const input = inputs[key(data.row, data.col)];
  if (input) {
    input.value = data.value;
    input.parentElement.classList.toggle("correct", false);
  }
  if (data.solved) showWin();
});

socket.on("players", (list) => {
  const el = document.getElementById("player-list");
  el.innerHTML = "";
  list.forEach((p, i) => {
    const chip = document.createElement("span");
    chip.className = "player-chip";
    chip.textContent = p.name;
    chip.style.background = p.color;
    el.appendChild(chip);
  });
});

socket.on("cursor_update", (data) => {
  Object.values(dots).forEach((d) => (d.style.display = "none"));
  const dot = dots[key(data.row, data.col)];
  if (dot) {
    dot.style.display = "block";
    dot.style.background = "#4ecdc4";
  }
});

// A tab left open overnight should pick up the new day when it's looked at again.
document.addEventListener("visibilitychange", async () => {
  if (document.hidden || !puzzle) return;
  const res = await fetch("/api/puzzle");
  const latest = await res.json();
  if (latest.date !== puzzle.date) location.reload();
});

document.getElementById("join-btn").addEventListener("click", join);
document.getElementById("name-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") join();
});
document.getElementById("reset-btn").addEventListener("click", () => {
  socket.emit("reset");
});

function join() {
  const input = document.getElementById("name-input");
  myName = input.value.trim() || "Player";
  socket.emit("join", { name: myName });
  document.getElementById("name-screen").classList.add("hidden");
}

loadPuzzle();
