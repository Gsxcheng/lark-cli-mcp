# Security

## What this server protects against

lark-cli-mcp assumes the MCP client (an AI agent) may be confused or prompt-injected, and limits what it can make `lark-cli` do:

- No shell: argv goes straight to `subprocess.run`, so shell syntax in arguments or stdin is inert text.
- No account or app changes: `config`, `update`, `profile` and `auth login/logout` are refused.
- No high-risk writes by default: arguments carrying `--yes` are refused unless `LARK_CLI_ALLOW_YES` is on.
- No local file reads: `@file` arguments are refused, so container files (including lark-cli's own config) cannot be pulled into a document.
- Raw `api` calls are GET-only unless `LARK_CLI_ALLOW_API_WRITE` is on.

The last two, and the domain list, can be opened up so that Feishu scopes do all the limiting; see [docs/architecture.md](docs/architecture.md). The first four always hold.
- Every HTTP request needs the bearer token; the container runs as a non-root user with a read-only root filesystem and no capabilities.

## What it does not protect against

- Anything the logged-in Feishu user or app is allowed to do inside the permitted domains. The agent can still edit or share documents it can reach. Grant the Feishu app the fewest scopes you need, and prefer a dedicated account.
- A leaked bearer token. Keep the server on loopback behind an authenticating proxy (for example Cloudflare Access), and rotate the token if it leaks.
- Bugs in `lark-cli` itself.

## Reporting a vulnerability

Please open a private security advisory on this repository (Security → Report a vulnerability) instead of a public issue.
