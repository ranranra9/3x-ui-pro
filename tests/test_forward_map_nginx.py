#!/usr/bin/env python3
"""Test the Nginx forwarding map and URI guard without root privileges."""
import pathlib
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

with tempfile.TemporaryDirectory(prefix="xray-nginx-test-") as tmp:
    root = pathlib.Path(tmp)
    (root / "logs").mkdir()
    allowed = root / "ports.map"
    allowed.write_text("15200 1;\n15201 1;\n")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    conf = root / "nginx.conf"
    conf.write_text(f"""pid {root}/nginx.pid;
error_log {root}/error.log notice;
events {{}}
http {{
    access_log off;
    map $fwdport $xray_forward_allowed {{
        default 0;
        include {allowed};
    }}
    server {{
        listen 127.0.0.1:{port};
        location ~ ^/(?<fwdport>\\d+)/(?<fwdpath>.*)$ {{
            if ($xray_forward_allowed = 0) {{ return 404; }}
            return 204;
        }}
        location / {{ return 404; }}
    }}
}}
""")
    cmd = ["nginx", "-p", str(root) + "/", "-c", str(conf)]
    verify = subprocess.run(cmd + ["-t"], capture_output=True, text=True)
    assert verify.returncode == 0, verify.stderr
    child = subprocess.Popen(cmd + ["-g", "daemon off;"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(30):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/15200/ok", timeout=1)
                break
            except Exception:
                assert child.poll() is None, "Nginx exited early"
                time.sleep(0.1)
        for path, expected in [("/15200/ws", 204), ("/15201/grpc", 204),
                               ("/22/admin", 404), ("/9000/sensitive", 404),
                               ("/text/test", 404)]:
            try:
                status = urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2).status
            except urllib.error.HTTPError as ex:
                status = ex.code
            assert status == expected, (path, status, expected)
    finally:
        child.terminate()
        try:
            child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
    print("PASS: Nginx allows approved routes and denies other local ports")
