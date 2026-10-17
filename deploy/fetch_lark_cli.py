"""Download the official lark-cli release, verify its SHA-256 and install it.

Checksums come from the checksums.txt published in @larksuite/cli. Bump
LARK_CLI_VERSION and the table together.
"""
import hashlib
import io
import os
import platform
import tarfile
import urllib.request

VERSION = os.environ.get("LARK_CLI_VERSION", "1.0.98")
SHA256 = {
    ("1.0.98", "amd64"): "4a12dcb7a0aab25986d8bcd046cb45b08278531a9aac3a12b53cf3d94738fe80",
    ("1.0.98", "arm64"): "f798b26ce4b369d70411945e7f66bbe4382c411bc47d81950a662de7b69b41ed",
}
ARCH = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[platform.machine().lower()]
DEST = os.environ.get("LARK_CLI_DEST", "/usr/local/bin/lark-cli")

name = f"lark-cli-{VERSION}-linux-{ARCH}.tar.gz"
want = os.environ.get("LARK_CLI_SHA256") or SHA256[(VERSION, ARCH)]
mirrors = [
    f"https://github.com/larksuite/cli/releases/download/v{VERSION}/{name}",
    # Same files, served by npmmirror (faster from mainland China).
    f"https://registry.npmmirror.com/-/binary/lark-cli/v{VERSION}/{name}",
]
if os.environ.get("LARK_CLI_PREFER_MIRROR"):
    mirrors.reverse()

data = None
for url in mirrors:
    try:
        data = urllib.request.urlopen(url, timeout=120).read()
        break
    except Exception as e:  # try the next source
        print(f"download failed: {url}: {e}")
if data is None:
    raise SystemExit("could not download lark-cli")
got = hashlib.sha256(data).hexdigest()
if got != want:
    raise SystemExit(f"lark-cli checksum mismatch: got {got}, want {want}")
with tarfile.open(fileobj=io.BytesIO(data)) as t:
    member = t.extractfile("lark-cli")
    with open(DEST, "wb") as f:
        f.write(member.read())
os.chmod(DEST, 0o755)
print(f"installed lark-cli {VERSION} ({ARCH}) to {DEST}")
