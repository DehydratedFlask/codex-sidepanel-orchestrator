---
name: codex-sidepanel-orchestrator
description: Plan coding work in Codex and delegate reasoning, edits, and tests to an existing OpenCode session only while an OpenCode TUI is live in the ChatGPT/Codex desktop side-panel terminal. Use for implementation, refactoring, debugging, or test-writing requests when the user wants Codex to orchestrate instead of code. Do not use for non-coding tasks, review-only requests, or when the user explicitly asks Codex to implement directly.
---

# Codex Side-Panel Orchestrator

Act as the planner and supervisor. Delegate implementation to the user's existing OpenCode side-panel session. Never silently replace that session or fall back to coding in Codex.

## Workflow

1. Inspect the repository read-only and turn the request into a concrete plan with acceptance criteria and verification commands. Do not edit files.
2. Resolve this skill's directory, then run the detector with the available Python 3 launcher (`python3` on macOS/Linux, usually `python` on Windows):

   ```bash
   python3 <skill-directory>/scripts/detect_sidepanel_opencode.py
   ```

3. Continue only when the detector exits `0` and returns `"open": true`. If it exits `1`, give the plan to the user and ask them to open OpenCode in the ChatGPT/Codex side-panel terminal. If it exits `2`, report the unsupported platform or detector error. Never launch OpenCode yourself.
4. Confirm the OpenCode MCP tools are available. A fresh OpenCode install does not include this MCP bridge. If the tools are absent or unhealthy, stop after the plan and tell the user to run `codex mcp add opencode -- npx -y opencode-mcp`, then restart Codex. No OpenCode-side skill or plugin is required. Never install or configure it without the user's request.
5. Use the OpenCode MCP session-list or overview tool with the repository's absolute directory. Select an existing session belonging to that directory.
   - No matching session: stop and ask the user to open one in that project.
   - One matching session: use it.
   - Multiple matching sessions: show their titles and IDs and ask the user which one to use. Do not guess.
   - Busy session: wait or report that it is busy; do not inject work blindly.
6. Continue the selected session with the MCP `opencode_reply` tool. Do not use tools that create, fork, delete, revert, abort, or dispose sessions. Do not override the session's provider, model, variant, or agent unless the user explicitly requests it.
7. Send a compact implementation brief containing:
   - objective and user-visible outcome;
   - relevant repository context;
   - ordered plan;
   - constraints and files that must remain untouched;
   - acceptance criteria and exact verification commands;
   - an instruction to reason, edit, and test, but not commit or push unless the user asked.
8. Monitor through MCP using status/check/wait tools. Inspect results and repository changes read-only. If acceptance criteria are unmet, send a focused correction through the same session. Do not implement the correction yourself.
9. Report the outcome, files changed, tests run, and unresolved risks. State clearly that OpenCode performed the implementation.

## Hard Gates

Both gates must pass for every delegation:

- **Live UI gate:** the detector must find an interactive `opencode` process beneath the ChatGPT desktop app, using a real TTY on POSIX systems or the native Windows process tree.
- **Session gate:** the MCP server must expose a matching existing session for the current repository.

Persisted MCP sessions do not prove the side panel is open. A headless `opencode serve` process does not pass the live UI gate.

## Safety Rules

- Keep Codex operations read-only apart from communicating through the selected OpenCode session.
- Never start a new OpenCode session, terminal, server, or replacement workflow.
- Never focus, refresh, close, or send keystrokes to the side panel.
- Never delegate secrets or unrelated repository content.
- Never commit, push, publish, deploy, or perform destructive actions unless the user explicitly authorized them.
- If any gate fails mid-task, stop delegation and preserve the current session.

## Platform

The detector runs on macOS, Linux, and Windows using only Python's standard library. Official ChatGPT/Codex desktop hosting is currently available on macOS and Windows. Native Windows terminals are supported; WSL processes cannot be reliably correlated to their Windows side-panel process and therefore fail closed. Linux can install and run the skill, but delegation requires a compatible ChatGPT desktop host.
