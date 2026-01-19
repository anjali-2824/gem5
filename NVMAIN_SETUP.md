# gem5 with NVMain Integration Guide

This guide provides step-by-step instructions for setting up gem5 with NVMain integration to simulate ReRAM and other non-volatile memory technologies.

## Prerequisites

### System Requirements
- Ubuntu 20.04 or later (or compatible Linux distribution)
- Python 3.8 or later
- GCC 9+ or Clang 6+
- At least 8GB RAM
- 20GB free disk space

### Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential git m4 scons zlib1g zlib1g-dev \
    libprotobuf-dev protobuf-compiler libprotoc-dev \
    libgoogle-perftools-dev python3-dev python3-six \
    python3-pydot libboost-all-dev pkg-config
```

## Installation Steps

### Step 1: Clone the Repository

This repository already contains gem5 with NVMain integrated:

```bash
git clone https://github.com/anjali-2824/gem5.git
cd gem5
```

**Note:** If you're starting fresh without this repository, see the "Manual Integration" section below.

### Step 2: Build gem5 with NVMain

NVMain is located in `ext/NVmain` and is automatically included during the build process using the `EXTRAS` parameter:

```bash
# Build for X86 architecture with NVMain support
scons build/X86/gem5.opt EXTRAS=/path/to/gem5/ext/NVmain -j$(nproc)

# Example with full path:
scons build/X86/gem5.opt EXTRAS=$(pwd)/ext/NVmain -j$(nproc)
```

**Build time:** First build takes 30-60 minutes depending on your system.

### Step 3: Verify Installation

Check that NVMain was successfully integrated:

```bash
./build/X86/gem5.opt --help
# Should complete without errors if NVMain is properly integrated
```

## Running ReRAM Simulations

### Using the Provided Test Script

A pre-configured script `run_nvmain_se.py` is provided for quick testing:

```bash
./build/X86/gem5.opt run_nvmain_se.py
```

This script:
- Runs a simple "hello world" binary
- Uses TimingSimpleCPU
- Configures NVMain with RRAM_ISSCC_2012_4GB configuration
- Outputs statistics to `m5out/stats.txt`

### Available NVMain Configurations

Located in `ext/NVmain/Config/`:

- **RRAM_ISSCC_2012_4GB.config** - Resistive RAM (ReRAM) configuration
- **PCM_ISSCC_2012_4GB.config** - Phase Change Memory
- **STTRAM_Everspin_4GB.config** - Spin-Transfer Torque RAM
- **PCM_MLC_example.config** - Multi-level cell PCM
- **PerfectMemory.config** - Zero-latency ideal memory (testing)

### Customizing Your Simulation

Edit `run_nvmain_se.py` to modify:

```python
# Change the binary to simulate
binary = "path/to/your/binary"

# Change NVMain configuration
config_path = "/path/to/gem5/ext/NVmain/Config/PCM_ISSCC_2012_4GB.config"

# Adjust system parameters
system.clk_domain.clock = "2GHz"  # CPU frequency
system.mem_ranges = [AddrRange("1GB")]  # Memory size
```

### Viewing Results

```bash
# View simulation statistics
cat m5out/stats.txt

# NVMain-specific stats include:
# - Read/write counts per channel/bank
# - Energy consumption (active, burst, background)
# - Average latency and queue latency
# - Endurance metrics
```

## Key Modifications Made

### 1. NVMain SCons Integration

**File:** `ext/NVmain/SConscript`

Added proper integration with gem5's build system:
```python
# Guard against early execution before Source() is available
if 'Source' in dir():
    # Define NVMainSource helper function
    def NVMainSource(source, tags=None):
        # ... implementation
    
    # Export for use by gem5 Simulators
    env['NVMainSource'] = NVMainSource
    env['NVMainSourceType'] = env.SourceFile
```

**File:** `ext/NVmain/Simulators/gem5/SConscript`

Added early return guard:
```python
# Early return if Source is not yet available
if 'Source' not in dir():
    Return()
```

### 2. Random Number Generator Fix

**File:** `ext/NVmain/Simulators/gem5/nvmain_mem.cc`

Replaced deprecated `random_mt` with C++11 standard library:

```cpp
// Old (deprecated):
// #include "base/random_mt.hh"
// latency += random_mt.random<Tick>(0, variance);

// New (C++11 standard):
#include <random>
static std::mt19937_64 rng(std::random_device{}());

