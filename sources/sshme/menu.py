"""
Interactive console prompts using questionary.
"""

from pathlib import Path

import questionary
from questionary import Choice

from .models import HostInfo

__all__ = ["input_profile", "input_key", "input_wildcard"]

CHOICE_NONE = "(cancel)"
HOST_WILDCARD = "*"


def _subtitle(h: HostInfo) -> str | None:
    conn: list[str] = []
    if h.hostname:
        suffix = f":{h.port}" if h.port else ""
        conn.append(f"{h.hostname}{suffix}")
    elif h.port:
        conn.append(str(h.port))
    if h.user:
        conn.append(f"({h.user})")
    connection = " ".join(conn)
    if h.description:
        sep = " — " if connection else ""
        return f"{connection}{sep}{h.description}"
    return connection or None


def input_key(keys: list[Path]) -> Path | None:
    choices: list[Choice] = [Choice(title=k.name, value=k) for k in keys]
    choices.append(Choice(title=CHOICE_NONE, value=None))
    return questionary.select(
        "Select an identity file:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
    ).ask()


def input_profile(*hosts: HostInfo, show_none: bool = False) -> HostInfo | None:
    choices: list[Choice] = [Choice(title=h.name, value=h, description=_subtitle(h)) for h in hosts]
    if show_none:
        choices.append(Choice(title=CHOICE_NONE, value=None))

    result = questionary.select(
        "Select an SSH profile:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
    ).ask()

    return result  # None on cancel or (cancel) choice


def input_wildcard(host: HostInfo) -> HostInfo:
    if HOST_WILDCARD not in host.name:
        return host

    value = questionary.text("Enter wildcard substitution:").ask()
    if not value:
        return host
    return HostInfo(
        name=host.name.replace(HOST_WILDCARD, value, 1),
        hostname=host.hostname,
        port=host.port,
        user=host.user,
        description=host.description,
        ssh_config_host=host.ssh_config_host,
    )
