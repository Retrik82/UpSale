import subprocess
import time
import sys
import re
import threading

frontend_url = None
backend_url = None

def run_tunnel(port, result_holder, index):
    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    for line in process.stdout:
        print(line, end="")
        if result_holder[0] is None:
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
            if match:
                result_holder[0] = match.group(0)

def main():
    print("Starting Cloudflare tunnels...\n")
    
    frontend_result = [None]
    backend_result = [None]
    
    t1 = threading.Thread(target=run_tunnel, args=(3000, frontend_result, 0))
    t2 = threading.Thread(target=run_tunnel, args=(8000, backend_result, 1))
    
    t1.start()
    t2.start()
    
    while frontend_result[0] is None or backend_result[0] is None:
        time.sleep(0.5)
    
    frontend_url = frontend_result[0]
    backend_url = backend_result[0]
    
    print(f"\n{'='*70}")
    print(f"Frontend URL: {frontend_url}")
    print(f"Backend URL:  {backend_url}")
    print(f"{'='*70}\n")
    
    with open("frontend/.env", "w") as f:
        f.write(f"API_URL={backend_url}\n")
    
    print("Updated frontend/.env")
    print(f"\nOpen frontend: {frontend_url}")
    print(f"API calls go to: {backend_url}\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)

if __name__ == "__main__":
    main()
