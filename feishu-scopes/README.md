# Feishu scope templates / 飞书权限模板

Ready-made scope lists for the Feishu Open Platform's **批量导入/导出权限** (bulk import/export scopes), built from what `lark-cli` 1.0.98 asks for at `auth login`.

开放平台 → 你的应用 → 开发配置 → 权限管理 → 批量处理 → 批量导入/导出权限，把下面某个文件的内容粘进去，导入后到「版本管理与发布」发布新版本才生效。

| File / 文件 | Domains / 包含 | Delete scopes / 删除权限 | User scopes / 数量 |
| --- | --- | --- | --- |
| [docs-no-delete.json](docs-no-delete.json) | docs, drive, markdown, wiki, sheets, base, slides, contact | none / 不含 | 103 |
| [docs-full.json](docs-full.json) | same / 同上 | included / 含 | 114 |
| [all-no-delete.json](all-no-delete.json) | every lark-cli domain / 全部域 | none / 不含 | 207 |
| [all.json](all.json) | every lark-cli domain / 全部域 | included / 含 | 222 |

Recommended start: `docs-no-delete.json`. 推荐先用它：能建、改、分享文档和表格，不能删。

## Notes / 说明

- **User identity only by default.** Templates fill `user` scopes and leave `tenant` empty, because lark-cli-mcp is meant to run as the logged-in user. Add `--with-tenant` if you also use `--as bot`. 默认只开用户身份权限；要用应用身份（`--as bot`）时加 `--with-tenant` 重新生成。
- **"No delete" means scopes whose name contains `delete`** (e.g. `space:document:delete`, `base:record:delete`, `base:table:delete`, `docs:permission.member:delete`). Some write scopes can still remove things inside a resource, for example `base:view:write_only` ("新增、更新、删除视图") or `docx:document:write_only` (editing blocks). 「不含删除」指名字里带 `delete` 的权限；少数写权限本身也能删资源内部的东西，如视图、文档里的块。
- **Don't add broad scopes** such as `drive:drive`, `docs:doc`, `bitable:app`. Many APIs accept any one of several scopes, so a broad scope re-enables what you left out. 不要另外开「管理全部」类的大权限，否则会绕过上面的细分控制。
- `offline_access` is included because lark-cli adds it to every login to refresh the token. 含 `offline_access`，lark-cli 每次登录都会申请它，用于刷新令牌。
- At login you can still narrow further: `lark-cli auth login --domain docs,drive` or `--exclude <scope>`. Effective scopes = enabled on the app ∩ consented at login. 登录时还能再收窄；实际权限 = 应用开通的 ∩ 登录时同意的。
- **Import format is UNVERIFIED.** The files use `{"scopes": {"tenant": [...], "user": [...]}}`. If the console rejects it, export your current scopes once and compare. 导入格式尚未实测；如果导入报错，请先导出一次现有权限对照格式。

## Regenerate / 重新生成

```bash
python feishu-scopes/make_template.py --domains docs,drive,wiki --no-delete > my-scopes.json
python feishu-scopes/make_template.py --domains all --with-tenant > all-with-bot.json
```

`domain-scopes.lark-cli-1.0.98.json` maps each lark-cli domain to its user and tenant scopes. It was resolved offline from the larksuite/cli v1.0.98 source with the same code path `auth login --domain` uses. When lark-cli adds commands, regenerate it for the new version. 每个域对应的权限是从 lark-cli v1.0.98 源码离线算出的，和 `auth login --domain` 用的是同一套逻辑；lark-cli 升级后需要重新生成。
