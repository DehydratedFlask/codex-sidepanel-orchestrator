#!/usr/bin/env python3
"""Detect a live OpenCode TUI owned by the ChatGPT desktop app on macOS."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass


CHATGPT_MARKERS = (
    "/Applications/ChatGPT.app/Contents/MacOS/ChatGPT",
    "/ChatGPT.app/Contents/MacOS/ChatGPT",
)
NON_TTYS = {"", "?", "??", "-"}


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    tty: str
    command: str


def parse_processes(output: str) -> dict[int, Process]:
    """Parse `ps -axo pid=,ppid=,tty=,command=` output."""
    processes: dict[int, Process] = {}
    for raw_line in output.splitlines():
        parts = raw_line.strip().split(None, 3)
        if len(parts) != 4:
            continue
        pid_text, ppid_text, tty, command = parts
        try:
            process = Process(int(pid_text), int(ppid_text), tty, command)
        except ValueError:
            continue
        processes[process.pid] = process
    return processes


def is_opencode_tui(process: Process) -> bool:
    if process.tty in NON_TTYS:
        return False
    executable, *arguments = process.command.split()
    if os.path.basename(executable) != "opencode":
        return False
    return not arguments or arguments[0] not in {"serve", "run"}


def has_chatgpt_ancestor(process: Process, processes: dict[int, Process]) -> bool:
    seen: set[int] = set()
    parent_id = process.ppid
    while parent_id > 0 and parent_id not in seen:
        seen.add(parent_id)
        parent = processes.get(parent_id)
        if parent is None:
            return False
        if any(marker in parent.command for marker in CHATGPT_MARKERS):
            return True
        parent_id = parent.ppid
    return False


def find_sidepanel_processes(processes: dict[int, Process]) -> list[Process]:
    return [
        process
        for process in processes.values()
        if is_opencode_tui(process) and has_chatgpt_ancestor(process, processes)
    ]


def read_process_table(ps_file: Path | None) -> str:
    if ps_file is not None:
        return ps_file.read_text(encoding="utf-8")
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,tty=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def emit(payload: dict[str, object], pretty: bool) -> None:
    print(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ps-file", type=Path, help="Read a saved ps table (for testing)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    if args.ps_file is None and platform.system() != "Darwin":
        emit({"open": False, "reason": "unsupported_platform", "platform": platform.system()}, args.pretty)
        return 2

    try:
        processes = parse_processes(read_process_table(args.ps_file))
        matches = find_sidepanel_processes(processes)
    except (OSError, subprocess.SubprocessError) as error:
        emit({"open": False, "reason": "detector_error", "error": str(error)}, args.pretty)
        return 2

    emit(
        {
            "open": bool(matches),
            "reason": "live_sidepanel_tui" if matches else "no_live_sidepanel_tui",
            "processes": [asdict(process) for process in matches],
        },
        args.pretty,
    )
    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())
