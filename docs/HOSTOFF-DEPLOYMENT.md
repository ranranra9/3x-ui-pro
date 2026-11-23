# HOSTOFF / Ubuntu 24.04 deployment checklist

> **Status: candidate hardening branch, not a validated production release.**
> Do not install until the GitHub Actions tests pass and a disposable VPS
> has completed the end-to-end transport checks below.

## Requirements

- A **clean** Ubuntu 24.04 VPS. The installer now refuses existing 3x-ui
  installations, websites and unrelated Nginx virtual hosts instead of
  deleting them. Use `x-ui-patch.sh` for an intentional update of an existing
  setup, after a snapshot.
- The upstream README previously advertised `-auto_domain y`, but the source
  did not implement domain discovery or DNS provisioning. This mode now fails
  early instead of silently prompting. It **cannot install domainlessly**.
- Two **different hostnames you control**, such as
  `panel.example.com` and `edge.example.com`. Both must resolve to the
  VPS IPv4 address. The current installer uses **two Let's Encrypt standalone
  HTTP-01 certificates**, and does not support a no-domain install.
- Inbound TCP/80 (certificate validation), TCP/443 and UDP/443 where needed;
  SSH must remain reachable on its existing port.
- Confirm the hoster's rules for REALITY/SNI and do not use third-party
  domains for camouflage without authorization.

## Before installing (do not skip)

1. Take a VPS snapshot using the hosting dashboard.
2. Verify addresses: `getent ahostsv4 panel.example.com` and
   `getent ahostsv4 edge.example.com`. Compare the A records to the VPS.
3. Record `sudo ss -lntup`, `sudo ufw status verbose`, and
   `sudo sshd -T | grep '^port '`. Keep a **second SSH session open** and
   test reconnection before enabling or changing UFW.
4. Review the exact commit. Do not blindly execute a moving branch as root.

## Before testing on a disposable server

From a trusted checkout of the reviewed branch, run:

```bash
bash -n x-ui-latest.sh x-ui-patch.sh assets/xray-forward-sync.sh
python3 tests/test_installer_invariants.py
python3 tests/test_forward_sync.py
python3 tests/test_forward_map_nginx.py  # requires nginx installed
```

After these pass, follow the installer prompts with your own two hostnames.
The scripts currently fetch support assets from the `security-hardening`
branch by default. For a **reproducible installation**, set `GITHUB_RAW`
to the reviewed immutable commit's raw-content URL before executing the
installer and fetch the installer from the same commit. Never use an
unreviewed remote shell pipeline.

## Post-install validation

```bash
sudo nginx -t
sudo systemctl --no-pager --full status nginx x-ui
sudo systemctl --no-pager --full status 3x-ui-pro-forward-sync.timer
sudo /usr/local/sbin/3x-ui-pro-sync-inbounds --sync
sudo cat /etc/nginx/snippets/xray-forward-ports.map
sudo ufw status verbose
sudo ss -lntup
```

The allowlist must contain only **enabled WS/gRPC Xray inbound ports**.
Check that the Xray REALITY, WS and gRPC TCP inbounds bind to
`127.0.0.1`, while public TLS traffic enters through Nginx on :443.
New/edited inbounds may take about a minute to appear in the map.

Test from an external client, not merely localhost:
- REALITY through Nginx stream on TCP/443;
- WebSocket and Trojan/gRPC via the real domain and generated path;
- XHTTP Unix-socket route if enabled;
- 3x-ui panel TLS, subscriptions and diagnostics;
- SSH reconnection before ending the active session;
- blocked requests to `https://panel.example.com/22/` and other
  disallowed numeric-port paths. Those must not reach a local service.

The test suite validates safeguards, not real-world proxy transport
performance or regional reachability. Verify with actual clients and
monitor `journalctl -u nginx -u x-ui` for failures.

## Backup / recovery

- Fresh installation: the installer saves the existing `/etc/nginx` to
  `/root/3x-ui-pro-nginx-backup-*/nginx.tar.gz` before reconfiguration.
- Patcher: it also saves a SQLite-consistent `x-ui.db` snapshot in
  `/root/3x-ui-pro-patch-backup-*/`.
- Restore files only after checking the paths and state; disable the timer,
  stop affected services, restore from the backup/snapshot, run `nginx -t`
  and then start the services. Do not assume an interrupted install is atomic.
