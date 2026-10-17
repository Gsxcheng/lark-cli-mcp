"""lark-cli-mcp: expose the official Feishu/Lark CLI (larksuite/cli) as one MCP tool."""
import hmac
import os
import subprocess

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .policy import Policy

INSTRUCTIONS = (
    "Runs the official Feishu/Lark CLI (lark-cli). Pass argv without the leading 'lark-cli', "
    "one list item per argument, e.g. ['docs', '+create', '--as', 'user', '--doc-format', "
    "'markdown', '--title', 'T', '--content', '-'] with the Markdown in stdin. "
    "Discover commands with ['<domain>', '--help'], ['schema', '<service.resource.method>'] "
    "and ['skills', 'read', 'lark-doc']. Prefer +shortcuts over raw api calls. "
    "Some commands are refused by the server policy; the refusal says why."
)


def build_server(env: dict[str, str] | None = None) -> MCPServer:
    env = dict(os.environ if env is None else env)
    policy = Policy.from_env(env)
    binary = env.get("LARK_CLI_BIN", "lark-cli")
    timeout = int(env.get("LARK_CLI_TIMEOUT", "120"))
    max_out = int(env.get("LARK_CLI_MAX_OUTPUT", "100000"))
    workdir = env.get("HOME") or os.getcwd()

    mcp = MCPServer(name="lark-cli", instructions=INSTRUCTIONS)

    @mcp.tool()
    def lark_cli(args: list[str], stdin: str | None = None) -> str:
        """Run `lark-cli <args...>` and return its exit code, stdout and stderr.

        args: argv after 'lark-cli', one list item per argument (no shell quoting).
        stdin: optional text fed to the process, for flags that accept '-'.
        """
        why = policy.refuse(args)
        if why:
            return f"REFUSED: {why}"
        try:
            p = subprocess.run(
                [binary, *args], input=stdin, capture_output=True, text=True,
                timeout=timeout, cwd=workdir,
            )
        except subprocess.TimeoutExpired:
            return f"TIMEOUT after {timeout}s"
        out = f"exit={p.returncode}\n--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}"
        if len(out) > max_out:
            out = out[:max_out] + f"\n[truncated {len(out) - max_out} chars]"
        return out

    return mcp


def bearer_guard(app, token: str):
    """Reject HTTP requests whose Authorization header is not `Bearer <token>`."""
    want = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            got = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(got, want):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await app(scope, receive, send)

    return guarded


def build_app(env: dict[str, str] | None = None):
    env = dict(os.environ if env is None else env)
    token = env.get("MCP_BEARER_TOKEN", "")
    if len(token) < 32:
        raise SystemExit("MCP_BEARER_TOKEN must be set to at least 32 characters")
    hosts = [h.strip() for h in env.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    security = TransportSecuritySettings(
        # Behind a reverse proxy the Host header is the public name; set MCP_ALLOWED_HOSTS to pin it.
        enable_dns_rebinding_protection=bool(hosts),
        allowed_hosts=hosts,
    )
    http_app = build_server(env).streamable_http_app(
        streamable_http_path=env.get("MCP_PATH", "/mcp"),
        stateless_http=True,
        json_response=True,
        transport_security=security,
        host="0.0.0.0",
    )
    return bearer_guard(http_app, token)


def main() -> None:
    import uvicorn

    uvicorn.run(build_app(), host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "3000")), log_level="info")


if __name__ == "__main__":
    main()
