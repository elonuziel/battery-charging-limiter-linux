## Plan: Simple Battery Limit GUI

Build a small Python desktop app that reuses the existing shell scripts to set battery charge thresholds and optionally persist settings across reboot. This keeps risk low by avoiding privileged logic rewrites, while adding a clear UI for value input, current limit display, and a persistence checkbox. The app should auto-detect init system support and route to the correct persistence script.

## Steps
1. Discovery lock-in: confirm existing script behavior as execution contracts, including argument validation (1-100), root/sudo behavior, and persistence paths in `limitd.sh`, `limit_runit.sh`, and `limitrc.sh`. Completed.
2. Phase 1 - UX and flow design: define single-window UI with current limit text, numeric input/spinbox (1-100), persist checkbox, Apply button, and status/error area; map each UI action to script calls and user-visible messages. Blocks step 3.
3. Phase 2 - Runtime capability detection: add startup checks for sysfs threshold file existence and available persistence targets (systemd/runit/OpenRC script availability), then determine persistence default behavior and disable/annotate unsupported states in UI. Depends on step 2.
4. Phase 3 - Command execution layer: implement a safe subprocess wrapper that runs non-persistent or persistent script depending on checkbox; use either `pkexec` if present or `sudo` fallback; capture stdout/stderr and exit codes for UI feedback. Depends on steps 2 and 3.
5. Phase 4 - GUI implementation: build the app in Python Tkinter (recommended for simplicity and minimal dependencies), wire widgets to detection and execution layers, and refresh displayed current threshold after successful apply. Depends on steps 3 and 4.
6. Phase 5 - Integration docs: update `README.md` with GUI usage, dependency notes, privilege behavior, and examples for both one-time and persistent limit setting through the UI. Parallel with step 5 once command semantics are stable.
7. Phase 6 - Hardening pass: validate edge cases (invalid input, missing BAT path, auth cancel, unsupported init, script failure) and improve messaging; optionally document known runit-script issue for follow-up fix if encountered. Depends on steps 5 and 6.

## Relevant Files
- `limit.sh`: reuse for non-persistent apply path.
- `limitd.sh`: reuse for systemd persistence path.
- `limit_runit.sh`: reuse for runit persistence path; verify behavior and known command mismatch risk.
- `limitrc.sh`: reuse for OpenRC persistence path.
- `README.md`: add GUI section and operational notes.
- `batlimit_gui.py` (new): Tkinter GUI app and subprocess orchestration.

## Verification
1. Startup checks: run GUI on a machine with and without threshold sysfs path and confirm capability/status messaging.
2. Non-persistent apply: set a valid value with persist unchecked; verify threshold file reflects the value immediately.
3. Persistent apply: set a value with persist checked; verify selected script ran successfully and service/init registration exists for detected init system.
4. Reboot validation: reboot and confirm threshold remains at selected value.
5. Negative-path checks: test invalid input bounds, canceled auth prompt, and script execution failures; confirm clear errors and no partial success message.
6. Documentation validation: follow updated `README.md` GUI instructions on a clean shell session and confirm all steps work.

## Decisions
- Implementation language: Python.
- GUI toolkit: Tkinter (chosen because no toolkit preference was specified and the goal is a simple app).
- Persistence scope: auto-detect and support available init system paths via existing scripts.
- Privilege model: prefer `pkexec` if available, fallback to `sudo` prompts.
- Included scope: local desktop GUI for setting threshold and persistence toggle.
- Excluded scope: daemon/service rewrite, D-Bus API, package manager integration, and redesign of existing CLI scripts.

## Further Considerations
1. If `limit_runit.sh` fails due to systemctl usage in runit flow, include a small corrective patch in the same implementation cycle to keep GUI persistence reliable on runit systems.
2. If Tkinter rendering feels too basic, a later enhancement can migrate the UI layer to PySide without changing command execution logic.