Tick jitter = 0;
if (variance > 0) {
    std::uniform_int_distribution<Tick> dist(0, variance);
    jitter = dist(rng);
}
latency += jitter;
```

### 3. Custom System Execution (SE) Script

**File:** `run_nvmain_se.py`

Created a minimal SE configuration script with:
- TimingSimpleCPU
- NVMainMemory controller
- Proper interrupt controller setup for X86
- SEWorkload configuration

Key components:
```python
# Memory controller with NVMain
system.mem_ctrl = NVMainMemory(
    range=system.mem_ranges[0],
    config=config_path,
    atomic_mode=False,
    atomic_latency="30ns",
    atomic_variance="30ns",
)

# Connect to system bus
system.mem_ctrl.port = system.membus.mem_side_ports

# X86 requires interrupt controller in SE mode
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports
```

### 4. Added ReRAM Configuration

**File:** `ext/NVmain/Config/reram.config`

Basic ReRAM configuration template (minimal settings):
```
; Basic ReRAM configuration
tREAD 20
tWRITE 100
EnergyRead 2.0
EnergyWrite 50.0
Endurance 1000000
```

**Note:** For production use, prefer the bundled `RRAM_ISSCC_2012_4GB.config` which has complete parameter definitions.

## Troubleshooting

### Build Errors

**Error:** `NameError: name 'Source' is not defined`
- **Solution:** Ensure you're using the EXTRAS parameter: `EXTRAS=$(pwd)/ext/NVmain`

**Error:** `random_mt` not found
- **Solution:** Already fixed in this repository. If using older NVMain, apply the RNG fix above.

**Error:** Segmentation fault during NVMain initialization
- **Cause:** Missing required parameters in NVMain config file
- **Solution:** Use one of the complete configs from `ext/NVmain/Config/` (e.g., `RRAM_ISSCC_2012_4GB.config`)

### Runtime Errors

**Error:** `KeyError: 'TARGET_ISA'`
- **Solution:** Don't use `buildEnv` in SE scripts; use explicit ISA selection

**Error:** Missing interrupts
- **Solution:** For X86 SE mode, always call `system.cpu.createInterruptController()`

## Manual Integration (For Fresh Setup)

If starting from a vanilla gem5 repository:

### 1. Clone NVMain
```bash
cd /path/to/gem5/ext
git clone https://github.com/SEAL-UCSB/NVmain.git NVmain
```

### 2. Apply Required Patches

Apply the modifications described in "Key Modifications Made" section above to:
- `ext/NVmain/SConscript`
- `ext/NVmain/Simulators/gem5/SConscript`
- `ext/NVmain/Simulators/gem5/nvmain_mem.cc`

### 3. Create Test Script

Copy `run_nvmain_se.py` from this repository or create one following the template in "Custom System Execution Script" section.

## Additional Resources

- **gem5 Documentation:** https://www.gem5.org/documentation/
- **NVMain Original Repository:** https://github.com/SEAL-UCSB/NVmain
- **NVMain Wiki:** https://github.com/SEAL-UCSB/NVmain/wiki

## Quick Reference Commands

```bash
# Build gem5 with NVMain
scons build/X86/gem5.opt EXTRAS=$(pwd)/ext/NVmain -j$(nproc)

# Run ReRAM simulation
./build/X86/gem5.opt run_nvmain_se.py

# View statistics
cat m5out/stats.txt

# Clean build
scons -c build/X86

# Rebuild after changes
scons build/X86/gem5.opt EXTRAS=$(pwd)/ext/NVmain -j$(nproc)
```

## Repository Structure

```
gem5/
├── build/                      # Build outputs
│   └── X86/
│       └── gem5.opt           # Optimized binary
├── ext/
│   └── NVmain/                # NVMain integration
│       ├── Config/            # Memory configurations
│       ├── Simulators/gem5/   # gem5 interface code
│       └── SConscript         # Build integration
├── run_nvmain_se.py           # Example SE simulation script
├── m5out/                     # Simulation outputs
│   ├── stats.txt              # Performance statistics
│   └── config.ini             # System configuration
└── NVMAIN_SETUP.md           # This file
```

## Contributing

When making modifications:
1. Test with both debug and optimized builds
2. Verify NVMain statistics are generated correctly
3. Document any new configuration parameters
4. Update this guide if adding new features

## Simulating Matrix-Vector Multiplication

### Overview

A complete matrix-vector multiplication benchmark is provided to demonstrate architectural simulation with gem5 and NVMain. This example shows how to:
- Run compute-intensive workloads in gem5
- Compare different CPU models and cache configurations
- Evaluate NVM vs DRAM performance for memory-intensive operations
- Collect detailed performance statistics

### Quick Start

```bash
# 1. Build the benchmark
cd benchmarks
make
cd ..

