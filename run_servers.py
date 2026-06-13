import os
import subprocess
import sys
import time

def run_backend():
    print("🚀 Starting FastAPI backend on http://localhost:8000 ...")
    cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    return subprocess.Popen(cmd)

def run_frontend():
    print("🚀 Starting Vite frontend on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    # Ensure npm install is run first if node_modules doesn't exist
    if not os.path.exists(os.path.join("frontend", "node_modules")):
        print("📦 Installing frontend dependencies...")
        subprocess.run([npm_cmd, "install"], cwd="frontend")
    
    cmd = [npm_cmd, "run", "dev"]
    return subprocess.Popen(cmd, cwd="frontend")

if __name__ == "__main__":
    print("=== Hand Gesture Recognition Platform ===")
    
    backend_process = None
    frontend_process = None
    
    try:
        backend_process = run_backend()
        frontend_process = run_frontend()
        
        print("\n✅ Servers are starting!")
        print("Backend API: http://localhost:8000/docs")
        print("Frontend UI: http://localhost:5173")
        print("\nPress Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    finally:
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
