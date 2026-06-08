#!/usr/bin/env python3

import argparse
import dataclasses
import sys
from os import execvp
from pathlib import Path
from sys import exit

import questionary

from . import config, history, menu, ssh, tmux
from .models import HostInfo

_PROMPT_USER = object()
_PROMPT_KEY = object()


def get_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Interactive SSH profile selector.",
        epilog="Use -- to pass extra flags directly to ssh/sftp/ssh-copy-id.",
    )
    p.add_argument("--config", "-c", type=Path, default=Path(ssh.DEFAULT_CONFIG_PATH))
    p.add_argument(
        "-l",
        nargs="?",
        const=_PROMPT_USER,
        default=None,
        metavar="USER",
        help="SSH login user; omit value to be prompted",
    )
    p.add_argument(
        "-i",
        nargs="?",
        const=_PROMPT_KEY,
        default=None,
        metavar="KEYFILE",
        help="identity file; omit value to choose from ~/.ssh/",
    )
    p.add_argument(
        "--tmux",
        "-t",
        action="store_true",
        default=False,
        help="attach to or create a remote tmux session named 'ssh' after connecting (ssh mode only)",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--sftp",
        action="store_true",
        default=False,
        help="open an SFTP session instead of SSH",
    )
    mode.add_argument(
        "--copy-id",
        action="store_true",
        default=False,
        dest="copy_id",
        help="run ssh-copy-id to install your public key on the remote host",
    )
    return p


def _discover_keys() -> list[Path]:
    ssh_dir = Path("~/.ssh").expanduser()
    if not ssh_dir.is_dir():
        return []
    return sorted(priv for pub in ssh_dir.glob("*.pub") if (priv := pub.with_suffix("")).is_file())


def _build_ssh_argv(
    host: HostInfo, user: str | None, key: str | None, extra: list[str], remote_tmux: bool
) -> list[str]:
    key_args = ["-i", key] if key else []
    if host.ssh_config_host:
        user_args = ["-l", user] if user else []
        tmux_cmd = ["tmux new-session -As ssh"] if remote_tmux else []
        return ["ssh", host.name, *user_args, *key_args, *extra, *tmux_cmd]
    target = f"{user}@{host.hostname or host.name}" if user else (host.hostname or host.name)
    port_args = ["-p", str(host.port)] if host.port else []
    tmux_cmd = ["tmux new-session -As ssh"] if remote_tmux else []
    return ["ssh", target, *port_args, *key_args, *extra, *tmux_cmd]


def _build_sftp_argv(
    host: HostInfo, user: str | None, key: str | None, extra: list[str]
) -> list[str]:
    key_args = ["-i", key] if key else []
    if host.ssh_config_host:
        target = f"{user}@{host.name}" if user else host.name
        return ["sftp", *key_args, *extra, target]
    target = f"{user}@{host.hostname or host.name}" if user else (host.hostname or host.name)
    port_args = ["-P", str(host.port)] if host.port else []
    return ["sftp", *port_args, *key_args, *extra, target]


def _build_copy_id_argv(
    host: HostInfo, user: str | None, key: str | None, extra: list[str]
) -> list[str]:
    key_args = ["-i", key] if key else []
    if host.ssh_config_host:
        target = f"{user}@{host.name}" if user else host.name
        return ["ssh-copy-id", *key_args, *extra, target]
    target = f"{user}@{host.hostname or host.name}" if user else (host.hostname or host.name)
    port_args = ["-p", str(host.port)] if host.port else []
    return ["ssh-copy-id", *port_args, *key_args, *extra, target]


def _execvp_safe(prog: str, args: list[str]) -> None:
    try:
        execvp(prog, args)
    except FileNotFoundError:
        print(
            f"sshme: error: {prog!r} not found — is it installed and on your PATH?", file=sys.stderr
        )
        exit(1)


def main() -> None:
    # Split sys.argv on "--" before argparse sees it.
    argv = sys.argv[1:]
    if "--" in argv:
        idx = argv.index("--")
        own_argv, extra_args = argv[:idx], argv[idx + 1 :]
    else:
        own_argv, extra_args = argv, []

    args = get_argparser().parse_args(own_argv)
    config_path = args.config

    try:
        ssh_infos = ssh.read_host_infos(config_path.as_posix())
        cfg = config.load()

        ssh_map = {h.name: h for h in (ssh_infos or [])}
        merged: list[HostInfo] = []
        seen: set[str] = set()

        for cfg_host in cfg.hosts:
            if cfg_host.name in ssh_map:
                base = ssh_map[cfg_host.name]
                merged.append(
                    dataclasses.replace(
                        base,
                        hostname=cfg_host.hostname or base.hostname,
                        port=cfg_host.port or base.port,
                        user=cfg_host.user or base.user,
                        description=cfg_host.description,
                    )
                )
            else:
                merged.append(cfg_host)
            seen.add(cfg_host.name)

        merged.extend(h for h in ssh_map.values() if h.name not in seen)

        if not merged:
            if ssh_infos is None:
                print(f"Configuration not found at {config_path}")
            else:
                print(f"No hosts configured in {config_path}")
            exit(1)

        recent = history.load()
        recent_set = set(recent)
        name_to_host = {h.name: h for h in merged}
        ordered = [name_to_host[n] for n in recent if n in name_to_host] + [
            h for h in merged if h.name not in recent_set
        ]

        profile = menu.input_profile(*ordered, show_none=True)
        if profile is None:
            exit(0)

        history.record(profile.name)
        host = menu.input_wildcard(profile)

        if args.l is _PROMPT_USER:
            user = questionary.text("Username:").ask()
        else:
            user = args.l  # str or None
        # For config-only hosts, fall back to the host's configured user.
        if user is None and not host.ssh_config_host:
            user = host.user

        if args.i is _PROMPT_KEY:
            keys = _discover_keys()
            if keys:
                key_path = menu.input_key(keys)
                key = str(key_path) if key_path else None
            else:
                print("sshme: no identity files found in ~/.ssh/", file=sys.stderr)
                key = None
        else:
            key = args.i  # str or None

        display = f"{user}@{host.name}" if user else host.name
        print(f"Connecting to {display}...")

        if args.copy_id:
            argv_out = _build_copy_id_argv(host, user, key, extra_args)
            _execvp_safe(argv_out[0], argv_out)
            return

        if args.sftp:
            argv_out = _build_sftp_argv(host, user, key, extra_args)
            _execvp_safe(argv_out[0], argv_out)
            return

        # SSH mode
        argv_out = _build_ssh_argv(host, user, key, extra_args, args.tmux)

        if tmux.is_active():
            win_name = f"SSH:{display}"
            try:
                win_id = tmux.find_window(win_name)
            except RuntimeError as exc:
                print(f"sshme: warning: {exc}", file=sys.stderr)
                _execvp_safe(argv_out[0], argv_out)
            else:
                if win_id:
                    tmux.select_window(win_id)
                else:
                    tmux.exec_new_window(win_name, *argv_out)
        else:
            _execvp_safe(argv_out[0], argv_out)

    except KeyboardInterrupt:
        print("Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
