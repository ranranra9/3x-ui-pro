#!/usr/bin/env python3
"""No-root regression tests for the Xray forwarding allowlist synchronizer."""
import os
import pathlib
import sqlite3
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNC = ROOT / "assets" / "xray-forward-sync.sh"

with tempfile.TemporaryDirectory() as work:
    root = pathlib.Path(work)
    mock = root / "bin"
    mock.mkdir()
    (mock / "sqlite3").write_text("""#!/usr/bin/env python3
import sys, sqlite3
args = [a for a in sys.argv[1:] if a not in ('-readonly', '-batch', '-noheader')]
con = sqlite3.connect(args[0])
print('\\n'.join(str(row[0]) for row in con.execute(args[1])))
con.close()
""")
    (mock / "nginx").write_text("#!/bin/sh\n[ \"$MOCK_NGINX_FAIL\" != 1 ]\n")
    (mock / "systemctl").write_text("#!/bin/sh\necho \"$*\" >> \"$CALLS\"\nexit 0\n")
    for path in mock.iterdir():
        path.chmod(0o755)

    db = root / "x-ui.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE inbounds (enable INT, port INT, stream_settings TEXT)")
        con.executemany("INSERT INTO inbounds VALUES (?,?,?)", [
            (1, 15200, '{"network":"ws"}'),
            (1, 15201, '{"network":"grpc"}'),
            (0, 15202, '{"network":"ws"}'),
            (1, 22, '{"network":"tcp"}'),
            (1, 16700, "invalid JSON"),
            (1, 0, '{"network":"ws"}'),
            (1, 15200, '{"network":"ws"}'),
        ])
    allowed = root / "xray-forward-ports.map"
    calls = root / "calls"
    calls.write_text("")
    env = {
        **os.environ,
        "PATH": str(mock) + ":" + os.environ["PATH"],
        "XRAY_FORWARD_DB": str(db),
        "XRAY_FORWARD_MAP": str(allowed),
        "XRAY_FORWARD_LOCK": str(root / "lock"),
        "CALLS": str(calls),
        "MOCK_NGINX_FAIL": "0",
    }

    def run(mode, **changes):
        return subprocess.run(["bash", str(SYNC), mode],
                              env={**env, **changes}, capture_output=True, text=True)

    response = run("--prepare")
    assert response.returncode == 0, response.stderr
    lines = allowed.read_text().splitlines()
    assert "15200 1;" in lines and "15201 1;" in lines
    assert all(f"{port} 1;" not in lines for port in (22, 15202, 16700, 0))
    assert not calls.read_text()

    response = run("--sync")
    assert response.returncode == 0 and not calls.read_text(), response.stderr

    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO inbounds VALUES (1,15555,'{\"network\":\"ws\"}')")
    response = run("--sync")
    assert response.returncode == 0, response.stderr
    assert "15555 1;" in allowed.read_text().splitlines()
    assert "reload nginx" in calls.read_text()

    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO inbounds VALUES (1,15556,'{\"network\":\"grpc\"}')")
    old_map = allowed.read_text()
    response = run("--sync", MOCK_NGINX_FAIL="1")
    assert response.returncode != 0
    assert allowed.read_text() == old_map, "Bad Nginx config must roll back map"

    db.rename(db.with_suffix(".gone"))
    response = run("--sync")
    assert response.returncode != 0
    assert allowed.read_text() == old_map, "Missing DB must not damage current map"
    print("PASS: safe ports, no-op, reload, rollback, missing database")
