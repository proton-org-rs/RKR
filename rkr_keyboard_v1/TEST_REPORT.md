# Validation report

- 16 Python unit tests passed: motion logic, limits, watchdog simulation, curl endpoints, preset completion/dwell, configuration validation, keyboard repeat, stop latch and focus loss.
- Actual firmware sketch compiled with host g++ using -Wall -Wextra -Werror and Arduino stubs; native harness passed protocol, pulse counting, travel limits, mid-move stop, watchdog and oversized-line checks.
- Python syntax compilation and CLI help passed.
- All six legacy files match uploaded originals byte-for-byte.

Not performed: compilation for a selected Arduino target, flashing, physical motor/cable tests, rendered desktop GUI tests, or current-sensor measurements. Host compilation does not prove board compatibility or real-time electrical behavior.
