TARGET = xdp_lb
BPF_OBJ = $(TARGET).o
BPF_C = $(TARGET).c

all: $(BPF_OBJ)

$(BPF_OBJ): $(BPF_C)
	clang -S \
	    -target bpf \
	    -D __BPF_TRACING__ \
	    -O2 -emit-llvm -c $(BPF_C) -o - | \
	llc -march=bpf -filetype=obj -o $(BPF_OBJ)

clean:
	rm -f $(BPF_OBJ)
