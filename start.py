#!/usr/bin/env python3
"""
Quick-start script for local development.

Usage:
  python start.py backend    # starts FastAPI on :8000
  python start.py frontend   # starts Streamlit on :8501
  python start.py both       # starts both (two processes)
  python start.py test       # runs pytest
"""
import sys
import subprocess
import os


def run_backend():
    print("Starting FastAPI backend on http://localhost:8000 ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ], env=env)


def run_frontend():
    print("Starting Streamlit frontend on http://localhost:8501 ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "frontend/app.py",
        "--server.port", "8501",
    ], env=env)


def run_tests():
    print("Running unit tests ...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "backend"

    if mode == "backend":
        run_backend()
    elif mode == "frontend":
        run_frontend()
    elif mode == "both":
        import multiprocessing
        b = multiprocessing.Process(target=run_backend)
        f = multiprocessing.Process(target=run_frontend)
        b.start()
        f.start()
        b.join()
        f.join()
    elif mode == "test":
        run_tests()
    else:
        print(__doc__)
        sys.exit(1)
