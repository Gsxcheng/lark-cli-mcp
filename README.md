# lark-cli-mcp

[中文](README.zh-CN.md)

Run the official [Feishu/Lark CLI](https://github.com/larksuite/cli) (`lark-cli`) as a remote MCP server, so Claude, ChatGPT or any MCP client can create and edit Feishu docs, Base tables, Wiki pages and Drive files without getting a shell on your server.

`lark-cli` is what Feishu now recommends for AI agents, but it has no MCP mode. Wrapping it in a generic "run a command" MCP server either gives the agent a shell or breaks on Markdown (tables contain `|`, titles contain `<`). This project sits in between: one MCP tool, one binary, a small refusal policy, and a hardened container.

## What you get

- One tool, `lark_cli(args, stdin)`. `args` is the argv after `lark-cli`; `stdin` feeds flags that accept `-`, so Markdown with tables, quotes and `<tags>` goes through untouched.
- No shell anywhere. The argv list goes straight to `subprocess.run`; `&&`, `$(...)` and backticks are just text.
- A refusal policy, on by default:
  - only the listed domains run (docs, drive, markdown, wiki, base, sheets, contact, plus schema, skills, doctor, help);
  - `config`, `update`, `profile` and `auth login/logout` are refused, so the agent cannot change which app or account it acts as;
  - `--yes` (lark-cli's marker for high-risk writes) is refused;
  - `@file` arguments are refused, so the agent cannot read files from the container into a document;
  - raw `api` calls are GET-only.
- Streamable HTTP with a required bearer token (32+ characters, compared in constant time).
- A container that runs as a non-root user with a read-only root filesystem, no capabilities and `no-new-privileges`. `lark-cli` is downloaded from the official release and checked against a pinned SHA-256.

What the agent can do is still bounded by the scopes you grant the Feishu app and the user who logs in. Grant the least you need. See [SECURITY.md](SECURITY.md) for the threat model.

## Quick start

```bash
git clone https://github.com/Gsxcheng/lark-cli-mcp && cd lark-cli-mcp
cp .env.example .env && sed -i "s/^MCP_BEARER_TOKEN=.*/MCP_BEARER_TOKEN=$(openssl rand -hex 32)/" .env
docker compose -f deploy/docker-compose.yml up -d --build

# One-time setup, done by you, not by the agent:
docker exec -it lark-cli-mcp lark-cli config init --new          # create or bind a Feishu app in the browser
docker exec -it lark-cli-mcp lark-cli auth login --domain docs,drive,markdown,wiki,base,sheets,contact
docker exec lark-cli-mcp lark-cli auth status
```

To reuse an existing app instead of `--new`: `docker exec -it lark-cli-mcp lark-cli config init --app-id <app id> --app-secret-stdin`.

The server listens on `127.0.0.1:3310` at `/mcp`. Put a reverse proxy or tunnel in front of it before exposing it; see [docs/cloudflare-mcp-portal.md](docs/cloudflare-mcp-portal.md) for Cloudflare Tunnel + Access + MCP Portal.

From mainland China, build with mirrors:

```bash
docker compose -f deploy/docker-compose.yml build \
  --build-arg LARK_CLI_PREFER_MIRROR=1 \
  --build-arg PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple
```

## Example call

```json
{
  "args": ["docs", "+create", "--as", "user", "--doc-format", "markdown", "--title", "Weekly notes", "--content", "-"],
  "stdin": "# This week\n\n| Item | Status |\n|---|---|\n| Launch | done |"
}
```

The tool returns `exit=<code>`, then stdout and stderr. Refused calls return `REFUSED: <reason>` and never start `lark-cli`.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `MCP_BEARER_TOKEN` | required | Clients send `Authorization: Bearer <token>`. At least 32 characters. |
| `MCP_ALLOWED_HOSTS` | empty | Comma-separated Host values to accept. Empty turns DNS-rebinding protection off, which is what you want behind a proxy that rewrites nothing. |
| `MCP_PATH` | `/mcp` | HTTP path of the MCP endpoint. |
| `LARK_CLI_ALLOWED_DOMAINS` | see above | Comma-separated first arguments that may run. |
| `LARK_CLI_ALLOW_YES` | off | Allow `--yes` high-risk writes. |
| `LARK_CLI_ALLOW_FILE_ARGS` | off | Allow `@file` arguments. |
| `LARK_CLI_ALLOW_API_WRITE` | off | Allow non-GET raw `api` calls. |
| `LARK_CLI_TIMEOUT` | `120` | Seconds before a call is killed. |
| `LARK_CLI_MAX_OUTPUT` | `100000` | Characters of output returned to the client. |

## Development

```bash
pip install -e '.[test]'
pytest
```

The tests use a fake `lark-cli`, so they need no Feishu account.

## Status

Early (v0.1). Covered by unit tests with a fake `lark-cli` and checked in the hardened container; first real deployment in progress. Built against `lark-cli` 1.0.98 and the MCP Python SDK 2.3.0. Not affiliated with Feishu, Lark or ByteDance.

## License

MIT
