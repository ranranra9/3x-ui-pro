# 3x-ui-pro

🇷🇺 [Русская версия](README.md)

Automated installer for the [3x-ui](https://github.com/MHSanaei/3x-ui) panel with nginx, SSL, Clash subscription and network diagnostics.

- Debian 12 / Ubuntu 24
- Two hostnames for panel and REALITY. **No domain purchase is required** with `-auto_domains y`: derive automatic IP-based names via `cdn-one.org` (restored legacy mode).
- Automatic SSL certificate renewal
- VLESS+REALITY, VLESS+WebSocket, VLESS+XHTTP, Trojan+gRPC — all through port 443

---

## What gets installed

| Component | Description |
|-----------|-------------|
| 3x-ui | VPN panel with web UI |
| nginx | Reverse proxy, SNI routing |
| certbot | Let's Encrypt SSL |
| Clash subscription | Serves `clash.yaml` based on User-Agent |
| Diagnostics | MTR tracer + in-browser speed test |
| Fake site | Random HTML cover site |
| Backup | Backup / restore script |
| AdGuard Home | Optional: ad-blocking DNS (DoH) — separate script |

---

## Installation

**Step 1 — download the script**

```bash
wget -qO x-ui-latest.sh https://raw.githubusercontent.com/mozaroc/3x-ui-pro/main/x-ui-latest.sh
```

**Step 2 — run it**

```bash
bash x-ui-latest.sh -install y
```

---
## Patch

Apply current fixes to an existing installation (no DB changes):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mozaroc/3x-ui-pro/main/x-ui-patch.sh)
```

---

## AdGuard Home (optional)

Installs [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) on the panel domain — no separate domain or open ports, everything goes through the existing 443:

- **DNS-over-HTTPS** for clients: `https://<panel-domain>/dns-query`
- **Admin UI** — at a random `/adg-<random>/` path (login and password are printed by the script)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mozaroc/3x-ui-pro/main/x-ui-adguard.sh)
```

Re-running is safe (settings and password are kept). After the installer or the patch, run this script again — they rewrite the nginx config.

Uninstall:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mozaroc/3x-ui-pro/main/x-ui-adguard.sh) -uninstall y
```

---

## Uninstall

**In `security-hardening`, the upstream `-uninstall y` mode is intentionally disabled.** It used to remove all of `/etc/nginx` and shared packages. Back up the VPS first and use a separately reviewed removal procedure scoped to X-UI resources.

---

 
Example without purchasing a domain:
```bash
bash x-ui-latest.sh -auto_domains y
```

**Automatic mode:** `-auto_domains y` (and the legacy alias `-auto_domain y`) derives `<IP>.cdn-one.org` and `<IP-with-hyphens>.cdn-one.org`. No domain purchase or manual DNS change is needed, but the external DNS service must resolve both names to the VPS before Certbot is run. This uses a third-party domain; confirm hosting and SNI policy compliance. It is not literal domain-free TLS.

## Command-line options

| Option | Description |
|--------|-------------|
| `-install y` | Install |
| `-subdomain <domain>` | Panel and subscription domain |
| `-reality_domain <domain>` | REALITY destination domain |
| `-auto_domains y` | Derive both hostnames from the IP using `cdn-one.org` without purchasing a domain; `-auto_domain y` remains an alias |
| `-version <version>` | Install specific 3x-ui version (e.g. `3.4.2`), default — latest |
| `-uninstall y` | **Disabled in security-hardening:** upstream uninstaller deleted all Nginx configuration and shared packages |

---

## Clash subscription

Works via User-Agent detection — one URL, different behavior:

- **Clash / Mihomo / Stash** → get a ready-to-use `clash.yaml` config
- **Regular browser / other clients** → get the standard 3x-ui subscription page

The import link is printed by the script after installation.

---

## Backup and restore

**Install the backup script**

```bash
wget -qO /usr/local/bin/x-ui-backup https://raw.githubusercontent.com/mozaroc/3x-ui-pro/main/assets/backup/x-ui-backup.sh
chmod +x /usr/local/bin/x-ui-backup
```

**Create a backup**

```bash
x-ui-backup backup
```

**List backups**

```bash
x-ui-backup list
```

**Restore from a backup** (on a clean server; packages are installed automatically)

```bash
x-ui-backup restore /var/backups/x-ui/x-ui-backup-20260101-120000.tar.gz
```

The backup includes: nginx configs, panel DB, 3x-ui binary, SSL certificates, web content, systemd units, cron, UFW rules.

---

## Network diagnostics

Available after installation at the link printed by the script. Includes:

- MTR trace to your IP
- Download and upload speed test (512 MB test files)
