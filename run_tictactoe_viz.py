"""
Launcher for Parallel MCTS Tic-Tac-Toe Visualizer
Serves the web application locally or opens it in your default browser.
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tictactoe_viz")

class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    index_path = os.path.join(DIRECTORY, "index.html")
    if not os.path.exists(index_path):
        print(f"Error: Could not find {index_path}")
        sys.exit(1)

    url = f"http://localhost:{PORT}/index.html"
    print("=" * 65)
    print(" Parallel MCTS Tic-Tac-Toe Visualizer")
    print("=" * 65)
    print(f"Serving visualization from: {DIRECTORY}")
    print(f"Opening browser at: {url}")
    print("Press Ctrl+C to stop the server.")
    print("=" * 65)

    try:
        webbrowser.open(url)
        server = HTTPServer(("127.0.0.1", PORT), CustomHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    except Exception as e:
        print(f"Could not bind server: {e}")
        print(f"Opening file directly: {index_path}")
        webbrowser.open(f"file:///{index_path}")

if __name__ == "__main__":
    main()
