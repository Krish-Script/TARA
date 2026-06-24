"""
Returns hardware metrics as structured dicts.
Formatting is handled by ToolFormatter — not here.

Queries supported:
  cpu        → usage percent, core count, frequency
  ram        → used/total GB, percent
  disk       → used/free GB, percent (C: drive)
  battery    → percent, charging state
  vram       → used/total GB, GPU temperature, utilization
  temperature→ GPU temp (pynvml), CPU temp (psutil, likely unavailable on Windows)
  uptime     → hours and minutes since last boot
  status     → all of the above in one call

Thermal-aware operation:
  GPU temperature via pynvml — reliable on RTX hardware.
  CPU temperature via psutil.sensors_temperatures() — often
  unavailable on Windows without third-party drivers. Returns
  "unavailable" gracefully rather than failing or guessing.
  This makes the "thermal-aware" design claim in the project
  objective honest within Windows hardware constraints.

Design decisions:
  - cpu_percent() warm-up call in __init__ — first call always
    returns 0.0 (psutil measures delta since last call; there is
    no previous call on first use). Discarding it here means all
    subsequent calls are accurate.
  - nvml_available flag — set once in __init__, checked before
    every pynvml call. Never raises outside __init__.
  - All sub-methods return {} on failure, never None.
    Empty dict → formatter returns graceful fallback string.
"""

import time

import psutil


