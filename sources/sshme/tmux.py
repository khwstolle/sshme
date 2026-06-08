"""
Utility methods for interacting with TMux.
"""

from os import environ, execvp
from subprocess import run

__all__ = ["is_active", "list_windows", "find_window", "select_window", "exec_new_window"]

WINDOW_SEP = ","


def is_active() -> bool:
    return "TMUX" in environ


def list_windows() -> list[str]:
    result = run(
        ["tmux", "list-windows", "-F", "#{window_index},#{window_name}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux list-windows failed: {result.stderr.strip()}")
    return result.stdout.splitlines()


def find_window(name: str) -> str | None:
    for w in list_windows():
        win_id, win_name = w.split(WINDOW_SEP, maxsplit=1)
        if win_name == name:
            return win_id
    return None


def select_window(window_id: str) -> None:
    execvp("tmux", args=["tmux", "select-window", "-t", window_id])


def exec_new_window(name: str, *cmd: str) -> None:
    execvp("tmux", args=["tmux", "new-window", "-n", name, *cmd])
