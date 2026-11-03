"""What this machine is: CPU, usable threads, memory, and the code it can run.

Everything here reads kernel interfaces as data and takes its paths as
parameters, so tests can describe any host. Only `read_cpu` raises: every CPU
target needs to know the CPU, while the cgroup and memory readings are limits
that simply do not apply when they are absent.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import BuildError
from .exec import Runner

GIB = 1024**3
# Gentoo's handbook sizes parallel builds at about 2 GiB of memory per job; the
# heaviest C++ translation units here (x265, libjxl's highway, SVT-AV1) approach
# that, and one job killed for memory fails the whole build.
MEMORY_PER_JOB = 2 * GIB

# The x86-64 psABI microarchitecture levels, in /proc/cpuinfo's flag names
# (`pni` is SSE3, `abm` is LZCNT). Each level includes the ones before it.
ISA_LEVELS = (
    ("x86-64-v2", frozenset({"cx16", "lahf_lm", "popcnt", "pni", "sse4_1", "sse4_2", "ssse3"})),
    (
        "x86-64-v3",
        frozenset({"abm", "avx", "avx2", "bmi1", "bmi2", "f16c", "fma", "movbe", "xsave"}),
    ),
    ("x86-64-v4", frozenset({"avx512bw", "avx512cd", "avx512dq", "avx512f", "avx512vl"})),
)
# The instruction-set extensions `-march=native` can enable. The CPU identity
# covers only these: a kernel that learns to name more flags must not read as a
# different CPU, while a virtual machine that hides AVX-512 must.
ISA_EXTENSION_FLAGS = frozenset(
    {
        "adx",
        "aes",
        "amx_bf16",
        "amx_complex",
        "amx_fp16",
        "amx_int8",
        "amx_tile",
        "avx",
        "avx2",
        "avx512_bf16",
        "avx512_bitalg",
        "avx512_fp16",
        "avx512_vbmi2",
        "avx512_vnni",
        "avx512_vp2intersect",
        "avx512_vpopcntdq",
        "avx512bw",
        "avx512cd",
        "avx512dq",
        "avx512f",
        "avx512ifma",
        "avx512vbmi",
        "avx512vl",
        "avx_ifma",
        "avx_ne_convert",
        "avx_vnni",
        "avx_vnni_int8",
        "abm",
        "bmi1",
        "bmi2",
        "clflushopt",
        "clwb",
        "clzero",
        "cx16",
        "f16c",
        "fma",
        "fma4",
        "fsgsbase",
        "gfni",
        "lahf_lm",
        "movbe",
        "movdir64b",
        "movdiri",
        "mwaitx",
        "pclmulqdq",
        "pku",
        "pni",
        "popcnt",
        "prefetchw",
        "rdpid",
        "rdrand",
        "rdseed",
        "serialize",
        "sha_ni",
        "sse",
        "sse2",
        "sse4_1",
        "sse4_2",
        "sse4a",
        "ssse3",
        "tbm",
        "vaes",
        "vpclmulqdq",
        "waitpkg",
        "wbnoinvd",
        "xop",
        "xsave",
        "xsavec",
        "xsaveopt",
        "xsaves",
    }
)


@dataclass(frozen=True)
class HostCpu:
    vendor: str
    model_name: str
    family: str
    model: str
    flags: frozenset[str]

    @property
    def isa_level(self) -> str:
        """The highest psABI level this CPU implements; `x86-64` is the baseline."""
        level = "x86-64"
        required: set[str] = set()
        for name, flags in ISA_LEVELS:
            required |= flags
            if not required <= self.flags:
                break
            level = name
        return level

    @property
    def identity(self) -> str:
        """What `-march=native` code depends on, readable in a mismatch message.

        Family and model decide `-mtune=native`; the extension set decides which
        instructions the build may emit. The digest keeps the record one line.
        """
        extensions = " ".join(sorted(self.flags & ISA_EXTENSION_FLAGS))
        digest = hashlib.sha256(extensions.encode()).hexdigest()[:12]
        return (
            f"{self.model_name} ({self.vendor} family {self.family} model {self.model}, "
            f"{self.isa_level}, isa {digest})"
        )


def read_cpu(path: Path = Path("/proc/cpuinfo")) -> HostCpu:
    """Describe the first logical CPU; every CPU in a Linux system reports the same ISA."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise BuildError(f"Unable to read '{path}' to identify this CPU: {error}") from error
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if fields:
                break
            continue
        key, separator, value = line.partition(":")
        if separator:
            fields.setdefault(key.strip(), value.strip())
    if "flags" not in fields:
        raise BuildError(f"'{path}' does not list this CPU's instruction-set flags.")
    return HostCpu(
        vendor=fields.get("vendor_id", "unknown"),
        model_name=" ".join(fields.get("model name", "unknown CPU").split()),
        family=fields.get("cpu family", "?"),
        model=fields.get("model", "?"),
        flags=frozenset(fields["flags"].split()),
    )


def target_isa_level(cpu_target: str) -> str:
    """The psABI level a CPU target's code requires; native requires this CPU."""
    return "x86-64" if cpu_target == "generic" else cpu_target


