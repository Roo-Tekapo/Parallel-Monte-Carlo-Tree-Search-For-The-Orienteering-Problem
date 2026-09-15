"""
Launcher for Parallel MCTS Orienteering Problem Visualizer
Serves the web application locally with benchmark API and opens it in your default browser.
"""

import os
import sys
import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8081
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
VIZ_DIR = os.path.join(ROOT_DIR, "orienteering_viz")
BENCH_DIR = os.path.join(ROOT_DIR, "OP_Benchmark_Set")

class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=VIZ_DIR, **kwargs)

    def do_GET(self):
        # API endpoint to list all available benchmark files in OP_Benchmark_Set
        if self.path == "/api/benchmarks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            benchmarks = []
            if os.path.exists(BENCH_DIR):
                for root, dirs, files in os.walk(BENCH_DIR):
                    for file in files:
                        if file.endswith(".txt"):
                            rel_path = os.path.relpath(os.path.join(root, file), BENCH_DIR)
                            benchmarks.append({
                                "filename": file,
                                "relativePath": rel_path.replace("\\", "/"),
                                "category": os.path.basename(root)
                            })
            self.wfile.write(json.dumps(benchmarks).encode("utf-8"))
            return

        # API endpoint to retrieve raw benchmark text from OP_Benchmark_Set
        if self.path.startswith("/api/benchmark?path="):
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(self.path).query)
            target_rel = query.get("path", [None])[0]
            if target_rel:
                safe_path = os.path.normpath(os.path.join(BENCH_DIR, target_rel))
                if safe_path.startswith(BENCH_DIR) and os.path.exists(safe_path):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    with open(safe_path, "r", encoding="utf-8") as f:
                        self.wfile.write(f.read().encode("utf-8"))
                    return
            self.send_response(404)
            self.end_headers()
            return

        super().do_GET()

    def do_POST(self):
        # API endpoint to solve problem with Google OR-Tools
        if self.path == "/api/solve_ortools":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                req = json.loads(body)

                time_limit = int(req.get("timeLimit", 5))
                nodes_data = req.get("nodes", [])
                budget = float(req.get("budget", 20.0))

                sys.path.append(ROOT_DIR)
                from OR_Tool.or_tools_solver import ORToolsOrienteeringSolver
                from orienteering.orienteering import OrienteeringProblem, Node

                nodes = [Node(n["id"], float(n["x"]), float(n["y"]), float(n["score"])) for n in nodes_data]
                problem = OrienteeringProblem(nodes, budget)

                solver = ORToolsOrienteeringSolver(problem, time_limit_seconds=time_limit)
                path, reward, distance, stats = solver.solve(verbose=False)

                resp_data = {
                    "success": True,
                    "path": path,
                    "score": reward,
                    "cost": distance,
                    "stats": stats,
                    "solver": "Google OR-Tools"
                }
            except Exception as e:
                resp_data = {
                    "success": False,
                    "error": str(e)
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resp_data).encode("utf-8"))
            return

        super().do_POST()

def main():
    index_path = os.path.join(VIZ_DIR, "index.html")
    if not os.path.exists(index_path):
        print(f"Error: Could not find {index_path}")
        sys.exit(1)

    url = f"http://localhost:{PORT}/index.html"
    print("=" * 65)
    print(" Parallel MCTS Orienteering Problem Visualizer")
    print("=" * 65)
    print(f"Serving visualization from: {VIZ_DIR}")
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
        print(f"Could not bind server on port {PORT}: {e}")
        print(f"Opening file directly: {index_path}")
        webbrowser.open(f"file:///{index_path}")

if __name__ == "__main__":
    main()
