"""
Matrix-Vector Multiplication Simulation Configuration for gem5 with NVMain

This script configures a gem5 system to simulate matrix-vector multiplication
with various CPU models, cache hierarchies, and memory subsystems including NVMain.

Usage:
    ./build/X86/gem5.opt configs/mvm_simulation.py [options]

Options:
    --binary=PATH           Path to the benchmark binary (default: benchmarks/mvm_benchmark)
    --rows=N                Matrix rows (default: 256)
    --cols=N                Matrix columns (default: 256)
    --cpu-type=TYPE         CPU model: timing, o3, minor (default: timing)
    --cpu-clock=FREQ        CPU frequency (default: 2GHz)
    --memory-type=TYPE      Memory type: ddr4, nvmain (default: ddr4)
    --nvmain-config=PATH    NVMain config file (default: RRAM_ISSCC_2012_4GB.config)
    --l1i-size=SIZE         L1 instruction cache size (default: 32kB)
    --l1d-size=SIZE         L1 data cache size (default: 32kB)
    --l2-size=SIZE          L2 cache size (default: 256kB)
    --mem-size=SIZE         Memory size (default: 1GB)
"""

import argparse
import os
import sys

import m5
from m5.objects import *
from m5.util import addToPath

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Matrix-Vector Multiplication Simulation')
parser.add_argument('--binary', type=str, default='benchmarks/mvm_benchmark',
                    help='Path to the benchmark binary')
parser.add_argument('--rows', type=int, default=256,
                    help='Number of matrix rows')
parser.add_argument('--cols', type=int, default=256,
                    help='Number of matrix columns')
parser.add_argument('--cpu-type', type=str, default='timing',
                    choices=['timing', 'o3', 'minor'],
                    help='CPU model type')
parser.add_argument('--cpu-clock', type=str, default='2GHz',
                    help='CPU clock frequency')
parser.add_argument('--memory-type', type=str, default='ddr4',
                    choices=['ddr4', 'nvmain'],
                    help='Memory subsystem type')
parser.add_argument('--nvmain-config', type=str, 
                    default='ext/NVmain/Config/RRAM_ISSCC_2012_4GB.config',
                    help='NVMain configuration file')
parser.add_argument('--l1i-size', type=str, default='32kB',
                    help='L1 instruction cache size')
parser.add_argument('--l1d-size', type=str, default='32kB',
                    help='L1 data cache size')
parser.add_argument('--l2-size', type=str, default='256kB',
                    help='L2 cache size')
parser.add_argument('--mem-size', type=str, default='1GB',
                    help='Total memory size')

args = parser.parse_args()

# Verify binary exists
if not os.path.exists(args.binary):
    print(f"Error: Benchmark binary not found: {args.binary}")
    print("Please compile the benchmark first:")
    print("  cd benchmarks && make")
    sys.exit(1)

# Create the system
system = System()

# Set clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()

# Memory configuration
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange(args.mem_size)]

# Create CPU based on type
print(f"Creating {args.cpu_type.upper()} CPU at {args.cpu_clock}")
if args.cpu_type == 'timing':
    system.cpu = TimingSimpleCPU()
elif args.cpu_type == 'o3':
    system.cpu = O3CPU()
elif args.cpu_type == 'minor':
    system.cpu = MinorCPU()

# Create memory bus
system.membus = SystemXBar()

# Create cache hierarchy
print(f"Configuring cache hierarchy:")
print(f"  L1I: {args.l1i_size}, L1D: {args.l1d_size}, L2: {args.l2_size}")

# L1 Instruction Cache
system.cpu.icache = Cache(
    size=args.l1i_size,
    assoc=2,
    tag_latency=2,
    data_latency=2,
    response_latency=2,
    mshrs=4,
    tgts_per_mshr=20
)

# L1 Data Cache
system.cpu.dcache = Cache(
    size=args.l1d_size,
    assoc=2,
    tag_latency=2,
    data_latency=2,
    response_latency=2,
    mshrs=4,
    tgts_per_mshr=20
)

# L2 Cache
system.l2bus = L2XBar()
system.l2cache = Cache(
    size=args.l2_size,
    assoc=8,
    tag_latency=20,
    data_latency=20,
    response_latency=20,
    mshrs=20,
    tgts_per_mshr=12
)

# Connect L1 caches to CPU
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Connect L1 caches to L2 bus
system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports

# Connect L2 cache
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.l2cache.mem_side = system.membus.cpu_side_ports

# Create memory controller
if args.memory_type == 'ddr4':
    print("Using DDR4 memory controller")
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR4_2400_16x4()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports
elif args.memory_type == 'nvmain':
    # Verify NVMain config exists
    nvmain_config_path = os.path.abspath(args.nvmain_config)
    if not os.path.exists(nvmain_config_path):
        print(f"Error: NVMain config not found: {nvmain_config_path}")
        sys.exit(1)
    
    print(f"Using NVMain memory controller")
    print(f"  Config: {nvmain_config_path}")
    system.mem_ctrl = NVMainMemory(
        range=system.mem_ranges[0],
        config=nvmain_config_path,
        atomic_mode=False,
        atomic_latency="30ns",
        atomic_variance="10ns"
    )
    system.mem_ctrl.port = system.membus.mem_side_ports

# Connect system port
system.system_port = system.membus.cpu_side_ports

# Create interrupt controller (required for X86)
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# Set up the workload
binary_path = os.path.abspath(args.binary)
cmd = [binary_path, str(args.rows), str(args.cols)]

print(f"\nSimulation configuration:")
print(f"  Binary: {binary_path}")
print(f"  Matrix size: {args.rows} x {args.cols}")
print(f"  Command: {' '.join(cmd)}")

# Initialize system-level SE workload
system.workload = SEWorkload.init_compatible(binary_path)

# Create process for the CPU
process = Process()
process.cmd = cmd
system.cpu.workload = process
system.cpu.createThreads()

# Set up simulation
root = Root(full_system=False, system=system)
m5.instantiate()

print("\n" + "="*60)
print("Starting gem5 simulation...")
print("="*60 + "\n")

# Run the simulation
exit_event = m5.simulate()

print("\n" + "="*60)
print(f"Simulation complete!")
print(f"Exit reason: {exit_event.getCause()}")
print(f"Simulated time: {m5.curTick() / 1e12:.6f} seconds")
print(f"Statistics saved to: m5out/stats.txt")
print("="*60)
