# Makefile for gem5 benchmarks

CC = gcc
CFLAGS = -O2 -static -std=c99
GEM5_M5OPS = ../util/m5/build/x86/out

# Default target
all: mvm_benchmark mvm_benchmark_m5ops

# Basic version without gem5 annotations
mvm_benchmark: mvm_benchmark.c
	$(CC) $(CFLAGS) -o mvm_benchmark mvm_benchmark.c -lm

# Version with gem5 m5ops annotations (requires building m5ops first)
mvm_benchmark_m5ops: mvm_benchmark.c
	@if [ -d "$(GEM5_M5OPS)" ]; then \
		echo "Building with gem5 m5ops support..."; \
		$(CC) $(CFLAGS) -DGEM5_ANNOTATIONS \
			-I../include \
			-o mvm_benchmark_m5ops mvm_benchmark.c \
			$(GEM5_M5OPS)/m5op_x86.o -lm; \
	else \
		echo "Warning: m5ops not found. Building basic version instead."; \
		echo "To build m5ops: cd ../util/m5 && scons build/x86/out/m5"; \
		$(CC) $(CFLAGS) -o mvm_benchmark_m5ops mvm_benchmark.c -lm; \
	fi

clean:
	rm -f mvm_benchmark mvm_benchmark_m5ops

.PHONY: all clean
