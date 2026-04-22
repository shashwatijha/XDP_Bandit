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

SEC("xdp")
int xdp_lb_prog(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;

    if (eth->h_proto != __constant_htons(ETH_P_IP)) return XDP_PASS;

    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) return XDP_PASS;

    // Only redirect ICMP (ping) for this test to avoid SSH suicide
    if (iph->protocol != IPPROTO_ICMP) return XDP_PASS;

    __u32 key = 0;
    __u32 *sel = bpf_map_lookup_elem(&backend_selector, &key);
    
    if (sel) {
        unsigned char mac1[] = BE1_MAC;
        unsigned char mac2[] = BE2_MAC;

        if (*sel == 0) {
            iph->daddr = BE1_IP;
            __builtin_memcpy(eth->h_dest, mac1, 6);
        } else {
            iph->daddr = BE2_IP;
            __builtin_memcpy(eth->h_dest, mac2, 6);
        }

        // Simple way to handle the checksum for this demo
        iph->check = 0; // Kernel or NIC usually handles this with XDP_TX, but for ICMP we are being quick
        
        bpf_printk("Redirecting to Backend %d\n", *sel + 1);
        return XDP_TX; // Transmit back out!
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
