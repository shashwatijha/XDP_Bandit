import subprocess
import time
import numpy as np
import re

# --- CONFIGURATION ---
MAP_ID = 8
BACKENDS = ["10.10.1.2", "10.10.1.3"]
ALPHA = 20.0 # Exploration rate
D = 2        # Number of features

# --- LinUCB STATE ---
# A: Covariance matrix for each backend
# B: Reward vector for each backend
A = {i: np.identity(D) for i in range(len(BACKENDS))}
B = {i: np.zeros((D, 1)) for i in range(len(BACKENDS))}

def get_reward(ip):
    # This command gets both latency AND packet loss
    res = subprocess.check_output(f"ping -c 1 -W 1 {ip}", shell=True).decode()
    
    # Extract Avg Latency
    avg_latency = float(re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)", res).group(1))
    
    # Extract Packet Loss (e.g., "0% packet loss")
    loss_percent = float(re.search(r"(\d+)% packet loss", res).group(1)) / 100.0
    
    # Calculate sophisticated reward
    # High latency = low reward | High loss = low reward
    reward = (1000 / avg_latency) * (1.0 - loss_percent)
    return reward
def select_backend(context):
    p = {}
    for i in range(len(BACKENDS)):
        A_inv = np.linalg.inv(A[i])
        theta = A_inv.dot(B[i])
        # LinUCB Formula: p = theta^T * x + alpha * sqrt(x^T * A_inv * x)
        uncertainty = ALPHA * np.sqrt(np.dot(context.T, np.dot(A_inv, context)))
        p[i] = np.dot(theta.T, context) + uncertainty
    
    return max(p, key=p.get)

def update_model(arm, context, reward):
    A[arm] += np.dot(context, context.T)
    B[arm] += reward * context

def update_xdp_map(backend_index):
    cmd = f"sudo /usr/lib/linux-tools/$(uname -r)/bpftool map update pinned /sys/fs/bpf/xdp_lb/backend_selector key 0 0 0 0 value {backend_index} 0 0 0"
    subprocess.run(cmd, shell=True)


print(f"Starting LinUCB MAB Daemon on Map {MAP_ID}...")
try:
    while True:
        p = {}
        for i in range(len(BACKENDS)):
            # 1. Arm-Specific Context: [1, 0] for Node 1, [0, 1] for Node 2
            arm_context = np.zeros((D, 1))
            arm_context[i] = 1.0
            
            # 2. Calculate UCB Score
            # We add a tiny bit of noise (1e-6) to A to ensure it can always be inverted
            A_inv = np.linalg.inv(A[i] + np.eye(D) * 1e-6)
            theta = A_inv.dot(B[i])
            
            uncertainty = ALPHA * np.sqrt(np.dot(arm_context.T, np.dot(A_inv, arm_context)))
            p[i] = np.dot(theta.T, arm_context) + uncertainty

        # 3. Choose the arm with the highest score
        choice = max(p, key=lambda k: p[k])
        
        # 4. Update Kernel and Observe
        update_xdp_map(choice)
        reward = get_reward(BACKENDS[choice])
        
        # 5. Update the Model with Arm-Specific Context
        current_context = np.zeros((D, 1))
        current_context[choice] = 1.0
        update_model(choice, current_context, reward)

        # 6. Global Decay: This is what forces the flip!
        GAMMA = 0.7  # Very aggressive for the demo
        for i in range(len(BACKENDS)):
            A[i] = A[i] * GAMMA + np.identity(D) * (1 - GAMMA)
            B[i] = B[i] * GAMMA

        print(f"Target: {BACKENDS[choice]} | Reward: {reward:.2f} | Choice: {choice}")
        time.sleep(0.1)

except Exception as e:
    print(f"Error: {e}")
except KeyboardInterrupt:
    print("\nStopping Daemon...")