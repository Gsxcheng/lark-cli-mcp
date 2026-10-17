# lark-cli-mcp

[中文](README.zh-CN.md)

Run the official [Feishu/Lark CLI](https://github.com/larksuite/cli) (`lark-cli`) as a remote MCP server, so Claude, ChatGPT or any MCP client can create and edit Feishu docs, Base tables, Wiki pages and Drive files without getting a shell on your server.

`lark-cli` is what Feishu now recommends for AI agents, but it has no MCP mode. Wrapping it in a generic "run a command" MCP server either gives the agent a shell or breaks on Markdown (tables contain `|`, titles contain `<`). This project sits in between: one MCP tool, one binary, a small refusal policy, and a hardened container.

## What you get

- One tool, `lark_cli(args, stdin)`. `args` is the argv after `lark-cli`; `stdin` feeds flags that accept `-`, so Markdown with tables, quotes and `<tags>` goes through untouched.
- No shell anywhere. The argv list goes straight to `subprocess.run`; `&&`, `$(...)` and backticks are just text.
- A refusal policy, on by default:
  - only the listed domains run (docs, drive, markdown, wiki, base, sheets, contact, plus schema, skills, doctor, help, whoami);
  - `config`, `update`, `profile` and `auth login/logout` are refused, so the agent cannot change which app or account it acts as;
  - `--yes` (lark-cli's marker for high-risk writes) is refused;
  - `@file` arguments are refused, so the agent cannot read files from the container into a document;
  - raw `api` calls are GET-only.
- Streamable HTTP with a required bearer token (32+ characters, compared in constant time).
- A container that runs as a non-root user with a read-only root filesystem, no capabilities and `no-new-privileges`. `lark-cli` is downloaded from the official release and checked against a pinned SHA-256.

What the agent can do is still bounded by the scopes you grant the Feishu app and the user who logs in. Grant the least you need. You can also open the MCP layer up (`LARK_CLI_ALLOWED_DOMAINS=*`) and control everything with Feishu scopes; `config`/`profile`/`update`, `auth login/logout` and `@file` stay refused either way. Ready-made scope lists for the Feishu console's bulk import are in [feishu-scopes/](feishu-scopes/). See [docs/architecture.md](docs/architecture.md) for the design and the four permission layers, and [SECURITY.md](SECURITY.md) for the threat model.

## Quick start

### Option 1: let an AI agent deploy it

Open an agent that can run commands on the server (Claude Code, Codex CLI, …) and paste this:

```text
Deploy lark-cli-mcp (https://github.com/Gsxcheng/lark-cli-mcp) on this server so the official Feishu/Lark CLI runs as an MCP server. Requirements:

1. Check that docker, docker compose, git and openssl are available. If something is missing, tell me; don't install system packages yourself.
2. git clone into /opt/lark-cli-mcp (git pull if it exists). Copy .env.example to .env, chmod 600, and write a MCP_BEARER_TOKEN generated with `openssl rand -hex 32`. Never print the token's value.
3. If the server is in mainland China, build with --build-arg LARK_CLI_PREFER_MIRROR=1 --build-arg PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple.
4. Run `docker compose -f deploy/docker-compose.yml up -d --build`, then check that `curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:3310/mcp` returns 401 (running, token required).
5. Feishu authorization must be done by me in a browser; you only pass me the links:
   - run `docker exec lark-cli-mcp lark-cli config init --new` in the background, send me the link from its output, and wait until I say it's done;
   - run `docker exec lark-cli-mcp lark-cli auth login --no-wait --json`, send me the verification link; after I confirm, finish with `docker exec lark-cli-mcp lark-cli auth login --device-code <device_code>`.
6. Run `docker exec lark-cli-mcp lark-cli auth status` and show me the result.
7. Finally tell me: the endpoint http://127.0.0.1:3310/mcp, that the token is MCP_BEARER_TOKEN in /opt/lark-cli-mcp/.env (location only, not the value), and that it needs a reverse proxy or tunnel before it is reachable from outside.

Don't change anything in .env besides MCP_BEARER_TOKEN, don't expose port 3310 to the internet, and don't run any lark-cli config or auth command other than the ones listed above.
```

To let Feishu scopes do all the limiting afterwards, add `LARK_CLI_ALLOWED_DOMAINS=*` and the other switches to `.env` (see [Configuration](#configuration) and [the design notes](docs/architecture.md)); ready-made scope lists for the Feishu console are in [feishu-scopes/](feishu-scopes/).

### Option 2: by hand

```bash
git clone https://github.com/Gsxcheng/lark-cli-mcp && cd lark-cli-mcp
cp .env.example .env && sed -i "s/^MCP_BEARER_TOKEN=.*/MCP_BEARER_TOKEN=$(openssl rand -hex 32)/" .env
docker compose -f deploy/docker-compose.yml up -d --build

# One-time setup; you consent in a browser:
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

### Teach your AI to use it

Once connected, add this to your AI client's project instructions or system prompt:

```text
You can operate Feishu/Lark with the lark_cli tool. args is the argv after lark-cli; stdin feeds flags given as `-`.
- Look before you call: `["<domain>", "--help"]` lists commands, `["schema", "<service.resource.method>"]` shows parameters and required scopes. Prefer +shortcut commands.
- Act as me by default: add `--as user`.
- Put document bodies in stdin with `--content -`; Markdown tables and quotes pass through unchanged.
- Add `--dry-run` to preview when you're unsure what a write will do.
- Ask me before deleting, removing collaborators, transferring ownership, or anything that needs `--yes`.
- REFUSED means a server-side rule blocked the call (config, auth login, @file, …). Don't work around it; tell me.
- On a missing-scope error, tell me the scope name; I'll enable it in the Feishu Open Platform.
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
| `LARK_CLI_ALLOWED_DOMAINS` | see above | Comma-separated first arguments that may run. `*` allows every domain except `config`, `profile` and `update`, which stay with the operator, so the Feishu app's scopes become the limit. |
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
