import json
import os
import stat
import sys

import anyio
import pytest

from lark_cli_mcp.server import build_app, build_server

FAKE = """#!{python}
import json, sys
print(json.dumps({{"argv": sys.argv[1:], "stdin": sys.stdin.read()}}))
"""


@pytest.fixture()
def fake_cli(tmp_path):
    path = tmp_path / "lark-cli"
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def call(server, args, stdin=None):
    async def run():
        payload = {"args": args, **({"stdin": stdin} if stdin is not None else {})}
        result = await server.call_tool("lark_cli", payload)
        return result.content[0].text if hasattr(result, "content") else result[0][0].text
    return anyio.run(run)


def test_runs_with_argv_and_stdin(fake_cli, tmp_path):
    server = build_server({"LARK_CLI_BIN": fake_cli, "HOME": str(tmp_path)})
    md = "# Title\n| a | b |\n|---|---|\n> quote <tag> && $(id) ; `x`"
    out = call(server, ["docs", "+create", "--content", "-"], md)
    assert out.startswith("exit=0")
    body = json.loads(out.split("--- stdout ---\n", 1)[1].split("\n--- stderr ---", 1)[0])
    assert body == {"argv": ["docs", "+create", "--content", "-"], "stdin": md}


def test_refusal_does_not_run(fake_cli, tmp_path):
    server = build_server({"LARK_CLI_BIN": fake_cli, "HOME": str(tmp_path)})
    assert call(server, ["config", "show"]).startswith("REFUSED:")


def test_app_requires_long_token():
    with pytest.raises(SystemExit):
        build_app({"MCP_BEARER_TOKEN": "short"})


def test_bearer_guard_rejects_missing_token():
    app = build_app({"MCP_BEARER_TOKEN": "x" * 40})
    sent = []

    async def run():
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(msg):
            sent.append(msg)

        await app({"type": "http", "method": "POST", "path": "/mcp", "headers": []}, receive, send)

    anyio.run(run)
    assert sent[0]["status"] == 401
