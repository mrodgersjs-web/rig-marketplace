"""Built-in command policy for done-tests.

A pack declares the executables it needs in ``permissions.commands``. That list is capped by
this module: only executables in ``BUILTIN_ALLOWED`` may be declared, and shells, file
removers, network clients and similar tools are named in ``FORBIDDEN`` so the error says why.
The argument shape of each allowed executable is also restricted.
"""

from __future__ import annotations

from pathlib import PurePosixPath

# Every executable a done-test may start. Placeholders are substituted by the runner.
BUILTIN_ALLOWED = frozenset({"{python}"})

# Never allowed, even if a pack declares them. Matched on the basename of argv[0].
FORBIDDEN = frozenset({
    # shells and interpreters that run inline code
    "sh", "bash", "zsh", "dash", "ksh", "csh", "tcsh", "fish", "busybox", "env", "xargs", "eval",
    "exec", "perl", "ruby", "node", "deno", "bun", "php", "lua", "osascript", "pwsh", "powershell",
    "cmd", "cmd.exe",
    # destructive or privilege-changing file tools
    "rm", "rmdir", "unlink", "shred", "dd", "mv", "cp", "ln", "chmod", "chown", "chgrp", "truncate",
    "find", "sudo", "su", "doas", "mkfs", "mount", "umount", "kill", "pkill", "killall", "launchctl",
    "systemctl", "crontab", "nohup", "open",
    # network clients
    "curl", "wget", "nc", "ncat", "netcat", "socat", "ssh", "scp", "sftp", "rsync", "ftp", "tftp",
    "telnet", "git", "pip", "pip3", "npm", "npx", "uv", "gh",
})

# The only module a done-test may run with `{python} -m`.
ALLOWED_PYTHON_MODULES = frozenset({"rigmarket.checks"})


def declared_command_errors(commands: list[str]) -> list[str]:
    errs = []
    for cmd in commands:
        base = PurePosixPath(cmd).name
        if base in FORBIDDEN or cmd in FORBIDDEN:
            errs.append(f"permissions.commands: {cmd!r} is forbidden by the built-in policy")
        elif cmd not in BUILTIN_ALLOWED:
            errs.append(f"permissions.commands: {cmd!r} is not in the built-in allowlist "
                        f"({', '.join(sorted(BUILTIN_ALLOWED))})")
    return errs


def run_errors(run: list[str], declared: list[str]) -> list[str]:
    """Problems with one done-test argv (before placeholder substitution)."""
    if not run:
        return ["empty command"]
    if any(not isinstance(a, str) or "\0" in a for a in run):
        return ["arguments must be strings without NUL bytes"]
    cmd = run[0]
    base = PurePosixPath(cmd).name
    if base in FORBIDDEN or cmd in FORBIDDEN:
        return [f"command {cmd!r} is forbidden by the built-in policy"]
    if cmd not in BUILTIN_ALLOWED:
        return [f"command {cmd!r} is not in the built-in allowlist"]
    if cmd not in declared:
        return [f"command {cmd!r} not in permissions.commands"]
    if cmd == "{python}":
        return _python_errors(run[1:])
    return []


def _python_errors(args: list[str]) -> list[str]:
    if not args:
        return ["{python} needs a module or a pack script"]
    first = args[0]
    if first == "-m":
        if len(args) < 2 or args[1] not in ALLOWED_PYTHON_MODULES:
            mod = args[1] if len(args) > 1 else ""
            return [f"{{python}} -m {mod!r} is not allowed (allowed: {', '.join(sorted(ALLOWED_PYTHON_MODULES))})"]
        return []
    if first.startswith("-"):
        return [f"{{python}} option {first!r} is not allowed (no inline code; use -m or a pack script)"]
    if not first.startswith("{pack}/") or not first.endswith(".py"):
        return [f"{{python}} script {first!r} must be a .py file inside the pack ({{pack}}/...)"]
    if ".." in PurePosixPath(first[len("{pack}/"):]).parts:
        return [f"{{python}} script {first!r} escapes the pack"]
    return []
