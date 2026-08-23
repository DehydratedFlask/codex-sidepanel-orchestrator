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

3. Continue only when the detector exits `0`, returns `"open": true`, and returns `"control_ready": true`. Control readiness means exactly one side-panel TUI exists and it was launched with `opencode attach <url>`. If the TUI is missing, unattached, or ambiguous, give the plan and the shared-server setup commands from the README. Never launch, restart, focus, or replace OpenCode yourself.
4. Confirm the OpenCode MCP tools are available and healthy. A fresh OpenCode install does not include this MCP bridge. The bridge must use the same URL reported in `attached[0].url`, with `OPENCODE_AUTO_SERVE=false`; otherwise its auto-started server shares persisted sessions but cannot control this TUI. If tools are absent or the URLs cannot be proven equal, stop after the plan and give the shared-server setup commands. No OpenCode-side skill or plugin is required. Never install or configure it without the user's request.
5. Use the OpenCode MCP session-list or overview tool with the repository's absolute directory. Select an existing session belonging to that directory.
   - No matching session: stop and ask the user to open one in that project.
   - One matching session: use it.
   - Multiple matching sessions: show their titles and IDs and ask the user which one to use. Do not guess.
   - Busy session: wait or report that it is busy; do not inject work blindly.
6. Send the brief through the shared server's TUI controls: first `opencode_tui_append_prompt`, then `opencode_tui_submit_prompt`. These controls preserve the TUI's selected model and agent. Do not use `opencode_reply` for side-panel orchestration: it is a headless session API and may require a separate provider/model selection. Do not clear or overwrite prompt text. If the prompt is not known to be empty, stop and ask the user to clear or submit it first. Do not use tools that create, fork, delete, revert, abort, or dispose sessions.
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

All three gates must pass for every delegation:

- **Live UI gate:** the detector must find exactly one interactive `opencode attach <url>` process beneath the ChatGPT desktop app, using a real TTY on POSIX systems or the native Windows process tree.
- **Session gate:** the MCP server must expose a matching existing session for the current repository.
- **Shared-server gate:** the MCP bridge and attached TUI must use the same OpenCode server URL, and MCP auto-serve must be disabled.

Persisted MCP sessions do not prove the side panel is open or controllable. A separate headless server may see the same session database while its TUI event channel has no side-panel subscriber.

## Safety Rules

- Keep Codex operations read-only apart from communicating through the selected OpenCode session.
- Never start a new OpenCode session, terminal, server, or replacement workflow.
- Never focus, refresh, close, or send OS-level keystrokes to the side panel. Use only the shared server's TUI API after all gates pass.
- Never delegate secrets or unrelated repository content.
- Never commit, push, publish, deploy, or perform destructive actions unless the user explicitly authorized them.
- If any gate fails mid-task, stop delegation and preserve the current session.

## Platform

The detector runs on macOS, Linux, and Windows using only Python's standard library. Official ChatGPT/Codex desktop hosting is currently available on macOS and Windows. Native Windows terminals are supported; WSL processes cannot be reliably correlated to their Windows side-panel process and therefore fail closed. Linux can install and run the skill, but delegation requires a compatible ChatGPT desktop host.
