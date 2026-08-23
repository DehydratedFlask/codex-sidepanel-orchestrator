# OpenCode Side-Panel Orchestrator

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows%20%7C%20Linux-black.svg)](#platform-support)

A Codex skill that keeps Codex in the planner's chair and delegates implementation to **your existing OpenCode side-panel session—only while that session is visibly open**.

It does not launch OpenCode, create a replacement session, refresh the panel, or quietly fall back to Codex for coding.

## Why this exists

OpenCode MCP can retain sessions after its terminal UI closes. Session history alone therefore cannot prove that the OpenCode session in the ChatGPT/Codex desktop side panel is still open.

This skill uses two independent gates before delegating:

1. A read-only process-tree check finds an interactive `opencode` TUI beneath the ChatGPT desktop app.
2. OpenCode MCP must expose an existing session for the current repository.

If either gate fails, Codex produces a plan and stops.

```mermaid
flowchart LR
    U[Your coding request] --> C[Codex inspects and plans]
    C --> L{Live OpenCode TUI\nin ChatGPT side panel?}
    L -- No --> S[Stop with plan]
    L -- Yes --> M{Matching existing\nMCP session?}
    M -- No --> S
    M -- Yes --> O[OpenCode reasons, edits, and tests]
    O --> R[Codex monitors and reports]
```

## Requirements

- macOS, Windows, or Linux for installation and detection
- ChatGPT/Codex desktop app with a side-panel terminal for live delegation
- [OpenCode](https://opencode.ai/) installed and authenticated (a fresh install is fine)
- [Codex](https://developers.openai.com/codex/) with MCP support
- Git, used by the skill installer
- Node.js 18 or newer, for `npx`
- Python 3, for the zero-dependency live-session detector
- [`opencode-mcp`](https://github.com/AlaeddineMessadi/opencode-mcp)

`opencode-mcp` is a bridge used by Codex. You do not install a skill or plugin inside OpenCode. With the `npx` configuration below, Node downloads the bridge automatically on first use.

## Quick start

### 1. Install and initialize OpenCode

If OpenCode is already installed, skip the installation command. The npm method works on macOS, Windows PowerShell, and Linux:

```bash
npm install -g opencode-ai
opencode --version
```

Run `opencode` once and complete its provider authentication before delegating work. Other official installation options are listed on the [OpenCode download page](https://dev.opencode.ai/download).

### 2. Connect OpenCode MCP to Codex

```bash
codex mcp add opencode -- npx -y opencode-mcp
```

Restart the ChatGPT/Codex desktop app after changing MCP configuration. Verify the registration with:

```bash
codex mcp list
```

For longer implementation tasks, you can set timeouts in `~/.codex/config.toml`:

```toml
[mcp_servers.opencode]
command = "npx"
args = ["-y", "opencode-mcp"]
startup_timeout_sec = 30
tool_timeout_sec = 600
default_tools_approval_mode = "writes"
```

See the official [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp) for configuration and trust guidance.

This command is sufficient for a fresh OpenCode setup; no OpenCode-side MCP skill is needed. `npx -y` fetches `opencode-mcp` when Codex starts it.

### 3. Install the skill

Install globally so it is available in every project:

```bash
npx skills add DehydratedFlask/opencode-sidepanel-orchestrator --skill opencode-sidepanel-orchestrator -g -y
```

Or omit `-g` for a project-local installation:

```bash
npx skills add DehydratedFlask/opencode-sidepanel-orchestrator --skill opencode-sidepanel-orchestrator -y
```

Restart Codex after installing a new skill.

### 4. Open the session you want Codex to use

In the ChatGPT/Codex desktop side-panel terminal:

```bash
cd /path/to/your/project
opencode
```

Leave that TUI open. The OpenCode MCP server must be able to see its existing session in the same project directory.

### 5. Delegate

Explicit invocation:

```text
Use $opencode-sidepanel-orchestrator to implement the new settings screen.
```

The skill also allows implicit invocation for coding work when your request makes the planner/delegator intent clear, for example:

```text
Plan this refactor, then have my open side-panel OpenCode session implement and test it.
```

## What it does

| Side-panel TUI | Matching MCP session | Result |
|---|---|---|
| Open | Found | Codex plans; OpenCode implements and tests; Codex monitors |
| Open | Missing | Codex stops with the plan and asks you to open/select the project session |
| Closed | Persisted session exists | Codex stops; stale history does not pass the live UI gate |
| Closed | Missing | Codex stops |
| Multiple matches | Multiple | Codex asks you to choose by title/session ID |

Codex communicates through `opencode_reply`, which continues the chosen session. It does not use session-creation tools, and it leaves the session's existing model/provider selection untouched.

## Verify the live-session detector

macOS or Linux:

```bash
python3 ~/.agents/skills/opencode-sidepanel-orchestrator/scripts/detect_sidepanel_opencode.py --pretty
```

Windows PowerShell:

```powershell
python "$HOME\.agents\skills\opencode-sidepanel-orchestrator\scripts\detect_sidepanel_opencode.py" --pretty
```

When the side-panel TUI is open, the command returns JSON with `"open": true` and exits `0`. If it is closed, it returns `"open": false` and exits `1`. Unsupported platforms or detector errors exit `2`.

The script only reads the process table. It never focuses, types into, refreshes, or closes the terminal.

## Manual installation

macOS or Linux:

```bash
git clone https://github.com/DehydratedFlask/opencode-sidepanel-orchestrator.git
mkdir -p ~/.agents/skills
cp -R opencode-sidepanel-orchestrator ~/.agents/skills/opencode-sidepanel-orchestrator
```

Windows PowerShell:

```powershell
git clone https://github.com/DehydratedFlask/opencode-sidepanel-orchestrator.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse opencode-sidepanel-orchestrator "$HOME\.agents\skills\opencode-sidepanel-orchestrator"
```

Restart Codex after copying the skill.

## Troubleshooting

### Codex says the side panel is closed

- Confirm the interactive `opencode` TUI is still visible in the desktop side-panel terminal.
- Do not confuse the MCP backend's `opencode serve` process with the TUI; the backend intentionally does not satisfy the gate.
- Run the detector command above and inspect its JSON result.

### MCP tools are unavailable

```bash
codex mcp list
npx -y opencode-mcp
```

Confirm `opencode` is on your `PATH`, then restart the desktop app. Use `Ctrl+C` to stop the second diagnostic command after it starts successfully.

For a fresh OpenCode install, this MCP registration is the only additional integration step. OpenCode itself does not need an `opencode-mcp` skill.

### No matching session is found

Start OpenCode from the same absolute project directory used by Codex. If several sessions match, tell Codex which displayed title or session ID to use.

### The skill does not appear

Restart Codex and confirm `SKILL.md` exists at:

```text
~/.agents/skills/opencode-sidepanel-orchestrator/SKILL.md
```

## Safety model

- Fails closed when live UI state cannot be proven.
- Uses an existing session; never creates, forks, deletes, reverts, aborts, or disposes one.
- Keeps Codex read-only during implementation.
- Does not commit, push, publish, deploy, or run destructive operations unless you explicitly authorize them.
- Sends only the implementation context needed for the current repository.

MCP servers can execute code with your account's permissions. Review third-party MCP source and configuration before enabling it.

## Platform support

| System | Install and run detector | Live side-panel delegation |
|---|---|---|
| macOS | Yes, using `ps` and TTY ancestry | Yes |
| Windows | Yes, using PowerShell `Win32_Process` ancestry | Yes, for native Windows terminal sessions |
| Linux | Yes, using `ps`; fails closed when no compatible host exists | No official ChatGPT desktop host currently |
| Windows + WSL OpenCode | Detector runs, but fails closed | Not currently supported because the process ancestry crosses the VM boundary |

OpenAI's current desktop documentation lists the ChatGPT/Codex app for [macOS and Windows](https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app). Other operating systems remain installable but cannot delegate without a compatible desktop side-panel host.

## Uninstall

```bash
npx skills remove opencode-sidepanel-orchestrator -g -y
```

Remove the MCP registration separately if you no longer use it:

```bash
codex mcp remove opencode
```

## Development

Run the zero-dependency unit tests and skill validator:

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

The detector accepts `--ps-file` for deterministic fixtures and debugging without touching live UI state.

## Design references

The README structure and distribution flow were informed by established agent-skill repositories such as [delegate-skills](https://github.com/amElnagdy/delegate-skills) and [terminal-control](https://github.com/anomalyco/terminal-control). Packaging follows the [Agent Skills CLI](https://skills.sh/) convention, while repository documentation follows [GitHub's README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).

## License

[MIT](LICENSE) © John Wang