# 2. Run with default configuration (DDR4 memory, 256x256 matrix)
./build/X86/gem5.opt configs/mvm_simulation.py

# 3. Run with NVMain ReRAM
./build/X86/gem5.opt configs/mvm_simulation.py --memory-type=nvmain

# 4. Run with larger matrix and O3 CPU
./build/X86/gem5.opt configs/mvm_simulation.py \
    --rows=512 --cols=512 --cpu-type=o3
```

### Benchmark Details

**File:** `benchmarks/mvm_benchmark.c`

Features:
- Parameterizable matrix dimensions via command-line
- Simple double-precision floating-point computation
- Checksum validation for correctness
- Optional gem5 magic instructions for region-of-interest (ROI) statistics
- Static linking for easy gem5 SE mode execution

Key computation:
```c
// Matrix-Vector Multiply: y = A * x
for (int i = 0; i < rows; i++) {
    y[i] = 0.0;
    for (int j = 0; j < cols; j++) {
        y[i] += A[i][j] * x[j];
    }
}
```

### Compilation Options

```bash
cd benchmarks

# Basic version (no gem5 annotations)
make mvm_benchmark

# Version with gem5 ROI markers (requires m5ops library)
# First build m5ops if not already built:
cd ../util/m5
scons build/x86/out/m5
cd ../../benchmarks

# Then build annotated version:
make mvm_benchmark_m5ops
```

**Benefits of m5ops version:**
- Reset statistics before main computation
- Exclude initialization and cleanup from performance metrics
- Mark specific code regions for detailed analysis

### Configuration Script Options

**File:** `configs/mvm_simulation.py`

```bash
# CPU Models
--cpu-type=timing    # Fast, in-order, single-cycle execution (default)
--cpu-type=o3        # Out-of-order CPU with complex pipeline
--cpu-type=minor     # In-order CPU with detailed pipeline modeling

# CPU Frequency
--cpu-clock=1GHz     # Slower clock
--cpu-clock=3GHz     # Faster clock

# Matrix Size
--rows=128 --cols=128      # Small (fast simulation)
--rows=512 --cols=512      # Medium
--rows=1024 --cols=1024    # Large (long simulation time)

# Cache Configuration
--l1i-size=16kB --l1d-size=16kB --l2-size=128kB   # Smaller caches
--l1i-size=64kB --l1d-size=64kB --l2-size=1MB     # Larger caches

# Memory Type
--memory-type=ddr4          # Standard DRAM (default)
--memory-type=nvmain        # Non-volatile memory via NVMain

# NVMain Configuration (when using --memory-type=nvmain)
--nvmain-config=ext/NVmain/Config/RRAM_ISSCC_2012_4GB.config      # ReRAM
--nvmain-config=ext/NVmain/Config/PCM_ISSCC_2012_4GB.config       # PCM
--nvmain-config=ext/NVmain/Config/STTRAM_Everspin_4GB.config      # STT-RAM

# Memory Size
--mem-size=512MB
--mem-size=2GB
```

### Example Use Cases

#### 1. Compare CPU Models

```bash
# TimingSimpleCPU (baseline)
./build/X86/gem5.opt configs/mvm_simulation.py --cpu-type=timing
mv m5out m5out_timing

# O3CPU (out-of-order, higher performance)
./build/X86/gem5.opt configs/mvm_simulation.py --cpu-type=o3
mv m5out m5out_o3

# Compare CPI
echo "Timing CPU CPI:"
grep "system.cpu.cpi" m5out_timing/stats.txt

echo "O3 CPU CPI:"
grep "system.cpu.cpi" m5out_o3/stats.txt
```

#### 2. Evaluate Cache Sensitivity

```bash
# Small caches (more misses expected)
./build/X86/gem5.opt configs/mvm_simulation.py \
    --l1d-size=16kB --l2-size=128kB
mv m5out m5out_small_cache

# Large caches (fewer misses expected)
./build/X86/gem5.opt configs/mvm_simulation.py \
    --l1d-size=64kB --l2-size=1MB
