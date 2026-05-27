#!/usr/bin/env python3
"""Local preview server for a user-journey workspace.

Most browsers can open index.html directly via file:// because journey data
and design tokens are inlined into the HTML. If, however, you edit
journey.json or DESIGN.md and the browser is configured to block local
fetch() calls, this script starts a tiny HTTP server so render.js can
re-read the latest files.

Usage:
    cd <workspace>
    python3 preview.py            # serve current dir at http://localhost:8765
    python3 preview.py --port 9000
    python3 preview.py --no-open  # do not auto-open the browser

Requires only the Python 3.10+ standard library. Press Ctrl+C to stop.
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
import webbrowser
from pathlib import Path


def serve(root: Path, port: int, open_browser: bool) -> int:
    if not (root / "index.html").exists():
        print(f"error: no index.html found in {root}", file=sys.stderr)
        return 2

    handler_cls = type(
        "Handler",
        (http.server.SimpleHTTPRequestHandler,),
        {"directory": str(root)},
    )

    socketserver.TCPServer.allow_reuse_address = True
    try:
        server = socketserver.TCPServer(("127.0.0.1", port), handler_cls)
    except OSError as exc:
        print(f"error: cannot bind to port {port}: {exc}", file=sys.stderr)
        return 1

    url = f"http://localhost:{port}/"
    print(f"Serving {root} at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="port to serve on (default: 8765)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="do not auto-open the browser",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="workspace directory to serve (default: current dir)",
    )
    args = parser.parse_args()

    root = Path(args.dir).expanduser().resolve()
    sys.exit(serve(root, args.port, not args.no_open))


if __name__ == "__main__":
    main()
