TARGET = xdp_lb
BPF_OBJ = $(TARGET).o
BPF_C = $(TARGET).c

all: $(BPF_OBJ)

$(BPF_OBJ): $(BPF_C)
	clang -target bpf -g -O2 -c $(BPF_C) -o $(BPF_OBJ)

clean:
	rm -f $(BPF_OBJ)
