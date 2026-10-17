# lark-cli-mcp

[English](README.md)

把飞书官方的 [飞书 CLI](https://github.com/larksuite/cli)（`lark-cli`）包装成远程 MCP 服务，让 Claude、ChatGPT 或任何 MCP 客户端能创建和编辑飞书云文档、多维表格、知识库和云空间文件，同时**不给 AI 服务器 shell**。

飞书现在主推用 CLI 接 AI Agent，但 CLI 本身没有 MCP 模式。用通用的「执行命令」类 MCP 去包，要么等于给了 AI 一个 shell，要么一遇到 Markdown 就出错（表格里有 `|`，标题里有 `<`）。这个项目只做中间那一层：一个 MCP 工具、一个程序、一套拒绝规则、一个加固过的容器。

## 特点

- 只有一个工具 `lark_cli(args, stdin)`。`args` 是 `lark-cli` 后面的参数列表；`stdin` 给支持 `-` 的参数传内容，带表格、引用、`<标签>` 的 Markdown 原样传入。
- 全程不经过 shell。参数列表直接交给 `subprocess.run`，`&&`、`$(...)`、反引号都只是普通文字。
- 默认开启的拒绝规则：
  - 只放行列出的业务域（docs、drive、markdown、wiki、base、sheets、contact，以及 schema、skills、doctor、help、whoami；`LARK_CLI_ALLOWED_DOMAINS=*` 时放行除 config、profile、update 以外的所有域）；
  - 拒绝 `config`、`update`、`profile`、`auth login/logout`，AI 改不了用哪个应用、哪个账号；
  - 拒绝 `--yes`（飞书 CLI 对高危写操作的确认标记）；
  - 拒绝 `@文件` 参数，AI 没法把容器里的文件读进文档；
  - 原始 `api` 调用只许 GET。
- Streamable HTTP，必须带 Bearer 令牌（至少 32 位，常数时间比较）。
- 容器以非 root 用户运行，根文件系统只读，去掉全部 capabilities，开启 `no-new-privileges`。`lark-cli` 从官方发布下载，并按固定的 SHA-256 校验。

AI 能做什么，最终仍受你给飞书应用开的权限和登录账号的权限限制，按最小够用来开。也可以把 MCP 这层放开（`LARK_CLI_ALLOWED_DOMAINS=*` 等），全部交给飞书开放平台的权限来管；不管哪种，`config`/`profile`/`update`、`auth login/logout` 和 `@文件` 都始终拒绝。设计思路和四层权限见 [docs/architecture.zh-CN.md](docs/architecture.zh-CN.md)，威胁模型见 [SECURITY.md](SECURITY.md)。

## 快速开始

```bash
git clone https://github.com/Gsxcheng/lark-cli-mcp && cd lark-cli-mcp
cp .env.example .env && sed -i "s/^MCP_BEARER_TOKEN=.*/MCP_BEARER_TOKEN=$(openssl rand -hex 32)/" .env
docker compose -f deploy/docker-compose.yml up -d --build

# 一次性初始化，由你本人执行，不交给 AI：
docker exec -it lark-cli-mcp lark-cli config init --new          # 在浏览器里创建或绑定飞书应用
docker exec -it lark-cli-mcp lark-cli auth login --domain docs,drive,markdown,wiki,base,sheets,contact
docker exec lark-cli-mcp lark-cli auth status
```

想复用已有应用：`docker exec -it lark-cli-mcp lark-cli config init --app-id <App ID> --app-secret-stdin`。

服务监听 `127.0.0.1:3310`，路径 `/mcp`。对外暴露前请在前面加反向代理或隧道；Cloudflare Tunnel + Access + MCP Portal 的接法见 [docs/cloudflare-mcp-portal.md](docs/cloudflare-mcp-portal.md)。

国内服务器构建时用镜像：

```bash
docker compose -f deploy/docker-compose.yml build \
  --build-arg LARK_CLI_PREFER_MIRROR=1 \
  --build-arg PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple
```

## 调用示例

```json
{
  "args": ["docs", "+create", "--as", "user", "--doc-format", "markdown", "--title", "周报", "--content", "-"],
  "stdin": "# 本周\n\n| 事项 | 状态 |\n|---|---|\n| 上线 | 完成 |"
}
```

返回 `exit=<退出码>`，然后是 stdout 和 stderr。被拒绝的调用返回 `REFUSED: <原因>`，不会启动 `lark-cli`。

## 配置项

见英文 README 的 Configuration 表，变量相同。

## 开发

```bash
pip install -e '.[test]'
pytest
```

测试用的是假的 `lark-cli`，不需要飞书账号。

## 状态

早期版本（v0.1）。已用假 CLI 做单元测试，并在加固容器里跑通；第一次真实部署进行中。基于 `lark-cli` 1.0.98 和 MCP Python SDK 2.3.0。与飞书、Lark、字节跳动无隶属关系。

## 许可证

MIT
