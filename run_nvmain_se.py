import m5
from m5.objects import *
from m5.objects import SEWorkload

# Paths
binary = "tests/test-progs/hello/bin/x86/linux/hello"
config_path = (
    "/home/anjali-naluvala/gem5/ext/NVmain/Config/RRAM_ISSCC_2012_4GB.config"
)

# System setup
system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

# CPU
system.cpu = TimingSimpleCPU()

# Buses
system.membus = SystemXBar()

# Memory: NVMain-backed
system.mem_ctrl = NVMainMemory(
    range=system.mem_ranges[0],
    config=config_path,
    atomic_mode=False,
    atomic_latency="30ns",
    atomic_variance="30ns",
)

# Connect memory
system.mem_ctrl.port = system.membus.mem_side_ports

# Connect CPU to bus
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

# Interrupt controller (needed for x86 SE)
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# System port
system.system_port = system.membus.cpu_side_ports

# Process workload
system.workload = SEWorkload.init_compatible(binary)
process = Process()
process.cmd = [binary]
system.cpu.workload = process
system.cpu.createThreads()

# Root and run
root = Root(full_system=False, system=system)

m5.instantiate()
print("Starting simulation with NVMain ReRAM config...")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
