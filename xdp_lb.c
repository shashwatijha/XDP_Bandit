#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include "balancer_config.h"

SEC("xdp")
int xdp_lb_prog(struct xdp_md *ctx) {
    bpf_printk("EBalaNCer: Packet received on node0\n");
    return XDP_PASS; 
}

char _license[] SEC("license") = "GPL";