mv m5out m5out_large_cache

# Compare cache miss rates
grep "dcache.overall_miss_rate" m5out_small_cache/stats.txt
grep "dcache.overall_miss_rate" m5out_large_cache/stats.txt
```

#### 3. Compare DRAM vs NVM Performance

```bash
# DDR4 baseline
./build/X86/gem5.opt configs/mvm_simulation.py \
    --memory-type=ddr4 --rows=512 --cols=512
mv m5out m5out_ddr4

# ReRAM (higher write latency, lower energy)
./build/X86/gem5.opt configs/mvm_simulation.py \
    --memory-type=nvmain --rows=512 --cols=512
mv m5out m5out_rram

# Compare performance
echo "DDR4 simulation time:"
grep "simTicks" m5out_ddr4/stats.txt

echo "ReRAM simulation time:"
grep "simTicks" m5out_rram/stats.txt

# Compare energy (NVMain only)
grep "Energy" m5out_rram/stats.txt
```

#### 4. Analyze Memory Bandwidth

```bash
# Run with larger matrix to stress memory
./build/X86/gem5.opt configs/mvm_simulation.py \
    --rows=1024 --cols=1024 --memory-type=nvmain

# Check memory statistics
cat m5out/stats.txt | grep -E "(Read|Write).*Total"
cat m5out/stats.txt | grep -E "avgQLat"  # Average queue latency
```

### Understanding Statistics

Key metrics in `m5out/stats.txt`:

```bash
# CPU Performance
system.cpu.numCycles                 # Total CPU cycles
system.cpu.cpi                       # Cycles per instruction
system.cpu.ipc                       # Instructions per cycle

# Cache Performance
system.cpu.dcache.overall_miss_rate  # Data cache miss rate
system.l2cache.overall_miss_rate     # L2 cache miss rate
system.cpu.dcache.overall_misses     # Total data cache misses

# Memory Performance (DDR4)
system.mem_ctrl.readReqs             # Total read requests
system.mem_ctrl.writeReqs            # Total write requests
system.mem_ctrl.avgRdBW              # Average read bandwidth (B/s)

# Memory Performance (NVMain)
# Look for lines containing:
# - ReadTotal, WriteTotal             # Total read/write operations
# - AvgLatency                        # Average memory latency
# - Energy                            # Energy consumption per channel
# - Endurance                         # Write endurance metrics

# Overall Simulation
simSeconds                           # Simulated time in seconds
simTicks                             # Simulated time in ticks
hostSeconds                          # Real wall-clock time
```

### Performance Exploration Ideas

1. **Algorithmic Optimization:**
   - Modify the benchmark to use tiled matrix-vector multiply
   - Compare blocked vs non-blocked implementations
   - Evaluate prefetching impact

2. **Memory Hierarchy Design:**
   - Test various L1/L2 cache sizes
   - Experiment with cache associativity
   - Try different cache line sizes

3. **NVM Technology Comparison:**
   - Compare ReRAM, PCM, and STT-RAM latency/energy
   - Evaluate endurance for write-heavy workloads
   - Test hybrid DRAM+NVM configurations

4. **CPU Microarchitecture:**
   - Compare in-order vs out-of-order execution
   - Evaluate impact of clock frequency scaling
   - Test different pipeline depths (Minor CPU)

### Troubleshooting

**Compilation errors:**
```bash
# Ensure GCC is installed
gcc --version

# For static linking issues on newer systems:
sudo apt-get install gcc-multilib
```

**gem5 simulation errors:**
```bash
# "Binary not found"
# Solution: Check that benchmarks/mvm_benchmark exists
ls -l benchmarks/mvm_benchmark

# "Cannot open NVMain config"
# Solution: Verify config path is correct
ls ext/NVmain/Config/*.config

# Simulation too slow
# Solution: Reduce matrix size or use TimingSimpleCPU
./build/X86/gem5.opt configs/mvm_simulation.py --rows=128 --cols=128
```

### Next Steps

- **Add more benchmarks:** Create matrix multiplication (MxM), convolution, or FFT
- **Multi-core simulation:** Extend script to use multiple CPUs
- **Full-system mode:** Boot Linux and run benchmarks in OS context
- **Custom memory controllers:** Modify NVMain configs for novel NVM designs
- **Trace generation:** Enable debug flags for detailed memory access traces

## License

- gem5: BSD-style license
- NVMain: Check NVMain repository for license details
