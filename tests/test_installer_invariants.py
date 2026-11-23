#!/usr/bin/env python3
"""Check that security invariants remain in both installer entry points."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
installer = (ROOT / "x-ui-latest.sh").read_text()
patcher = (ROOT / "x-ui-patch.sh").read_text()
helper = (ROOT / "assets/xray-forward-sync.sh").read_text()

for name, source in (("installer", installer), ("patcher", patcher)):
    assert "map \\$fwdport \\$xray_forward_allowed {" in source, f"{name}: missing port map"
    assert "if (\\$xray_forward_allowed = 0) { return 404; }" in source, (
        f"{name}: missing deny guard")
    assert "include /etc/nginx/snippets/xray-forward-ports.map;" in source
    assert "3x-ui-pro-sync-inbounds --prepare" in source
    assert "3x-ui-pro-forward-sync.timer" in source

assert "rm -rf /etc/nginx/" not in installer
assert "rm -rf /etc/x-ui" not in installer
assert 'msg_err "Unsafe legacy -uninstall is disabled in security-hardening."' in installer
assert '-auto_domain)      AUTODOMAIN="$2" ;;' in installer
assert 'Invalid hostname: use fully qualified ASCII DNS names' in installer
assert installer.index("    # Verify DNS before stopping Nginx") < installer.index("    systemctl stop nginx 2>/dev/null || true")
assert "clean_previous_install" not in installer
assert "verify_clean_install" in installer
assert "backup_nginx_before_changes" in installer
assert "ufw disable" not in installer
assert "fuser -k 80/tcp" not in installer
assert installer.index("    verify_clean_install\n") < installer.index("    install_packages\n")
assert installer.index("    backup_nginx_before_changes\n") < installer.index("    install_forward_sync\n")
assert installer.index("    install_forward_sync\n") < installer.index("    configure_nginx\n")
assert installer.index("    configure_xui_db\n") < installer.index(
    "    /usr/local/sbin/3x-ui-pro-sync-inbounds --sync")
for label, port in [
    ("reality", "8443"),
    ("ws", "${ws_port}"),
    ("trojan-grpc", "${trojan_port}"),
]:
    marker = f"${{emoji_flag}} {label}','1','0','127.0.0.1','{port}'"
    assert marker in installer, f"non-loopback Xray inbound: {label}"

assert "find /etc/nginx/sites-enabled -mindepth 1 -delete" not in patcher
assert "Conflicting enabled Nginx site" in patcher
assert 'sqlite3 "$XUIDB" ".backup ' in patcher
assert "json_valid(stream_settings)" in helper
assert "if ! nginx -t " in helper
assert "restore_map" in helper

print("PASS: installer order, loopback Xray inbounds, protected vhosts, deny-by-default")
