#!/usr/bin/env python3
"""Detect a live OpenCode TUI owned by the ChatGPT desktop app."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass


NON_TTYS = {"", "?", "??", "-"}
SUPPORTED_SYSTEMS = {"Darwin", "Linux", "Windows"}


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    tty: str
    command: str
    name: str = ""


def parse_processes(output: str) -> dict[int, Process]:
    """Parse `ps -axo pid=,ppid=,tty=,command=` output."""
    processes: dict[int, Process] = {}
    for raw_line in output.splitlines():
        parts = raw_line.strip().split(None, 3)
        if len(parts) != 4:
            continue
        pid_text, ppid_text, tty, command = parts
        try:
            process = Process(
                int(pid_text),
                int(ppid_text),
                tty,
                command,
                os.path.basename(command.split()[0]),
            )
        except ValueError:
            continue
        processes[process.pid] = process
    return processes


def parse_windows_processes(output: str) -> dict[int, Process]:
    """Parse PowerShell's JSON representation of Win32_Process objects."""
    items = json.loads(output)
    if isinstance(items, dict):
        items = [items]
    processes: dict[int, Process] = {}
    for item in items:
        try:
            pid = int(item["ProcessId"])
            process = Process(
                pid,
                int(item.get("ParentProcessId") or 0),
                "windows",
                item.get("CommandLine") or item.get("Name") or "",
                item.get("Name") or "",
            )
        except (KeyError, TypeError, ValueError):
            continue
        processes[pid] = process
    return processes


def executable_name(process: Process) -> str:
    name = process.name or process.command.split()[0]
    return name.strip('"').replace("\\", "/").rsplit("/", 1)[-1].lower()


def is_chatgpt(process: Process) -> bool:
    return executable_name(process) in {"chatgpt", "chatgpt.exe"}


def is_opencode_tui(process: Process) -> bool:
    if process.tty in NON_TTYS:
        return False
    if executable_name(process) not in {"opencode", "opencode.exe", "opencode.cmd"}:
        return False
    return re.search(r"\bopencode(?:\.exe|\.cmd)?[\"']?\s+(?:serve|run)\b", process.command, re.I) is None


def has_chatgpt_ancestor(process: Process, processes: dict[int, Process]) -> bool:
    seen: set[int] = set()
    parent_id = process.ppid
    while parent_id > 0 and parent_id not in seen:
        seen.add(parent_id)
        parent = processes.get(parent_id)
        if parent is None:
            return False
        if is_chatgpt(parent):
            return True
        parent_id = parent.ppid
    return False


def find_sidepanel_processes(processes: dict[int, Process]) -> list[Process]:
    return [
        process
        for process in processes.values()
        if is_opencode_tui(process) and has_chatgpt_ancestor(process, processes)
    ]


def read_process_table(ps_file: Path | None, system: str) -> str:
    if ps_file is not None:
        return ps_file.read_text(encoding="utf-8")
    if system == "Windows":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            raise OSError("PowerShell is required for Windows process detection")
        command = [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress",
        ]
    else:
        command = ["ps", "-axo", "pid=,ppid=,tty=,command="]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def read_processes(ps_file: Path | None, system: str) -> dict[int, Process]:
    output = read_process_table(ps_file, system)
    return parse_windows_processes(output) if system == "Windows" else parse_processes(output)


def emit(payload: dict[str, object], pretty: bool) -> None:
    print(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ps-file", type=Path, help="Read a saved process table (for testing)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    system = platform.system()
    if system not in SUPPORTED_SYSTEMS:
        emit({"open": False, "reason": "unsupported_platform", "platform": system}, args.pretty)
        return 2

    try:
        processes = read_processes(args.ps_file, system)
        matches = find_sidepanel_processes(processes)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        emit({"open": False, "reason": "detector_error", "error": str(error)}, args.pretty)
        return 2

    emit(
        {
            "open": bool(matches),
            "reason": "live_sidepanel_tui" if matches else "no_live_sidepanel_tui",
            "processes": [asdict(process) for process in matches],
            "platform": system,
        },
        args.pretty,
    )
    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())
