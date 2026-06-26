# MCP live bridge for the KLayout GUI.
#
# Run this *inside* a running KLayout application so the klayout-draw-mcp server can
# edit the layout you already have loaded, instead of regenerating and reloading a file.
# Easiest path: ask the assistant to call the `gui_bridge_macro` tool, paste the output
# into KLayout's Macro IDE (F5 -> new Python macro) and Run it. Or launch KLayout with
# `klayout -rm <path-to-this-file> my_layout.gds`.
#
# Protocol (loopback only by default): each request and response is a 4-byte big-endian
# length prefix followed by a UTF-8 JSON object.
#   request  : {"code": "<python>"}
#   response : {"ok": bool, "stdout": str, "error": str|null, "traceback": str|null}
#
# Received code runs on KLayout's main (GUI) thread with these names injected:
#   pya       - the KLayout GUI Python module
#   view      - the current pya.LayoutView (or None)
#   cv        - the active pya.CellView (or None)
#   layout    - the current pya.Layout (or None)
#   cell      - the current pya.Cell, i.e. the cell shown in the view (or None)
#   refresh() - redraw the view (called automatically after every request)
# A persistent globals dict is reused across requests, so variables you set in one call
# are still available in the next.

import io
import json
import socket
import struct
import threading
import traceback
from contextlib import redirect_stdout

import pya

HOST = "127.0.0.1"
PORT = 8082

# Work is queued from the socket threads and drained on the GUI main thread by a timer.
# KLayout's QTimer can miss repeating timeouts, so we use a self-re-arming single-shot
# timer (the documented workaround) and connect the slot by assignment — pya signals do
# not support .connect().
_queue = []
_qlock = threading.Lock()
_globals = {"pya": pya}
_timer = None  # kept as a module global so it is not garbage-collected


def _refresh(view):
    """Make newly added shapes / layers visible in the view."""
    if view is None:
        return
    for call in ("add_missing_layers", "update_content"):
        try:
            getattr(view, call)()
        except Exception:
            pass


def _exec_on_main(code):
    """Execute one request on the GUI main thread. Returns a response dict."""
    view = pya.LayoutView.current()
    g = _globals
    g["pya"] = pya
    g["view"] = view
    cv = view.active_cellview() if view is not None else None
    valid = cv is not None and cv.is_valid()
    g["cv"] = cv
    g["layout"] = cv.layout() if valid else None
    g["cell"] = cv.cell if valid else None
    g["refresh"] = lambda: _refresh(view)

    buf = io.StringIO()
    resp = {"ok": True, "stdout": "", "error": None, "traceback": None}
    try:
        with redirect_stdout(buf):
            exec(code, g)
    except Exception as e:  # noqa: BLE001 - report any error back to the caller
        resp["ok"] = False
        resp["error"] = "".join(traceback.format_exception_only(type(e), e)).strip()
        resp["traceback"] = traceback.format_exc()
    resp["stdout"] = buf.getvalue()
    _refresh(view)
    return resp


def _on_tick():
    """Runs on the main thread: execute all pending requests, then re-arm the timer."""
    try:
        with _qlock:
            items = _queue[:]
            _queue.clear()
        for code, holder, ev in items:
            try:
                holder.append(_exec_on_main(code))
            except Exception as e:  # noqa: BLE001
                holder.append(
                    {"ok": False, "stdout": "", "error": repr(e), "traceback": traceback.format_exc()}
                )
            ev.set()
    finally:
        _timer.start(50)  # re-arm (robust against KLayout's missed repeating timeouts)


def _recv_exactly(sock, n):
    chunks = []
    while n > 0:
        b = sock.recv(n)
        if not b:
            return None
        chunks.append(b)
        n -= len(b)
    return b"".join(chunks)


def _handle(conn):
    with conn:
        while True:
            header = _recv_exactly(conn, 4)
            if header is None:
                return
            (length,) = struct.unpack(">I", header)
            body = _recv_exactly(conn, length)
            if body is None:
                return
            try:
                code = json.loads(body.decode("utf-8")).get("code", "")
            except Exception as e:  # noqa: BLE001
                resp = {"ok": False, "stdout": "", "error": f"bad request: {e}", "traceback": None}
            else:
                holder, ev = [], threading.Event()
                with _qlock:
                    _queue.append((code, holder, ev))
                ev.wait()
                resp = holder[0]
            payload = json.dumps(resp).encode("utf-8")
            conn.sendall(struct.pack(">I", len(payload)) + payload)


def _serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(4)
    print(f"[mcp_live_bridge] listening on {HOST}:{PORT}")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


def start():
    """Start the main-thread drain timer and the socket server."""
    global _timer
    _timer = pya.QTimer()
    _timer.setSingleShot(True)
    _timer.timeout = _on_tick  # pya connects a signal by assignment, not .connect()
    _timer.start(50)
    threading.Thread(target=_serve, daemon=True).start()
    print("[mcp_live_bridge] ready - the klayout-draw-mcp gui_exec tool can now connect")


start()
