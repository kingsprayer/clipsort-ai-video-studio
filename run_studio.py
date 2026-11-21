#!/usr/bin/env python3
"""
================================================================================
⚡ CLIPSORT AI — UNIVERSAL PYTHON STUDIO LAUNCHER & DEPLOYER
================================================================================
Cross-platform, self-bootstrapping Python launcher for ClipSort AI Studio.
Automatically handles virtual environments, dependencies, FFmpeg discovery,
and starts the local web server on port 5005.

Usage:
  python run_studio.py
  python run_studio.py --port 5005
  python run_studio.py --open
================================================================================
"""

import os
import sys
import glob
import time
import shutil
import socket
import signal
import argparse
import subprocess
import webbrowser

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# 1. Self-Bootstrap: Ensure execution inside .venv or with required modules
def ensure_virtualenv():
    # If already running inside virtualenv or has required modules, continue
    try:
        import flask
        import cv2
        return
    except ImportError:
        pass

    # Dynamic search for Python environments
    candidate_venvs = [
        os.path.join(SCRIPT_DIR, ".venv", "bin", "python"),
        os.path.join(SCRIPT_DIR, ".venv", "bin", "python3"),
        os.path.join(SCRIPT_DIR, ".venv", "bin", "python3.11"),
        os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe"),
        os.path.expanduser("~/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3"),
        os.path.expanduser("~/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11"),
        os.path.expanduser("~/.local/share/uv/python/cpython-3.11.16-macos-aarch64-none/bin/python3"),
    ]
    # Glob for any other UV-managed CPython installations
    candidate_venvs.extend(sorted(glob.glob(os.path.expanduser("~/.local/share/uv/python/*/bin/python3*")), reverse=True))
    candidate_venvs.extend([
        os.path.expanduser("~/.local/bin/python3"),
        os.path.expanduser("~/.local/bin/python"),
    ])

    for py in candidate_venvs:
        if os.path.exists(py) and os.access(py, os.X_OK):
            try:
                # Test if candidate python has flask
                test_res = subprocess.run([py, "-c", "import flask; import cv2"], capture_output=True)
                if test_res.returncode == 0:
                    os.environ["VIRTUAL_ENV"] = os.path.dirname(os.path.dirname(py))
                    os.environ["PATH"] = f"{os.path.dirname(py)}:{os.environ.get('PATH', '')}"
                    os.execv(py, [py] + sys.argv)
            except Exception:
                continue

    # Fallback to direct exec if .venv binary exists
    local_venv_py = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
    if os.path.exists(local_venv_py) and os.access(local_venv_py, os.X_OK):
        os.environ["VIRTUAL_ENV"] = os.path.join(SCRIPT_DIR, ".venv")
        os.environ["PATH"] = f"{os.path.join(SCRIPT_DIR, '.venv', 'bin')}:{os.environ.get('PATH', '')}"
        os.execv(local_venv_py, [local_venv_py] + sys.argv)

    print("[Error] Required packages (flask, cv2) not found and usable .venv python was not found.")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

ensure_virtualenv()

# 2. Add FFmpeg and tools to PATH
for bin_dir in [
    os.path.expanduser("~/.local/bin"),
    os.path.join(SCRIPT_DIR, ".venv", "bin"),
    "/opt/homebrew/bin",
    "/usr/local/bin"
]:
    if os.path.exists(bin_dir) and bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"

# 3. Suppress duplicate library noise if present
os.environ.setdefault("PYTHONWARNINGS", "ignore")

def release_port(port: int):
    """Checks if port is in use and gracefully terminates the stale process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", port)) != 0:
            return  # Port is already free

    print(f"[Launcher] Port {port} is currently in use. Releasing port for clean deployment...")
    try:
        res = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        pids = [int(p) for p in res.stdout.strip().split() if p.isdigit()]
        for pid in pids:
            if pid != os.getpid():
                print(f"  • Terminating stale server process (PID {pid})...")
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        time.sleep(1.2)
    except Exception as e:
        print(f"[Launcher Warning] Could not release port {port}: {e}")

def main():
    parser = argparse.ArgumentParser(description="ClipSort AI — Local Studio Deployment")
    parser.add_argument("--port", "-p", type=int, default=int(os.environ.get("PORT", 5005)), help="Port to bind (default: 5005)")
    parser.add_argument("--host", "-H", type=str, default=os.environ.get("HOST", "0.0.0.0"), help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--open", "-o", action="store_true", help="Automatically open the studio in your default browser")
    parser.add_argument("--no-kill", action="store_true", help="Do not attempt to kill stale process on port")
    args = parser.parse_args()

    # Free up port if stale process is holding it
    if not args.no_kill:
        release_port(args.port)

    # Import Master Engine
    try:
        from clipsort_engine_master import app, OUTPUT_DIR, STATE, CATEGORIES, refresh_state_counts
    except ImportError as e:
        print(f"[Fatal] Failed to import clipsort_engine_master: {e}")
        sys.exit(1)

    refresh_state_counts()
    url = f"http://localhost:{args.port}"

    print("\n" + "=" * 68)
    print("⚡  CLIPSORT AI — MASTER STUDIO DEPLOYED ON LOCALHOST")
    print("=" * 68)
    print(f"  • Web Studio URL : \033[1;32m{url}\033[0m")
    print(f"  • Host / Port    : {args.host}:{args.port}")
    print(f"  • Workspace Dir  : {SCRIPT_DIR}")
    print(f"  • Output Dir     : {OUTPUT_DIR}")
    print(f"  • Active Categories : {len(CATEGORIES)} ({', '.join(CATEGORIES)})")
    print(f"  • Loaded Clips   : {len(STATE.get('results', []))} clips")
    print("=" * 68)
    print(f"👉 Open in browser : {url}\n")
    print("Press Ctrl+C to stop the studio server.\n")

    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()
