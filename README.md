# daily-tips

Keep a plain-text list of tips and get one at random on your phone each day
via [ntfy](https://ntfy.sh). Secrets (topic, optional token/server) are
encrypted with [dotenvx](https://dotenvx.com); a systemd user timer runs it
daily.

## Setup

1. **Install** Python 3.9+, [dotenvx](https://dotenvx.com/docs/install)
   (`curl -sfS https://dotenvx.sh | sh`), and the ntfy app on your phone.
   Subscribe the app to a hard-to-guess topic name — on public ntfy.sh the
   topic name *is* the password.

2. **Set secrets** (from the repo root). Each `set` encrypts the value into
   `.env` and writes the private key to `.env.keys` (gitignored):

   ```sh
   dotenvx set NTFY_TOPIC my-secret-topic-name
   # optional, for a protected or self-hosted server:
   dotenvx set NTFY_TOKEN tk_xxxxxxxx
   dotenvx set NTFY_SERVER https://ntfy.example.com
   ```

   The encrypted `.env` is safe to commit. **Never commit `.env.keys`.**
   (dotenvx 2.x may store the key in your OS secret store instead of
   `.env.keys`; systemd can't read that, so export it with
   `dotenvx keypair DOTENV_PRIVATE_KEY` and use the `key.env` file below.)
   See `.env.example` for every supported variable.

3. **Edit `tips.txt`** — one tip per line. Blank lines and `#` comments are
   ignored.

4. **Test:**

   ```sh
   python3 daily_tip.py --dry-run              # prints a tip, no secrets needed
   dotenvx run -- python3 daily_tip.py         # actually publishes
   ```

## Daily schedule (systemd user timer)

```sh
# Keep the private key outside the repo (or leave .env.keys next to .env
# and remove the EnvironmentFile= line from the service).
mkdir -p ~/.config/daily-tip
echo "DOTENV_PRIVATE_KEY=$(dotenvx keypair DOTENV_PRIVATE_KEY)" > ~/.config/daily-tip/key.env
chmod 600 ~/.config/daily-tip/key.env

# Adjust WorkingDirectory= and the dotenvx/python3 paths in the service first.
mkdir -p ~/.config/systemd/user
cp systemd/daily-tip.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now daily-tip.timer

# Let the timer run while you're logged out:
loginctl enable-linger "$USER"
```

Check it:

```sh
systemctl --user start daily-tip.service     # run once now
journalctl --user -u daily-tip -n 20         # see what was sent
systemctl --user list-timers daily-tip.timer # next scheduled run
```

The timer fires at 09:00 (plus up to 15 min random delay) and catches up on
the next boot if the machine was off. Change `OnCalendar=` to adjust.

## Configuration

| Variable        | Required | Default          | Notes                                   |
|-----------------|----------|------------------|-----------------------------------------|
| `NTFY_TOPIC`    | yes      | —                | Not needed for `--dry-run`              |
| `NTFY_SERVER`   | no       | `https://ntfy.sh`|                                         |
| `NTFY_TOKEN`    | no       | —                | Sent as `Authorization: Bearer …`       |
| `NTFY_TITLE`    | no       | `Daily Tip`      |                                         |
| `NTFY_PRIORITY` | no       | server default   | `1`–`5` or `min`/`low`/`default`/`high`/`urgent` |
| `NTFY_TAGS`     | no       | —                | Comma-separated, e.g. `bulb,books`      |
| `TIPS_FILE`     | no       | `tips.txt` next to the script | `--tips-file` overrides    |
