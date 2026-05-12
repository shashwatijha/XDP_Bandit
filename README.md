# XDP_Bandit

An eBPF load balancer that uses a contextual multi-armed bandit (LinUCB) to pick backends based on real-time network conditions. The XDP program runs in the kernel and classifies traffic; a Python daemon reads that classification out of BPF maps and decides where to send traffic next.

Built and tested on CloudLab (`c220g5` nodes, Ubuntu 22.04, kernel 5.15).

---

## How it works

The kernel side (`xdp_lb.c`) hooks into XDP — before the kernel even allocates a socket buffer — and does two things: counts packets per backend, and puts incoming traffic into one of two buckets (mouse flows ≤1000 bytes, elephant flows >1000 bytes). It writes those counts into BPF maps.

The userspace side (`mab_daemon_traffic.py`) polls those maps every 500ms, builds a context vector from the traffic type, runs the LinUCB math, picks a backend, and writes that decision back into the `backend_selector` map. The XDP program reads that on the next packet.

Reward is measured by pinging the chosen backend and computing `min(100/rtt_ms, 10.0)`. Not perfect, but it works for a testbed.

---

## Testbed setup

You need 3 nodes minimum, 4 if you want a dedicated client. We used CloudLab with this layout:

```
node0  :  load balancer (runs XDP + daemon)
node1  :  backend 1   (10.10.1.2)
node2  :  backend 2   (10.10.1.3)
node3  :  client / traffic generator  [optional]
```

`chaos_env.py` SSHes into node1 and node2 directly, so it can run on node0 — no need for a separate machine just for chaos injection.

**CloudLab profile:** any bare-metal x86 profile works. We used `c220g5`. The nodes need to share an experiment network interface — ours was `eno1d1` on the `10.10.1.0/24` subnet. If yours is different you'll need to change the interface name in the attach command and in `chaos_env.py`.

**Kernel requirement:** 5.10 or newer. BPF map pinning and XDP are both needed.

---

## Dependencies

Run this on all nodes:

```bash
sudo apt update && sudo apt install -y \
    clang llvm libelf-dev linux-headers-$(uname -r) \
    iproute2 bpftool python3-pip

pip3 install numpy streamlit plotly pandas
```

Check your clang is recent enough:

```bash
clang --version   # needs 10+
```

---

## Before you compile: update the IPs

The backend IPs and MACs are hardcoded in two places. You need to fix both before building.

**1. `balancer_config.h`** — find your node1 and node2 MAC/IP:

```bash
ssh node1 "ip addr show eno1d1"
ssh node2 "ip addr show eno1d1"
```

Then edit the file:

```c
#define BE1_MAC {0xec, 0xb1, 0xd7, 0x85, 0x2a, 0xd3}  // node1 MAC
#define BE1_IP  0x02010a0a                               // node1 IP, little-endian

#define BE2_MAC {0x14, 0x58, 0xd0, 0x58, 0xaf, 0x73}  // node2 MAC
#define BE2_IP  0x03010a0a                               // node2 IP, little-endian
```

To get the little-endian hex for an IP address:

```python
import socket, struct
hex(struct.unpack("<I", socket.inet_aton("10.10.1.2"))[0])
#  '0x02010a0a'
```

**2. `mab_daemon_traffic.py`** — around line 35 there's a hardcoded penalty for node1. Change the IP to match yours:

```python
if is_elephant == 1.0 and ip == "10.10.1.2":   # your node1 IP here
```

---

## Compile

```bash
git clone https://github.com/shashwatijha/XDP_Bandit.git
cd XDP_Bandit
make
```

This produces `xdp_lb.o`. If it fails, the most common issue is clang not finding the kernel headers — make sure `linux-headers-$(uname -r)` installed cleanly.

---

## Attach XDP to the interface

```bash
# mount bpffs if it isn't already
sudo mount -t bpf bpf /sys/fs/bpf/ 2>/dev/null || true
sudo mkdir -p /sys/fs/bpf/xdp_lb

# attach — change eno1d1 to your interface name if needed
sudo ip link set dev eno1d1 xdp obj xdp_lb.o sec xdp

# sanity check
ip link show eno1d1 | grep xdp
```

