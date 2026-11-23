#!/usr/bin/env bash
# Synchronize Nginx forwarding allowlist with enabled WS/gRPC Xray inbounds.
# --prepare: write map without reloading Nginx (during installation).
# --sync: validate and reload Nginx (for periodic systemd timer).
set -Eeuo pipefail

DB="${XRAY_FORWARD_DB:-/etc/x-ui/x-ui.db}"
MAP="${XRAY_FORWARD_MAP:-/etc/nginx/snippets/xray-forward-ports.map}"
MODE="${1:---sync}"

case "$MODE" in --prepare|--sync) ;; *) echo "Usage: $0 [--prepare|--sync]" >&2; exit 2;; esac
[[ -f "$DB" ]] || { echo "Missing X-UI database: $DB" >&2; exit 1; }
command -v sqlite3 >/dev/null || { echo 'sqlite3 is required' >&2; exit 1; }
command -v flock >/dev/null || { echo 'flock is required' >&2; exit 1; }

mkdir -p "$(dirname "$MAP")"
# Serialize timer invocations with installer and patcher.
LOCK="${XRAY_FORWARD_LOCK:-/run/lock/3x-ui-pro-forward-sync.lock}"
mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK"
flock -x 9

# JSON validation and explicit decimal-port checking ensure map data is safe.
# CASE prevents malformed JSON from ever reaching json_extract().
QUERY="SELECT DISTINCT CAST(port AS INTEGER)
  FROM inbounds
 WHERE enable = 1
   AND CAST(port AS INTEGER) BETWEEN 1 AND 65535
   AND TRIM(CAST(port AS TEXT)) = CAST(CAST(port AS INTEGER) AS TEXT)
   AND CASE WHEN json_valid(stream_settings)
            THEN json_extract(stream_settings, '$.network') IN ('ws', 'grpc')
            ELSE 0 END
 ORDER BY CAST(port AS INTEGER);"

ports="$(sqlite3 -readonly -batch -noheader "$DB" "$QUERY")" || {
    echo 'Cannot read Xray inbounds; leaving existing map unchanged' >&2
    exit 1
}

tmp="$(mktemp "$(dirname "$MAP")/.xray-forward-ports.XXXXXX")"
backup=""
cleanup() { rm -f "$tmp"; [[ -z "$backup" ]] || rm -f "$backup"; }
trap cleanup EXIT

{
    echo '# Managed by 3x-ui-pro-sync-inbounds; DO NOT EDIT.'
    while IFS= read -r port; do
        [[ -z "$port" ]] && continue
        [[ "$port" =~ ^[0-9]+$ ]] && (( port >= 1 && port <= 65535 )) || exit 1
        printf '%s 1;\n' "$port"
    done <<< "$ports"
} > "$tmp"
chmod 0644 "$tmp"

if [[ -f "$MAP" ]] && cmp -s "$tmp" "$MAP"; then
    exit 0
fi

if [[ -f "$MAP" ]]; then
    backup="$(mktemp "$(dirname "$MAP")/.xray-forward-backup.XXXXXX")"
    cp -p -- "$MAP" "$backup"
fi
mv -f -- "$tmp" "$MAP"

if [[ "$MODE" == --prepare ]]; then
    exit 0
fi

restore_map() {
    if [[ -n "$backup" ]]; then
        cp -p -- "$backup" "$MAP"
    else
        rm -f -- "$MAP"
    fi
}

if ! nginx -t >/dev/null 2>&1; then
    restore_map
    echo 'Nginx validation failed; restored previous allowlist' >&2
    exit 1
fi

# A running config is unchanged until reload. Do not start a stopped Nginx
# during certificate renewal or other planned maintenance.
if systemctl is-active --quiet nginx; then
    if ! systemctl reload nginx; then
        restore_map
        systemctl reload nginx >/dev/null 2>&1 || true
        echo 'Nginx reload failed; restored previous allowlist' >&2
        exit 1
    fi
fi
