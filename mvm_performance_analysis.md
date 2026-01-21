# Matrix-Vector Multiplication Performance Analysis

## Simulation Configuration

- **CPU Type**: O3 (Out-of-Order) CPU
- **CPU Frequency**: 2 GHz
- **Matrix Size**: 512 x 512
- **Memory Type**: NVMain (ReRAM - RRAM_ISSCC_2012_4GB)
- **L1 I-Cache**: 32 KiB, 2-way associative
- **L1 D-Cache**: 32 KiB, 2-way associative  
- **L2 Cache**: 256 KiB, 8-way associative
- **Total Memory**: 1 GiB

---

## Performance Metrics

### CPU Performance

| Metric | Value | Description |
|--------|-------|-------------|
| **Total CPU Cycles** | 8,018,393,861 | Total number of CPU cycles simulated |
| **Instructions Executed** | 496,153 | Total instructions committed |
| **CPI (Cycles Per Instruction)** | 16,161.13 | Very high due to memory-intensive workload |
| **IPC (Instructions Per Cycle)** | 0.000062 | Extremely low - dominated by memory stalls |
| **Simulated Time** | 4.009 seconds | Time simulated at 2 GHz |
| **Host Simulation Time** | 100,832 seconds (~28 hours) | Real-world time to simulate |

**Analysis**: The extremely high CPI (16,161) indicates the computation is severely memory-bound. The O3 CPU spends most cycles waiting for memory accesses rather than executing instructions.

---

### Cache Performance

#### L1 Instruction Cache

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Accesses** | 81,271 | Instruction fetch requests |
| **Hits** | 80,368 | Successful cache hits |
| **Misses** | 903 | Cache misses |
| **Miss Rate** | 1.11% | Very low - good instruction locality |
| **Average Miss Latency** | 65,719 ticks (~33 ns) | Time per miss |

#### L1 Data Cache

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Accesses** | 76,896 | Read + write requests |
| **Hits** | 70,518 | Successful cache hits |
| **Misses** | 6,378 | Cache misses |
| **Miss Rate** | 8.29% | Moderate - typical for matrix ops |
| **Average Miss Latency** | 51,529 ticks (~26 ns) | Time per miss |
| **MSHR Misses** | 3,966 | Misses that went to L2 |
| **Writebacks** | 2,713 | Dirty lines written back |

**Analysis**: The D-cache miss rate of 8.29% is reasonable for matrix-vector multiplication, which has predictable but sparse access patterns. Many misses are absorbed by MSHRs (Miss Status Holding Registers).

#### L2 Cache

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Accesses** | 4,684 | Requests from L1 caches |
| **Hits** | 143 | L2 cache hits |
| **Misses** | 4,541 | L2 cache misses |
| **Miss Rate** | 96.95% | Extremely high - most data not in L2 |
| **Average Miss Latency** | 66,462 ticks (~33 ns) | Time per miss |
| **MSHR Misses** | 4,541 | Requests to main memory |
| **Replacements** | 641 | Cache lines evicted |

**Analysis**: The 96.95% L2 miss rate is extremely high, indicating the working set (512x512 matrix = 2 MB for double precision) far exceeds the 256 KB L2 cache. Almost every L1 miss propagates to main memory.

---

### Memory Performance

#### Memory Controller Stats

| Metric | Value | Description |
|--------|-------|-------------|
| **Read Requests** | 4,540 | Total memory reads |
| **Instruction Reads** | 681 | Code fetches |
| **Data Reads** | 3,859 | Data loads |
| **Write Requests** | 65 | Writebacks to memory |
| **Bytes Read** | 290,560 bytes (~284 KB) | Total read traffic |
| **Bytes Written** | 4,160 bytes (~4 KB) | Total write traffic |
| **Read Bandwidth** | 72,473 B/s | Average read bandwidth |
| **Write Bandwidth** | 1,038 B/s | Average write bandwidth |

**Analysis**: The low write count (65) vs high read count (4,540) is expected for read-heavy matrix-vector multiplication. Total bandwidth is very low due to frequent stalls.

---

### Memory Hierarchy Impact

#### Data Flow Through Caches

```
L1 D-Cache Misses: 6,378
  ├─ MSHR Hits (absorbed): 2,412 (37.8%)
  └─ L2 Requests: 3,966
      ├─ L2 Hits: 102 (2.6%)
      └─ Memory Requests: 3,859 (97.4%)
```

**Key Insight**: Only 2.6% of L1 D-cache misses are satisfied by L2. The vast majority (97.4%) require main memory access, explaining the severe performance degradation.

---

### Branch Prediction Performance

| Metric | Value | Description |
|--------|-------|-------------|
| **Total Branches** | 91,508 | Branch instructions encountered |
| **Mispredictions** | 885 | Incorrectly predicted branches |
| **Misprediction Rate** | 0.97% | Very accurate prediction |
| **Branch Types** | Mostly conditional (79.3%) | Loop control branches |

**Analysis**: Excellent branch prediction (99% accurate) for matrix loops, which have predictable patterns.

