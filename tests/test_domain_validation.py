#!/usr/bin/env python3
"""Exercise the exact installer functions and CLI parser without root/network."""
import pathlib
import subprocess

script = (pathlib.Path(__file__).resolve().parents[1] / "x-ui-latest.sh").read_text()
begin = script.index("valid_dns_hostname() {")
end = script.index("# INSTALL PACKAGES", begin)
validators = script[begin:end]
arg_begin = script.index("# ─── Argument parsing")
arg_end = script.index("# ─── Detect package manager", arg_begin)
cli = script[arg_begin:arg_end]

assert 'domain="${IP4}.cdn-one.org"' in script
assert 'reality_domain="${IP4//./-}.cdn-one.org"' in script
assert 'get_ssl_certs() {' in script
assert 'case "$AUTODOMAIN" in' in script
assert "    validate_domains\n" in script

def run(code, initial=""):
    bash = """
msg_err() { printf '%s\\n' "$*" >&2; }
msg_inf() { :; }
""" + validators + "\n" + initial + "\n" + code
    return subprocess.run(["bash", "-c", bash],
                          capture_output=True, text=True, timeout=5)

for hostname in ("panel.example.com", "host-1.example.co.uk", "a.b"):
    p = run(f'valid_dns_hostname "{hostname}"')
    assert p.returncode == 0, (hostname, p.stderr)

for hostname in ("", "example", "example.com.", ".example.com",
                 "a..b.com", "-bad.example.com", "bad-.example.com",
                 "bad_name.example.com", "a/../b.com",
                 "a" * 64 + ".example.com"):
    p = run(f'valid_dns_hostname "{hostname}"')
    assert p.returncode != 0, hostname

p = run('validate_domains; printf "%s|%s" "$domain" "$reality_domain"',
        'AUTODOMAIN=y; IP4=203.0.113.27; domain=""; reality_domain=""')
assert p.returncode == 0, p.stderr
assert p.stdout == "203.0.113.27.cdn-one.org|203-0-113-27.cdn-one.org", p.stdout

for bad in ("", "999.0.0.1", "1.2.3.999", "1.2.3", "1.2.3.9999"):
    p = run("validate_domains", f'AUTODOMAIN=y; IP4="{bad}"; domain=""; reality_domain=""')
    assert p.returncode != 0, (bad, p.stdout, p.stderr)

p = run("validate_domains",
        'AUTODOMAIN=n; domain="Panel.Example.Com"; reality_domain="Edge.Example.Com"')
assert p.returncode == 0, p.stderr

p = run("validate_domains",
        'AUTODOMAIN=n; domain="panel.example.com"; reality_domain="panel.example.com"')
assert p.returncode != 0

p = run("validate_domains",
        'AUTODOMAIN=n; domain="bad/name"; reality_domain="edge.example.com"')
assert p.returncode != 0

def parse(*args):
    text = """msg_err() { printf '%s\\n' "$*" >&2; }
INSTALL=y; AUTODOMAIN=n; domain=""; reality_domain=""
""" + cli + """\nprintf '%s|%s|%s|%s' "$AUTODOMAIN" "$domain" "$reality_domain" "$INSTALL"
"""
    return subprocess.run(["bash", "-c", text, "_", *args],
                          capture_output=True, text=True, timeout=5)

for flag in ("-auto_domain", "-auto_domains"):
    p = parse(flag, "y")
    assert p.returncode == 0, (flag, p.stderr)
    assert p.stdout == "y|||y", (flag, p.stdout)

p = parse("-auto_domains", "y", "-install", "n")
assert p.returncode == 0 and p.stdout == "y|||n", p.stderr
assert parse("-auto_domains").returncode != 0
assert parse("-unknown", "x").returncode != 0

print("PASS: historical automatic DNS, both CLI spellings, invalid IPs and names")
