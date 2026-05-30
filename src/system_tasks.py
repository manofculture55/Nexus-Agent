"""
system_tasks.py — NEXUS System Tasks
Provides functions to query system information like battery status
and running processes, and to execute safe system commands (shutdown,
restart, sleep) with confirmation prompts. Uses psutil and subprocess.
"""

import psutil
import datetime
import subprocess


# ---------------------------------------------------------------------------
# Battery status
# ---------------------------------------------------------------------------
def get_battery():
    """
    Return a formatted string showing battery percentage and charging status.
    Handles desktop PCs that have no battery gracefully.
    """
    battery = psutil.sensors_battery()

    if battery is None:
        return "No battery detected. This appears to be a desktop PC (always on AC power)."

    percent = battery.percent
    plugged = battery.power_plugged
    status = "Charging" if plugged else "Discharging"

    # Estimate time remaining (only meaningful when discharging)
    time_info = ""
    if not plugged and battery.secsleft not in (
        psutil.POWER_TIME_UNLIMITED,
        psutil.POWER_TIME_UNKNOWN,
    ):
        remaining = str(datetime.timedelta(seconds=battery.secsleft))
        time_info = f" | Estimated time remaining: {remaining}"

    return f"Battery: {percent}% | Status: {status}{time_info}"


# ---------------------------------------------------------------------------
# Running processes (top 10 by memory)
# ---------------------------------------------------------------------------
def get_processes():
    """
    Return a formatted string listing the top 10 processes by RAM usage.
    Handles AccessDenied exceptions for protected system processes.
    """
    processes = []

    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = proc.info
            mem = info["memory_info"]
            if mem is not None:
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "ram_bytes": mem.rss,
                })
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            # Skip processes we can't access
            continue

    # Sort by RAM usage descending and take top 10
    processes.sort(key=lambda p: p["ram_bytes"], reverse=True)
    top10 = processes[:10]

    if not top10:
        return "Could not retrieve process information."

    lines = ["Top 10 Processes by Memory Usage:", ""]
    for i, p in enumerate(top10, 1):
        ram_mb = p["ram_bytes"] / (1024 * 1024)
        lines.append(
            f"  {i:2d}. {p['name']:<30s} | PID: {p['pid']:<8d} | RAM: {ram_mb:.1f} MB"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System commands — shutdown, restart, sleep (Phase 17)
# ---------------------------------------------------------------------------
def shutdown_system():
    """
    Shut down the computer after a 30-second delay.
    Asks for user confirmation before executing.
    The user can cancel with 'shutdown /a' within 30 seconds.
    """
    print()
    print("  [WARNING] This will SHUT DOWN your computer in 30 seconds.")
    print("  You can cancel within 30 seconds by running: shutdown /a")
    print()
    confirm = input("  Are you sure you want to shut down? (y/n): ").strip().lower()

    if confirm != "y":
        return "Shutdown cancelled."

    try:
        subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
        return ("Shutdown initiated. Your computer will shut down in 30 seconds.\n"
                "To cancel, type 'cancel shutdown' or run: shutdown /a")
    except subprocess.CalledProcessError as e:
        return f"Failed to initiate shutdown: {e}"
    except Exception as e:
        return f"Error: {e}"


def restart_system():
    """
    Restart the computer after a 30-second delay.
    Asks for user confirmation before executing.
    """
    print()
    print("  [WARNING] This will RESTART your computer in 30 seconds.")
    print("  You can cancel within 30 seconds by running: shutdown /a")
    print()
    confirm = input("  Are you sure you want to restart? (y/n): ").strip().lower()

    if confirm != "y":
        return "Restart cancelled."

    try:
        subprocess.run(["shutdown", "/r", "/t", "30"], check=True)
        return ("Restart initiated. Your computer will restart in 30 seconds.\n"
                "To cancel, type 'cancel shutdown' or run: shutdown /a")
    except subprocess.CalledProcessError as e:
        return f"Failed to initiate restart: {e}"
    except Exception as e:
        return f"Error: {e}"


def sleep_system():
    """
    Put the computer to sleep immediately.
    Asks for user confirmation before executing.
    """
    print()
    print("  [WARNING] This will put your computer to SLEEP.")
    print()
    confirm = input("  Are you sure you want to sleep? (y/n): ").strip().lower()

    if confirm != "y":
        return "Sleep cancelled."

    try:
        subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            check=True,
        )
        return "Sleep command sent."
    except subprocess.CalledProcessError as e:
        return f"Failed to put system to sleep: {e}"
    except Exception as e:
        return f"Error: {e}"


def cancel_shutdown():
    """
    Cancel a pending shutdown or restart using 'shutdown /a'.
    """
    try:
        subprocess.run(["shutdown", "/a"], check=True)
        return "Pending shutdown/restart has been cancelled."
    except subprocess.CalledProcessError:
        return "No pending shutdown or restart to cancel."
    except Exception as e:
        return f"Error: {e}"
