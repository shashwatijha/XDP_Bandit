import subprocess
import time
import random

MAP_ID = "8"

def set_backend(backend_index):
    cmd = f"sudo bpftool map update id {MAP_ID} key 0 0 0 0 value {backend_index} 0 0 0"
    subprocess.run(cmd.split(), check=True)

def get_reward(backend_ip):
    return random.uniform(10, 50) 

if __name__ == "__main__":
    while True:
        try:
            reward1 = get_reward("10.10.1.2")
            reward2 = get_reward("10.10.1.3")
            
            best_backend = 0 if reward1 < reward2 else 1
            set_backend(best_backend)
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            break
