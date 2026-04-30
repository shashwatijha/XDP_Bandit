import subprocess
import time
import numpy as np
import re
import datetime
import sys

DEFAULT_BACKENDS = ["10.10.1.2", "10.10.1.3"]
BACKENDS = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_BACKENDS
D = 4  

A = {i: np.identity(D) for i in range(len(BACKENDS))}
B = {i: np.zeros((D, 1)) for i in range(len(BACKENDS))}

def get_traffic_status():
    try:
       
    #look into the eBPF Map 'traffic_stats' pinned in the filesystem
        cmd = "sudo bpftool map dump pinned /sys/fs/bpf/xdp_lb/traffic_stats"
        res = subprocess.check_output(cmd, shell=True).decode()
        
        
        matches = re.findall(r'"value":\s+(\d+)|value:\s+0x([0-9a-fA-F]+)', res)
        
        elephant_val = 0
        if matches:
            
            val_tuple = matches[1] 
            elephant_val = int(val_tuple[0]) if val_tuple[0] else int(val_tuple[1], 16)
            # print(f"DEBUG: Elephant Count is {elephant_val}")

        if elephant_val >=1: # Threshold of 500 packets to avoid jitter
            # Reset the counter
            subprocess.run("sudo bpftool map update pinned /sys/fs/bpf/xdp_lb/traffic_stats key 1 0 0 0 value 0 0 0 0 0 0 0 0", shell=True)
            # print(f"DEBUG: Elephant Count is {elephant_val}")
            return 1.0
        return 0.0
    except Exception as e:
        # print(f"Debug Error: {e}") 
        return 0.0


def get_reward(ip, is_elephant):
    try:
        res = subprocess.check_output(f"ping -c 2 -W 1 {ip}", shell=True).decode()
        avg_latency = float(re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)", res).group(1))
        
    
        if is_elephant == 1.0 and ip == "10.10.1.2":
            return 2.0 # Force a low reward
            
        reward = 100.0 / avg_latency 
        return min(reward, 10.0) 
    except:
        return 0.0

def update_xdp_map(backend_index):
    # Write the chosen node index into the 'backend_selector' map
    cmd = f"sudo bpftool map update pinned /sys/fs/bpf/xdp_lb/backend_selector key 0 0 0 0 value {backend_index} 0 0 0"
    subprocess.run(cmd, shell=True)

with open("mab_contextual.csv", "w") as f:
    f.write("timestamp,choice,reward,load0,load1,traffic_type\n")

print("Daemon Running. Use 'ping -s 1400' to trigger Elephant mode.")

try:
    while True:
        is_elephant = get_traffic_status()
        
        # 1. Choose node (Standard LinUCB)
        p = {}
        arm_contexts = {}
        for i in range(len(BACKENDS)):
            context = np.array([[1.0], [0.5], [1.0], [is_elephant]]) # Simplified context
            arm_contexts[i] = context
            A_inv = np.linalg.inv(A[i] + np.eye(D) * 1e-6)
            theta = A_inv.dot(B[i])

            # Calculate the Score for each backend
            # Score = (Learned weights * Context) + (Exploration Bonus)
            p[i] = np.dot(theta.T, context).item() + 5.0 * np.sqrt(np.dot(context.T, np.dot(A_inv, context)))

        choice = max(p, key=p.get)
        update_xdp_map(choice)
        
        # Get Reward (with the elephant penalty)
        reward = get_reward(BACKENDS[choice], is_elephant)
        
        # Update Brain
        A[choice] += np.dot(arm_contexts[choice], arm_contexts[choice].T)
        B[choice] += reward * arm_contexts[choice]

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        mode_str = "ELEPHANT" if is_elephant == 1.0 else "MOUSE"
        print(f"[{ts}] Mode: {mode_str} | Target: {BACKENDS[choice]} | Reward: {reward:.2f}")
        
        with open("mab_contextual.csv", "a") as f:
            f.write(f"{ts},{choice},{reward:.2f},0,0,{is_elephant}\n")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Stopped.")