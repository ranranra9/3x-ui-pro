#!/usr/bin/env python3
"""Exercise exact domain-validator functions from the installer without root."""
import pathlib
import subprocess

script = (pathlib.Path(__file__).resolve().parents[1] / "x-ui-latest.sh").read_text()
begin = script.index("valid_dns_hostname() {")
end = script.index("# INSTALL PACKAGES", begin)
snippet = script[begin:end]

# Only function definitions and comments are extracted, not root checks or
# installation calls. An earlier regression silently ignored -auto_domain y.
assert '-auto_domain)      AUTODOMAIN="$2" ;;' in script
assert 'main() {' in script
assert script.index("    validate_domains\n", script.index("main() {")) < script.index(
    "    verify_clean_install\n", script.index("main() {"))

def run(code, initial):
    return subprocess.run(
        ["bash", "-c", 'msg_err() { printf "%s\\n" "$*" >&2; }\n'
         + snippet + '\n' + initial + "\n" + code],
        capture_output=True, text=True, timeout=5,
    )

for hostname in ("panel.example.com", "host-1.example.co.uk", "a.b"):
    result = run(f'valid_dns_hostname "{hostname}"', "")
    assert result.returncode == 0, (hostname, result.stderr)

for hostname in ("", "example", "example.com.", ".example.com",
                 "a..b.com", "-bad.example.com", "bad-.example.com",
                 "bad_name.example.com", "a/../b.com",
                 "a" * 64 + ".example.com"):
    result = run(f'valid_dns_hostname "{hostname}"', "")
    assert result.returncode != 0, hostname

result = run("validate_domains", 'AUTODOMAIN=y; domain=""; reality_domain=""')
assert result.returncode != 0
assert "not implemented" in result.stderr.lower(), result.stderr

result = run("validate_domains", 'AUTODOMAIN=n; domain="Panel.Example.Com"; reality_domain="Edge.Example.Com"')
assert result.returncode == 0, result.stderr

result = run("validate_domains", 'AUTODOMAIN=n; domain="panel.example.com"; reality_domain="panel.example.com"')
assert result.returncode != 0

result = run("validate_domains", 'AUTODOMAIN=n; domain="bad/name"; reality_domain="edge.example.com"')
assert result.returncode != 0

print("PASS: domain validation, no silent auto-domain, no noninteractive blocking")
