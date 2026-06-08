"""
Interactive command-line menu for selecting a SSH profile to connect to.

See: https://github.com/kurt-stolle/sshme
"""

from . import config, history, menu, models, ssh, tmux

__all__ = ["config", "history", "menu", "models", "ssh", "tmux"]


def entry_point() -> None:
    from .__main__ import main

    main()
