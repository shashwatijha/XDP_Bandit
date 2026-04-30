import subprocess
import time
import random

def apply_delay(node_ip, delay):
    target_host = "node1" if ".2" in node_ip else "node2"
    
    if delay == 0:
        # FORCE CLEAN: Make sure NO delay exists
        print(f"Status: {target_host} link restored (0ms)")
        cmd = f"ssh {target_host} 'sudo tc qdisc del dev eno1d1 root || true'"
    else:
        print(f"Status: {target_host} link throttled ({delay}ms)")
        cmd = f"ssh {target_host} 'sudo tc qdisc replace dev eno1d1 root netem delay {delay}ms 2>/dev/null || sudo tc qdisc add dev eno1d1 root netem delay {delay}ms'"
    
    subprocess.run(cmd, shell=True)

try:
    while True:
        print(f"\n[{time.strftime('%H:%M:%S')}] Applying Scenario: Node 1 Congested")
        apply_delay("10.10.1.2", 200)
        apply_delay("10.10.1.3", 0)
        time.sleep(30) 
        
        print(f"\n[{time.strftime('%H:%M:%S')}] Applying Scenario: Node 2 Congested")
        apply_delay("10.10.1.2", 0)
        apply_delay("10.10.1.3", 200)
        time.sleep(30)
except KeyboardInterrupt:
    print("\nTermination signal received. Cleaning up interfaces...")
    subprocess.run("ssh node1 'sudo tc qdisc del dev eno1d1 root 2>/dev/null || true'", shell=True)
    subprocess.run("ssh node2 'sudo tc qdisc del dev eno1d1 root 2>/dev/null || true'", shell=True)
    print("Cleanup complete.")