---

## Performance Bottlenecks

### 1. Memory Wall Effect
- **Problem**: 96.95% L2 miss rate creates massive memory stalls
- **Root Cause**: 2 MB working set >> 256 KB L2 cache
- **Impact**: CPI of 16,161 (99.99% time in memory waits)

### 2. Limited Memory Bandwidth
- **Observed**: Only 73.5 KB/s bandwidth utilization
- **Cause**: Sequential memory access pattern + high latency
- **Effect**: CPU heavily underutilized

### 3. Cache Thrashing
- **Evidence**: 641 L2 replacements for only 4,541 accesses
- **Reason**: Matrix data constantly evicting each other
- **Result**: No temporal reuse benefits

---

## Optimization Recommendations

### 1. **Increase L2 Cache Size**
```bash
# Try 1 MB or 2 MB L2 cache
./build/X86/gem5.opt configs/mvm_simulation.py \
    --l2-size=1MB --rows=512 --cols=512 --memory-type=nvmain
```
**Expected**: Reduce L2 miss rate from 97% to <50%, significantly improving CPI.

### 2. **Implement Cache Blocking (Tiling)**
Modify the benchmark to process matrix in tiles that fit in cache:
```c
#define TILE_SIZE 32
for (int i0 = 0; i0 < rows; i0 += TILE_SIZE) {
    for (int i = i0; i < min(i0+TILE_SIZE, rows); i++) {
        y[i] = 0.0;
        for (int j = 0; j < cols; j++) {
            y[i] += A[i][j] * x[j];
        }
    }
}
```
**Expected**: Better cache reuse, lower miss rates.

### 3. **Try Different CPU Models**
```bash
# TimingSimpleCPU (simpler, faster simulation)
./build/X86/gem5.opt configs/mvm_simulation.py --cpu-type=timing

# Minor CPU (in-order with pipeline detail)
./build/X86/gem5.opt configs/mvm_simulation.py --cpu-type=minor
```
**Expected**: Faster simulation with similar memory insights.

### 4. **Reduce Matrix Size for Testing**
```bash
# Smaller matrix fits better in cache
./build/X86/gem5.opt configs/mvm_simulation.py \
    --rows=256 --cols=256 --memory-type=nvmain
```
**Expected**: Lower simulation time, visible cache effects.

### 5. **Enable NVMain Statistics**
Check NVMain configuration and ensure statistics are being generated. The current stats don't show NVMain-specific energy/endurance metrics that should be available with RRAM configuration.

---

## Comparison Guidelines

To compare different configurations, focus on these key metrics:

### Performance Metrics
- **CPI**: Lower is better (indicates less memory stalling)
- **Simulated Time (simSeconds)**: Lower is better (faster execution)
- **L2 Miss Rate**: Lower is better (more data reuse)

### Memory Metrics (when available)
- **NVMain ReadTotal/WriteTotal**: Total NVM operations
- **NVMain AvgLatency**: Average memory access latency
- **NVMain Energy**: Power consumption (important for NVM)
- **NVMain Endurance**: Write wear statistics

### Running Comparisons

```bash
# Configuration 1: Current (O3 + NVMain)
./build/X86/gem5.opt configs/mvm_simulation.py \
    --cpu-type=o3 --memory-type=nvmain --rows=512 --cols=512
mv m5out m5out_o3_nvmain_512

# Configuration 2: DDR4 baseline
./build/X86/gem5.opt configs/mvm_simulation.py \
    --cpu-type=o3 --memory-type=ddr4 --rows=512 --cols=512
mv m5out m5out_o3_ddr4_512

# Configuration 3: Larger cache
./build/X86/gem5.opt configs/mvm_simulation.py \
    --cpu-type=o3 --memory-type=nvmain --l2-size=1MB --rows=512 --cols=512
mv m5out m5out_o3_nvmain_1MB_512

# Compare results
echo "CPI Comparison:"
grep "system.cpu.cpi " m5out_*/stats.txt

echo "L2 Miss Rate Comparison:"
grep "system.l2cache.overall_miss_rate::total" m5out_*/stats.txt

echo "Simulated Time Comparison:"
grep "simSeconds " m5out_*/stats.txt
```

---

## Summary

This 512x512 matrix-vector multiplication on gem5 with O3 CPU and NVMain ReRAM demonstrates:

1. **Severe memory bottleneck**: 97% L2 miss rate dominates performance
2. **Excellent branch prediction**: 99% accuracy for loop branches  
3. **Low memory bandwidth utilization**: Only 73.5 KB/s achieved
4. **Cache thrashing**: Working set far exceeds cache capacity

**Main Takeaway**: The computation is completely dominated by memory latency. To improve performance, focus on cache optimization (larger caches or algorithmic blocking) rather than CPU microarchitecture features.

**Next Steps**: 
1. Run comparison with larger L2 cache (1-2 MB)
2. Implement tiled/blocked matrix-vector multiplication
3. Compare NVMain (ReRAM) vs DDR4 performance and energy
4. Verify NVMain statistics are being captured properly
