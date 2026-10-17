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

AI 能做什么，最终仍受你给飞书应用开的权限和登录账号的权限限制，按最小够用来开。也可以把 MCP 这层放开（`LARK_CLI_ALLOWED_DOMAINS=*` 等），全部交给飞书开放平台的权限来管；不管哪种，`config`/`profile`/`update`、`auth login/logout` 和 `@文件` 都始终拒绝。飞书后台「批量导入权限」可直接用的模板在 [feishu-scopes/](feishu-scopes/)。设计思路和四层权限见 [docs/architecture.zh-CN.md](docs/architecture.zh-CN.md)，威胁模型见 [SECURITY.md](SECURITY.md)。

## 快速开始

### 方式一：交给 AI 助手部署

在服务器上打开一个能执行命令的 AI 助手（如 Claude Code、Codex CLI），把下面整段粘给它：

```text
请在这台服务器上部署 lark-cli-mcp（https://github.com/Gsxcheng/lark-cli-mcp），把飞书官方 CLI 作为 MCP 服务运行。要求：

1. 检查 docker、docker compose、git、openssl 是否可用，缺了先告诉我，不要自己装系统软件。
2. git clone 到 /opt/lark-cli-mcp（已存在就 git pull），复制 .env.example 为 .env，权限设为 600，用 `openssl rand -hex 32` 生成 MCP_BEARER_TOKEN 写进去。不要在输出里打印令牌的值。
3. 如果服务器在中国大陆，构建时加 --build-arg LARK_CLI_PREFER_MIRROR=1 --build-arg PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple。
4. 执行 `docker compose -f deploy/docker-compose.yml up -d --build`，然后用 `curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:3310/mcp` 确认返回 401（说明服务在跑且需要令牌）。
5. 飞书授权必须由我本人在浏览器里完成，你只负责把链接转给我：
   - 在后台运行 `docker exec lark-cli-mcp lark-cli config init --new`，把输出里的链接发给我，等我说「好了」再继续；
   - 运行 `docker exec lark-cli-mcp lark-cli auth login --no-wait --json`，把验证链接发给我；我确认后用返回的 device_code 执行 `docker exec lark-cli-mcp lark-cli auth login --device-code <device_code>` 完成登录。
6. 执行 `docker exec lark-cli-mcp lark-cli auth status`，把结果告诉我。
7. 最后告诉我：服务地址 http://127.0.0.1:3310/mcp，令牌在 /opt/lark-cli-mcp/.env 的 MCP_BEARER_TOKEN（只告诉位置，不打印值），以及下一步需要给它加反向代理或隧道才能从外网访问。

不要修改 .env 里除 MCP_BEARER_TOKEN 以外的项，不要把 3310 端口开放到公网，除上面列出的以外不要执行任何 lark-cli config / auth 命令。
```

部署好后，想只在飞书开放平台管权限，可以在 `.env` 里加 `LARK_CLI_ALLOWED_DOMAINS=*` 等开关（见[配置项](#配置项)和[设计说明](docs/architecture.zh-CN.md)），飞书后台可直接导入 [feishu-scopes/](feishu-scopes/) 里的权限模板。

### 方式二：手动部署

```bash
git clone https://github.com/Gsxcheng/lark-cli-mcp && cd lark-cli-mcp
cp .env.example .env && sed -i "s/^MCP_BEARER_TOKEN=.*/MCP_BEARER_TOKEN=$(openssl rand -hex 32)/" .env
docker compose -f deploy/docker-compose.yml up -d --build

# 一次性初始化，需要你本人在浏览器里同意：
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

### 让 AI 用好这个工具

连上 MCP 之后，可以把下面这段加进 AI 客户端的项目说明或系统提示词里：

```text
你可以用 lark_cli 工具操作飞书，args 是 lark-cli 后面的参数列表，stdin 是传给 `-` 参数的内容。
- 先看帮助再调用：`["<域>", "--help"]` 看有哪些命令，`["schema", "<服务.资源.方法>"]` 看参数和所需权限。优先用带 + 的快捷命令。
- 默认用我的身份：加 `--as user`。
- 写文档时正文放 stdin，参数写 `--content -`，Markdown 的表格、引用都能原样传。
- 不确定会写入什么时先加 `--dry-run` 预览。
- 删除、移除协作者、转移所有者、需要 `--yes` 的操作，先跟我确认再执行。
- 返回 REFUSED 说明被服务端规则拦截（比如 config、auth login、@文件），不要换方式绕过，直接告诉我。
- 报权限不足时，把缺的权限名告诉我，由我去飞书开放平台开通。
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
