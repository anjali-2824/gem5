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

## License

- gem5: BSD-style license
- NVMain: Check NVMain repository for license details
