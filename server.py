import os
from flask import Flask, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

from puzzle import SIZE, BLOCKS, SOLUTION, is_block, puzzle_payload

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["SECRET_KEY"] = "duo-crossword"
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# In-memory shared state -- this app is designed for exactly one small
# shared game between two people, so a single global room is enough.
state = {
      "cells": [[""] * SIZE for _ in range(SIZE)],
      "solved": False,
}
players = {}  # sid -> name
COLORS = ["#ff6b9d", "#4ecdc4"]


@app.route("/")
def index():
      return send_from_directory(app.static_folder, "index.html")


@app.route("/api/puzzle")
def api_puzzle():
      return jsonify(puzzle_payload())


@socketio.on("connect")
def on_connect():
      emit("state", {"cells": state["cells"], "solved": state["solved"]})
      emit("players", list(players.values()), broadcast=True)


@socketio.on("join")
def on_join(data):
      from flask import request
      name = (data or {}).get("name", "Player")[:20] or "Player"
      color = COLORS[len(players) % len(COLORS)]
      players[request.sid] = {"name": name, "color": color}
      emit("players", list(players.values()), broadcast=True)


@socketio.on("disconnect")
def on_disconnect():
      from flask import request
      players.pop(request.sid, None)
      emit("players", list(players.values()), broadcast=True)


@socketio.on("cell_input")
def on_cell_input(data):
      r, c, ch = data.get("row"), data.get("col"), (data.get("value") or "").upper()[:1]
      if r is None or c is None or not (0 <= r < SIZE and 0 <= c < SIZE) or is_block(r, c):
                return
            state["cells"][r][c] = ch
    solved = all(
              state["cells"][r][c] == SOLUTION[r][c]
              for r in range(SIZE) for c in range(SIZE)
              if not is_block(r, c)
    )
    state["solved"] = solved
    emit("cell_update", {"row": r, "col": c, "value": ch, "solved": solved}, broadcast=True)


@socketio.on("cursor_move")
def on_cursor_move(data):
      from flask import request
    emit("cursor_update", {"sid": request.sid, **data}, broadcast=True, include_self=False)


@socketio.on("reset")
def on_reset():
      state["cells"] = [[""] * SIZE for _ in range(SIZE)]
    state["solved"] = False
    emit("state", {"cells": state["cells"], "solved": False}, broadcast=True)


if __name__ == "__main__":
      port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("DEBUG") == "1"
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