def isa_level_rank(level: str) -> int:
    names = ["x86-64", *(name for name, _ in ISA_LEVELS)]
    return names.index(level)


def march(cpu_target: str) -> str:
    """The `-march`/`--cpu`/`target-cpu` value for a CPU target."""
    return target_isa_level(cpu_target) if cpu_target != "native" else "native"


def _cgroup_directories(proc_cgroup: Path, cgroup_root: Path) -> list[Path]:
    """This process's cgroup v2 directory and its ancestors, innermost first.

    A limit anywhere up the tree applies, so every level is read. cgroup v1 has
    no single hierarchy to walk and is the default on no supported release.
    """
    try:
        text = proc_cgroup.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        if line.startswith("0::"):
            relative = line[3:].strip().lstrip("/")
            directory = cgroup_root / relative if relative else cgroup_root
            directories = [directory]
            while directory != cgroup_root and cgroup_root in directory.parents:
                directory = directory.parent
                directories.append(directory)
            return directories
    return []


def _read_first_line(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def cgroup_cpu_limit(
    proc_cgroup: Path = Path("/proc/self/cgroup"), cgroup_root: Path = Path("/sys/fs/cgroup")
) -> int | None:
    """CPUs a cgroup v2 `cpu.max` quota allows, rounded up; None when unlimited."""
    limit: int | None = None
    for directory in _cgroup_directories(proc_cgroup, cgroup_root):
        value = _read_first_line(directory / "cpu.max")
        if value is None:
            continue
        match = re.fullmatch(r"([0-9]+) ([0-9]+)", value)
        if match is None or int(match.group(2)) == 0:
            continue
        cpus = max(1, math.ceil(int(match.group(1)) / int(match.group(2))))
        limit = cpus if limit is None else min(limit, cpus)
    return limit


@dataclass(frozen=True)
class HostMemory:
    total: int
    available: int
    # The tightest cgroup v2 `memory.max`, when one is below physical memory.
    cgroup_limit: int | None


def read_memory(
    meminfo: Path = Path("/proc/meminfo"),
    proc_cgroup: Path = Path("/proc/self/cgroup"),
    cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> HostMemory | None:
    """Physical and available memory, with any cgroup v2 limit applied."""
    try:
        text = meminfo.read_text(encoding="utf-8")
    except OSError:
        return None
    values: dict[str, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"(MemTotal|MemAvailable):\s+([0-9]+) kB", line.strip())
        if match is not None:
            values[match.group(1)] = int(match.group(2)) * 1024
    if "MemTotal" not in values or "MemAvailable" not in values:
        return None
    total = values["MemTotal"]
    available = values["MemAvailable"]
    limit: int | None = None
    for directory in _cgroup_directories(proc_cgroup, cgroup_root):
        maximum = _read_first_line(directory / "memory.max")
        current = _read_first_line(directory / "memory.current")
        if maximum is None or not maximum.isdigit():
            continue
        if limit is None or int(maximum) < limit:
            limit = int(maximum)
        if current is not None and current.isdigit():
            available = min(available, max(0, int(maximum) - int(current)))
    if limit is not None and limit >= total:
        limit = None
    return HostMemory(total=total, available=available, cgroup_limit=limit)


def usable_threads() -> int:
    """Threads this process may run on; under `taskset -c 0,1` that is 2, not 24."""
    return len(os.sched_getaffinity(0))


@dataclass(frozen=True)
class JobPlan:
    jobs: int
    reason: str


def plan_jobs(
    requested: int | None, threads: int, cpu_limit: int | None, memory: HostMemory | None
) -> JobPlan:
    """Parallel jobs: the request, or every usable thread that memory can feed."""
    if requested is not None:
        return JobPlan(requested, "--jobs")
    usable = threads if cpu_limit is None else min(threads, cpu_limit)
    if cpu_limit is not None and cpu_limit < threads:
        reason = f"cgroup CPU quota of {cpu_limit}"
    else:
        reason = f"{usable} usable CPU threads"
    if memory is None:
        return JobPlan(usable, f"{reason}; free memory unknown")
    memory_jobs = max(1, memory.available // MEMORY_PER_JOB)
    if memory_jobs < usable:
        return JobPlan(memory_jobs, f"{reason}, limited by free memory at 2 GiB per job")
    return JobPlan(usable, f"{reason}; memory allows {memory_jobs}")


def format_gib(size: int) -> str:
    return f"{size / GIB:.1f} GiB"


def compiler_cpu_target(runner: Runner, compiler: str, command: str) -> str | None:
    """The CPU the compiler resolves `-march=native` to; None when it cannot say."""
    if compiler == "gcc":
        result = runner.capture([command, "-march=native", "-Q", "--help=target"], timeout=30)
        match = re.search(r"^\s+-march=\s+(\S+)\s*$", result.stdout, re.MULTILINE)
    else:
        result = runner.capture(
            [command, "-march=native", "-###", "-x", "c", "-c", "/dev/null", "-o", "/dev/null"],
            timeout=30,
        )
        match = re.search(r'"-target-cpu" "([^"]+)"', result.stderr)
    if result.returncode != 0 or match is None:
        return None
    return match.group(1)
