# WipeLock for Windows

WipeLock is a small Windows utility that temporarily blocks keyboard and mouse input while a visible countdown is running.

## Safety

- Emergency unlock shortcut: **Ctrl + Alt + W**.
- The timer automatically unlocks when it reaches zero.
- The lock is limited to a maximum of five minutes.
- The application must be tested on the target Windows system before relying on it. Do not use it on a shared or managed computer.

## Build

The GitHub Actions workflow builds `WipeLock.exe` on Windows and publishes it as a prerelease asset.

