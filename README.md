# sshme

Interactive SSH profile selector for the terminal. Pick a host from your `~/.ssh/config` with arrow keys or type to filter, then connect — or open an SFTP session, install your public key, or drop into a tmux window.

## Installation

```sh
uv tool install sshme
# or
pip install sshme
```

## Usage

```
sshme [options] [-- <ssh-flags>]
```

Run `sshme` with no arguments to open the selection menu. Navigate with arrow keys or type to filter. Recent connections appear at the top.

### Options

| Flag | Description |
|---|---|
| `-c`, `--config <path>` | SSH config file (default: `~/.ssh/config`) |
| `-l [USER]` | Login user — omit `USER` to be prompted |
| `-i [KEYFILE]` | Identity file — omit `KEYFILE` to choose from `~/.ssh/` |
| `-t`, `--tmux` | Attach to or create a remote tmux session named `ssh` after connecting |
| `--sftp` | Open an SFTP session instead of SSH |
| `--copy-id` | Run `ssh-copy-id` to install your public key |
| `--` | Pass remaining arguments directly to `ssh`, `sftp`, or `ssh-copy-id` |

### Examples

```sh
# Select a host and connect
sshme

# Connect as a specific user
sshme -l root

# Open SFTP with a specific identity file
sshme --sftp -i ~/.ssh/work_key

# Choose an identity file interactively
sshme -i

# Forward a local port
sshme -- -L 8080:localhost:8080

# Install your public key on a host
sshme --copy-id
```

## tmux Integration

When a tmux session is active, `sshme` opens the connection in a new window named `SSH:<host>`. If a window with that name already exists, `sshme` switches to it instead of opening a duplicate.

## Config Files

`sshme` reads hosts from `~/.ssh/config`, including any `Include` directives. Supplement or annotate those hosts with a TOML config file.

**Discovery order:**

1. `~/.config/sshme/config.toml` — user-wide defaults
2. `.sshme.toml` or `sshme.toml` — project-local, searched upward from the current directory

Project-local entries shadow user-wide entries when names conflict.

### Schema

```toml
# Add a host not in ~/.ssh/config
[[hosts]]
name = "devbox"
hostname = "192.168.1.42"
port = 2222
user = "dev"
description = "Local dev VM"

# Annotate an existing SSH config host with a description
[[hosts]]
name = "prod"
description = "Production cluster — handle with care"
```

All fields except `name` are optional. For hosts already in `~/.ssh/config`, `hostname`, `port`, and `user` appear as menu hints; OpenSSH resolves the connection from its config. For hosts defined only in TOML, those fields drive the connection.

## History

`sshme` records each selected profile in `~/.local/share/sshme/history.json` and sorts recent hosts to the top of the menu. Set `XDG_DATA_HOME` to store the file elsewhere.
