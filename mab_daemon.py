import subprocess
import time
import numpy as np
import re
import datetime
import sys

DEFAULT_BACKENDS = ["10.10.1.2", "10.10.1.3"]
BACKENDS = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_BACKENDS
ALPHA = 1.0  # High alpha for faster exploration in demos
D = 3  
GAMMA = 1.0   # Keep memory at 100% for the demo

# Initialize A as Identity and B as Zero
A = {i: np.identity(D) for i in range(len(BACKENDS))}
B = {i: np.zeros((D, 1)) for i in range(len(BACKENDS))}
python_pkt_counts = [0] * len(BACKENDS)

def get_packet_count(idx):
    try:
        cmd = f"sudo bpftool map lookup pinned /sys/fs/bpf/xdp_lb/pkt_counters key {idx} 0 0 0"
        res = subprocess.check_output(cmd, shell=True).decode()
        match = re.search(r"value:\s+0x([0-9a-fA-F]+)", res)
        return int(match.group(1), 16) if match else 0
    except:
        return 0

def get_reward(ip):
    try:
        res = subprocess.check_output(f"ping -c 2 -W 1 {ip}", shell=True).decode()
        avg_latency = float(re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)", res).group(1))
        # Scale reward between 0 and 10 (much better for LinUCB math)
        reward = 100.0 / avg_latency 
        return min(reward, 10.0) 
    except:
        return 0.0
def update_xdp_map(backend_index):
    cmd = f"sudo bpftool map update pinned /sys/fs/bpf/xdp_lb/backend_selector key 0 0 0 0 value {backend_index} 0 0 0"
    subprocess.run(cmd, shell=True)

print("Starting Final LinUCB MAB Daemon...")

try:
    with open("mab_performance.csv", "w") as f:
        f.write("timestamp,choice,reward,load0,load1\n")

    while True:
        # 1. Get current state
        loads = [get_packet_count(i) + python_pkt_counts[i] for i in range(len(BACKENDS))]
        total_load = sum(loads) + 1
        
        p = {}
        arm_contexts = {}

        # 2. Check for "Cold Start" (Any node never tried?)
        unpulled_arms = [i for i in range(len(BACKENDS)) if python_pkt_counts[i] == 0]
        
        if unpulled_arms:
            choice = unpulled_arms[0]
            # Create a simple initial context for the first pull
            norm_load = loads[choice] / total_load
            arm_contexts[choice] = np.array([[1.0], [norm_load], [0.0]])
        else:
            # 3. Standard LinUCB Math
            for i in range(len(BACKENDS)):
                norm_load = loads[i] / total_load
                # Context vector: [Bias, Load, History]
                context = np.array([[1.0], [norm_load], [1.0]])
                arm_contexts[i] = context

                # Calculate UCB Score: Upper Bound = Predicted Reward + Uncertainty
                A_inv = np.linalg.inv(A[i] + np.eye(D) * 1e-6)
                theta = A_inv.dot(B[i])
                uncertainty = ALPHA * np.sqrt(np.dot(context.T, np.dot(A_inv, context)))
                
                # Extract scalar values from 1x1 numpy arrays
                p[i] = np.dot(theta.T, context).item() + uncertainty.item()

            choice = max(p, key=p.get)

        # 4. Enforce Choice & Measure Reward
        update_xdp_map(choice)
        python_pkt_counts[choice] += 1
        reward = get_reward(BACKENDS[choice])

        if reward < 1.0:
            ALPHA = 20.0
        else:
            ALPHA = 1.0
        
        # 5. Update the "Brain"
        # A = A + x*x.T
        # B = B + reward*x
        A[choice] += np.dot(arm_contexts[choice], arm_contexts[choice].T)
        B[choice] += reward * arm_contexts[choice]

        # 6. Logging
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Target: {BACKENDS[choice]} | Reward: {reward:.2f} | Load: {loads}")
        
        with open("mab_performance.csv", "a") as f:
            f.write(f"{ts},{choice},{reward:.2f},{loads[0]},{loads[1]}\n")

        # 0.5s sleep is a good balance for live demos
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping Daemon...")