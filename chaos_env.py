import subprocess
import time
import random


def apply_delay(node_ip, delay):
    target_host = "node1" if ".2" in node_ip else "node2"
    
    if delay == 0:
        # FORCE CLEAN: Make sure NO delay exists
        print(f"--- {target_host} is now CLEAN (FAST) ---")
        cmd = f"ssh {target_host} 'sudo tc qdisc del dev eno1d1 root || true'"
    else:
        print(f"{target_host} is now DELAYED ({delay}ms) ---")
        cmd = f"ssh {target_host} 'sudo tc qdisc replace dev eno1d1 root netem delay {delay}ms 2>/dev/null || sudo tc qdisc add dev eno1d1 root netem delay {delay}ms'"
    
    subprocess.run(cmd, shell=True)

try:
    while True:
        # Scenario A: Node 1 is slow, Node 2 is fast
        print("\n--- SCENARIO: NODE 1 CONGESTED ---")
        apply_delay("10.10.1.2", 200)
        apply_delay("10.10.1.3", 0)
        time.sleep(30) # Wait 30 seconds for the Bandit to react
        
        # Scenario B: Node 2 is slow, Node 1 is fast
        print("\n--- SCENARIO: NODE 2 CONGESTED ---")
        apply_delay("10.10.1.2", 0)
        apply_delay("10.10.1.3", 200)
        time.sleep(30)
except KeyboardInterrupt:
    print("Cleaning up...")
    subprocess.run("ssh node1 'sudo tc qdisc del dev eno1d1 root'", shell=True)
    subprocess.run("ssh node2 'sudo tc qdisc del dev eno1d1 root'", shell=True)