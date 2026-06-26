# Installation &amp; Setup

This page covers installing the server and connecting it to an MCP client
(Claude Code or Claude Desktop). The server speaks MCP over **stdio** — the client
launches it for you, so you normally never run it by hand.

## Requirements

- **Python ≥ 3.10**
- The `klayout` and `mcp` Python packages (installed automatically with the server)
- The [KLayout application](https://www.klayout.de/build.html) — **optional**, only needed
  for `open_layout` / `open_editor` (drawing, saving and DRC all work without it)

## 1. Install the server

=== "uv / uvx (recommended)"

    Run it without installing anything, straight from PyPI:

    ```bash
    uvx klayout-draw-mcp        # downloads and runs in an isolated environment
    ```

    `uvx` is ideal for MCP clients because the command is self-contained.

=== "pip"

    ```bash
    pip install klayout-draw-mcp
    ```

    This puts a `klayout-draw-mcp` console script on your `PATH`.

=== "From a checkout"

    ```bash
    git clone https://github.com/geniuskey/klayout-draw-mcp
    cd klayout-draw-mcp
    uv sync
    ```

    The interpreter is then `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python`
    (macOS/Linux), and you run the module with `python -m klayout_draw_mcp.server`.

## 2. Connect to Claude Code

Use `claude mcp add`. Pick the form that matches how you installed it:

```bash
# uvx — no prior install needed
claude mcp add klayout -s user -- uvx klayout-draw-mcp

# pip install (console script on PATH)
claude mcp add klayout -s user -- klayout-draw-mcp

# from a checkout
claude mcp add klayout -s user -- /path/to/repo/.venv/bin/python -m klayout_draw_mcp.server
```

`-s user` registers it for all your projects. Check it with `/mcp` inside Claude Code —
`klayout` should be listed with its tools.

## 3. Connect to Claude Desktop

Edit `claude_desktop_config.json` and add a server under `mcpServers`:

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-draw-mcp"]
    }
  }
}
```

The config file lives at:

| OS | Path |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

If you installed with pip instead of uvx, use `"command": "klayout-draw-mcp"` with
`"args": []`. **Restart Claude Desktop** after editing the file. On Windows, prefer
forward slashes in any paths, or escape backslashes (`\\`) in JSON.

## 4. Connect to OpenCode

[OpenCode](https://opencode.ai) is a terminal-based AI coding agent that also supports MCP.
Add the server to your project's `opencode.json` (or `~/.config/opencode/config.json` for global registration):

=== "uvx (recommended)"

    ```json
    {
      "$schema": "https://opencode.ai/config.json",
      "mcp": {
        "klayout": {
          "type": "local",
          "command": ["uvx", "klayout-draw-mcp"],
          "enabled": true
        }
      }
    }
    ```

=== "pip"

    ```json
    {
      "$schema": "https://opencode.ai/config.json",
      "mcp": {
        "klayout": {
          "type": "local",
          "command": ["python", "-m", "klayout_draw_mcp.server"],
          "enabled": true
        }
      }
    }
    ```

=== "From a checkout"

    ```json
    {
      "$schema": "https://opencode.ai/config.json",
      "mcp": {
        "klayout": {
          "type": "local",
          "command": ["/path/to/repo/.venv/bin/python", "-m", "klayout_draw_mcp.server"],
          "enabled": true
        }
      }
    }
    ```

    On Windows use `.venv\Scripts\python.exe` instead.

Place `opencode.json` in your project root for per-project registration, or in
`~/.config/opencode/config.json` to make it available globally. After saving the
file, run `opencode` in the terminal — the `klayout` MCP server will be loaded
automatically and its tools will be available to the assistant.

## 5. Install the KLayout application (optional)

Only `open_layout` and `open_editor` launch the GUI; everything else uses the in-process
`klayout.db` module. Install the app from [klayout.de](https://www.klayout.de/build.html).
The server finds it via `PATH` (`klayout`), the macOS `open -a KLayout`, or these default
Windows locations:

```
%APPDATA%\KLayout\klayout_app.exe
%ProgramFiles%\KLayout\klayout_app.exe
%LOCALAPPDATA%\Programs\KLayout\klayout_app.exe
```

## 6. Verify the connection

In Claude Code, `/mcp` should show `klayout`. Then try a prompt:

> "Draw a 5×5 µm box on layer 1, save to out.gds and open it."

The assistant should call `new_layout` → `add_box` → `save_gds`. Walk through the rest on
the [Getting Started](getting-started.md) page.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `klayout-draw-mcp: command not found` | The console script isn't on `PATH`. Use `uvx klayout-draw-mcp`, or point the client at `python -m klayout_draw_mcp.server` with a full interpreter path. |
| Server shows as **failed** in the client | Run the exact command yourself in a terminal — it should start and wait silently on stdio. Any traceback printed there is the real error (often a wrong Python or missing install). |
| "KLayout application not found" | Only affects `open_layout` / `open_editor`. Install the app and ensure it's on `PATH` or a default location above. Saving GDS still works. |
| Running the command "hangs" | That's correct — an stdio MCP server waits for a client. Don't run it directly; let Claude launch it. |
| Coordinates look 1000× off | All tool coordinates are **micrometers**; the database grid defaults to `dbu = 0.001` (1 nm). |
