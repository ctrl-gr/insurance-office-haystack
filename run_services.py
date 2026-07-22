from __future__ import annotations

import socket
import subprocess
import sys
import time


SERVICES = [
    ("The Lion MCP", [sys.executable, "-m", "backend.mcp_servers.lion_server"], 5081),
    ("The Blue Company MCP", [sys.executable, "-m", "backend.mcp_servers.blue_server"], 5082),
    ("The Three Lines MCP", [sys.executable, "-m", "backend.mcp_servers.three_lines_server"], 5083),
    ("Insurance Conditions RAG MCP", [sys.executable, "-m", "backend.rag.server"], 5084),
    ("Insurance MCP Proxy", [sys.executable, "-m", "backend.mcp_proxy.server"], 5275),
    ("Haystack API", [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", "5100"], 5100),
]


def wait_for_port(name: str, port: int, process: subprocess.Popen, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited with code {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"{name} did not start on port {port}")


def main() -> None:
    processes: list[subprocess.Popen] = []
    try:
        for name, command, port in SERVICES:
            print(f"Starting {name} on port {port}...", flush=True)
            process = subprocess.Popen(command)
            processes.append(process)
            wait_for_port(name, port, process)
        print("All backend services are ready. Press Ctrl+C to stop.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