The BPF maps get pinned to `/sys/fs/bpf/xdp_lb/` automatically. Verify:

```bash
ls /sys/fs/bpf/xdp_lb/
# backend_selector   pkt_counters   traffic_stats
```

If the directory is empty or missing, the program didn't attach correctly. Check `dmesg | tail -20` for verifier errors.

---

## SSH setup for chaos injection

`chaos_env.py` SSHes into `node1` and `node2` by hostname to run `tc` commands. Set that up from the load balancer node:

```bash
ssh-keygen -t ed25519 -N ""
ssh-copy-id node1
ssh-copy-id node2

# make sure it works without a password prompt
ssh node1 "hostname"
ssh node2 "hostname"
```

---

## Running

You'll want three terminals on the load balancer.

**Terminal 1 — the daemon:**

```bash
# traffic-aware contextual LinUCB (recommended)
sudo python3 mab_daemon_traffic.py 10.10.1.2 10.10.1.3

# or the simpler non-contextual version
sudo python3 mab_daemon.py 10.10.1.2 10.10.1.3
```

**Terminal 2 — chaos injection:**

```bash
sudo python3 chaos_env.py
```

This alternates a 200ms `tc netem` delay between node1 and node2 every 30 seconds. Watch the daemon output to see it react.

**Terminal 3 — live dashboard:**

```bash
streamlit run dashboard.py
```

Open `http://localhost:8501` in a browser. You can switch between `mab_contextual.csv`, `mab_performance.csv`, and `baseline_rr.csv` from the sidebar.

---

## Running the baseline

To get round-robin numbers to compare against, stop the daemon first, then:

```bash
sudo python3 baseline_rr.py 10.10.1.2 10.10.1.3
```

Results go to `baseline_rr.csv` in the same format as the MAB output, so the dashboard can display it directly.

---

## Triggering elephant flows manually

To test the traffic classification without waiting for the chaos script:

```bash
# from the client node (or node0)
ping -f -s 1400 10.10.1.2
```

The `-s 1400` flag makes packets >1000 bytes, which pushes them into the elephant bucket in `traffic_stats`. You should see the daemon switch to `ELEPHANT` mode in its output within one or two ticks.

---

## Cleanup

```bash
sudo ip link set dev eno1d1 xdp off
sudo rm -rf /sys/fs/bpf/xdp_lb
```

---

## Files

| File | What it does |
|---|---|
| `xdp_lb.c` | XDP kernel program — classifies traffic, reads backend selector, counts packets |
| `balancer_config.h` | Hardcoded backend MACs and IPs — edit this before compiling |
| `Makefile` | Single clang BPF compile rule |
| `mab_daemon.py` | Basic LinUCB daemon, 3D context, no traffic classification |
| `mab_daemon_traffic.py` | Contextual LinUCB daemon, reads elephant flag from BPF map |
| `baseline_rr.py` | Round-robin baseline for comparison |
| `chaos_env.py` | Injects/removes `tc netem` delay on backends via SSH |
| `dashboard.py` | Streamlit dashboard for live monitoring |
| `mab_performance.csv` | Output from `mab_daemon.py` runs |
| `mab_contextual.csv` | Output from `mab_daemon_traffic.py` runs |
| `baseline_rr.csv` | Output from `baseline_rr.py` runs |

---

## Known issues / limitations

- The XDP program returns `XDP_PASS` — it does not actually redirect packets at the driver level. Routing still goes through the kernel IP stack. Real redirection with `bpf_redirect` and header rewriting is the obvious next step but we ran out of time debugging ARP edge cases.
- The BPF maps use `BPF_MAP_TYPE_ARRAY` with atomic adds. At high packet rates this would cause cache-line contention across cores. Switching to `PERCPU_ARRAY` is straightforward.
- Reward is measured by pinging the chosen backend. This is slow (adds ~20ms per tick from the subprocess call) and imprecise. Good enough for a testbed, not for production.
- `chaos_env.py` hardcodes the interface name `eno1d1`. Change it if your CloudLab nodes have a different experiment interface.