class SystemMonitor:

    def __init__(self):
        # Warm up CPU percent — discard the always-zero first reading
        psutil.cpu_percent(interval=0.1)

        # Initialise NVML — set flag, never raise after this point
        self.nvml_available = False
        self._nvml_handle   = None
        self._init_nvml()

    def _init_nvml(self):
        """Attempt NVML init. Sets self.nvml_available = True on success."""
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_handle   = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.nvml_available = True
            print("[SYS] NVML initialised ✓  (GPU metrics available)")
        except Exception as e:
            print(f"[SYS] NVML unavailable: {e}")
            print("[SYS] GPU metrics will be skipped.")

    # ── Public API ───────────────────────────────────────────

    def run(self, query: str) -> dict:
        """
        Dispatch to the correct sub-method based on keywords in query.
        Falls back to _get_all() for ambiguous or status queries.
        """
        lower = query.lower()

        dispatch = [
            (["vram", "gpu memory", "graphics memory"], self._get_vram),
            (["temperature", "temp", "thermal", "hot", "heat"],
                                                          self._get_temperature),
            (["cpu", "processor", "processing"],          self._get_cpu),
            (["ram", "memory usage", "how much memory"],  self._get_ram),
            (["disk", "storage", "drive", "space"],       self._get_disk),
            (["battery", "charge", "charging"],           self._get_battery),
            (["uptime", "how long", "running since"],     self._get_uptime),
            (["status", "stats", "everything", "all"],    self._get_all),
        ]

        for keywords, method in dispatch:
            if any(kw in lower for kw in keywords):
                return method()

        # No keyword matched — return full status
        return self._get_all()

    # ── Sub-methods ──────────────────────────────────────────

    def _get_cpu(self) -> dict:
        """CPU usage, core count, and current frequency."""
        try:
            usage   = psutil.cpu_percent(interval=0.1)
            cores   = psutil.cpu_count(logical=False)
            threads = psutil.cpu_count(logical=True)
            freq    = psutil.cpu_freq()

            return {
                "cpu_percent":   usage,
                "cpu_cores":     cores,
                "cpu_threads":   threads,
                "cpu_freq_mhz":  round(freq.current) if freq else None,
            }
        except Exception:
            return {}

    def _get_ram(self) -> dict:
        """RAM usage in GB and percent."""
        try:
            mem = psutil.virtual_memory()
            return {
                "ram_used_gb":  round(mem.used  / 1024**3, 1),
                "ram_total_gb": round(mem.total / 1024**3, 1),
                "ram_percent":  mem.percent,
            }
        except Exception:
            return {}

    def _get_disk(self) -> dict:
        """C: drive usage in GB and percent."""
        try:
            disk = psutil.disk_usage("C:\\")
            return {
                "disk_used_gb":  round(disk.used  / 1024**3, 1),
                "disk_total_gb": round(disk.total / 1024**3, 1),
                "disk_free_gb":  round(disk.free  / 1024**3, 1),
                "disk_percent":  disk.percent,
            }
        except Exception:
            return {}

    def _get_battery(self) -> dict:
        """Battery percent and charging state. Returns {} on desktops."""
        try:
            batt = psutil.sensors_battery()
            if batt is None:
                return {"battery_available": False}
            return {
                "battery_percent":  round(batt.percent, 1),
                "charging":         batt.power_plugged,
                "battery_available": True,
            }
        except Exception:
            return {}

    def _get_vram(self) -> dict:
        """GPU VRAM usage and utilization via pynvml."""
        if not self.nvml_available:
            return {"vram_available": False}
        try:
            import pynvml
            mem  = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
            return {
                "vram_used_gb":    round(float(mem.used)  / 1024**3, 2),
                "vram_total_gb":   round(float(mem.total) / 1024**3, 2),
                "vram_free_gb":    round(float(mem.free)  / 1024**3, 2),
                "vram_percent":    round(float(mem.used) / float(mem.total) * 100, 1),
                "gpu_util_percent": util.gpu,
                "vram_available":  True,
            }
        except Exception:
            return {"vram_available": False}

    def _get_temperature(self) -> dict:
        """
        Thermal-aware operation implementation.

        GPU temperature: pynvml — reliable on RTX hardware.
        CPU temperature: psutil.sensors_temperatures() — often
        unavailable on Windows without third-party drivers.
        Reports 'unavailable' gracefully rather than failing.
        """
        result = {}

        # GPU temperature via NVML
        if self.nvml_available:
            try:
                import pynvml
                gpu_temp = pynvml.nvmlDeviceGetTemperature(
                    self._nvml_handle,
                    pynvml.NVML_TEMPERATURE_GPU,
                )
                result["gpu_temp_c"]       = gpu_temp
                result["gpu_temp_available"] = True
            except Exception:
                result["gpu_temp_available"] = False
        else:
            result["gpu_temp_available"] = False

        # CPU temperature via psutil
        # Returns empty dict on most Windows systems without
        # third-party sensor drivers — this is expected, not a bug.
        try:
            if not hasattr(psutil, "sensors_temperatures"):
                result["cpu_temp_available"] = False
            else:
                temps = psutil.sensors_temperatures() # type: ignore
            if temps:
                # Try common sensor keys — varies by hardware
                for key in ("coretemp", "cpu_thermal", "k10temp", "acpitz"):
                    if key in temps and temps[key]:
                        result["cpu_temp_c"]        = round(
                            temps[key][0].current, 1
                        )
                        result["cpu_temp_available"] = True
                        break
                else:
                    result["cpu_temp_available"] = False
            else:
                result["cpu_temp_available"] = False
        except Exception:
            result["cpu_temp_available"] = False

        return result

    def _get_uptime(self) -> dict:
        """System uptime since last boot."""
        try:
            uptime_secs = time.time() - psutil.boot_time()
            hours       = int(uptime_secs // 3600)
            minutes     = int((uptime_secs % 3600) // 60)
            return {
                "uptime_hours":   hours,
                "uptime_minutes": minutes,
                "uptime_seconds": int(uptime_secs),
            }
        except Exception:
            return {}

    def _get_all(self) -> dict:
        """Full system status — merges all sub-method results."""
        result = {}
        for method in [
            self._get_cpu,
            self._get_ram,
            self._get_disk,
            self._get_battery,
            self._get_vram,
            self._get_temperature,
            self._get_uptime,
        ]:
            result.update(method())
        return result