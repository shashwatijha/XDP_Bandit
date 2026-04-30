#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/in.h>
#include "balancer_config.h"

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);
} backend_selector SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 2); // One for each backend
    __type(key, __u32);
    __type(value, __u64);
} pkt_counters SEC(".maps");

SEC("xdp")
int xdp_lb_prog(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;

    if (eth->h_proto != __constant_htons(ETH_P_IP)) return XDP_PASS;

    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) return XDP_PASS;

    if (iph->protocol != IPPROTO_ICMP) return XDP_PASS;

    __u32 key = 0;
    __u32 *sel = bpf_map_lookup_elem(&backend_selector, &key);
    
    if (sel) {
        __u32 backend_idx = *sel;
        __u64 *count = bpf_map_lookup_elem(&pkt_counters, &backend_idx);
        if (count) {
            __sync_fetch_and_add(count, 1);
        }
        bpf_printk("Bandit chose backend %d, incrementing counter\n", backend_idx);
        return XDP_PASS; 
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
