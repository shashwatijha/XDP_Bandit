import subprocess
import time
import datetime
import re

BACKENDS = ["10.10.1.2", "10.10.1.3"]

def update_xdp_map(index):
    cmd = f"sudo bpftool map update pinned /sys/fs/bpf/xdp_lb/backend_selector key 0 0 0 0 value {index} 0 0 0"
    subprocess.run(cmd, shell=True)

def get_reward(ip):
    try:
        # Measure latency to record the "blind" performance
        res = subprocess.check_output(f"ping -c 1 -W 1 {ip}", shell=True).decode()
        avg_latency = float(re.search(r"time=([\d\.]+)", res).group(1))
        # Reward is inverse latency as defined in your proposal [cite: 69]
        return min(100.0 / avg_latency, 10.0)
    except:
        return 0.0

# Write to a unique file for the evaluation report [cite: 73]
output_file = "baseline_rr.csv"
print(f"Recording Baseline to {output_file}...")

with open(output_file, "w") as f:
    f.write("timestamp,choice,reward,load0,load1,traffic_type\n")

try:
    count = 0
    while True:
        choice = count % 2 # Static Round Robin 
        update_xdp_map(choice)
        
        reward = get_reward(BACKENDS[choice])
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        
        print(f"[{ts}] Static Choice: {BACKENDS[choice]} | Reward: {reward:.2f}")
        
        with open(output_file, "a") as f:
            f.write(f"{ts},{choice},{reward:.2f},0,0,0\n")
            
        count += 1
        time.sleep(0.5)
except KeyboardInterrupt:
    print(f"\nBaseline complete. Data saved in {output_file}")