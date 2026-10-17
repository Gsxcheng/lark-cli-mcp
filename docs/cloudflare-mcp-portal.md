# Behind Cloudflare Tunnel + Access + MCP Portal

This is how the author runs it: the container listens on loopback, `cloudflared` publishes it, Cloudflare Access only lets the MCP Portal through, and Claude / ChatGPT connect to the Portal.

Replace `<team>`, `<domain>` and the names with your own.

1. **Service token.** Zero Trust → Access → Service credentials → create `portal-lark-cli-mcp-origin`. Keep the Client ID and Secret.
2. **Access application for the origin.** Self-hosted, hostname `lark-cli-mcp-origin.<domain>`, one policy with action **Service Auth** that includes only that service token. Copy the application's AUD tag.
3. **Tunnel route.** In your tunnel, add a published application route `lark-cli-mcp-origin.<domain>` → `http://127.0.0.1:3310` (write the `http://`). Turn on "Protect with Access" with your team name `<team>` and the AUD tag. No Host header rewrite is needed.
4. **Check the gate.** Opening `https://lark-cli-mcp-origin.<domain>/mcp` in a browser should show a Cloudflare Access 403.
5. **MCP server.** AI → MCP portals → MCP servers → add. URL `https://lark-cli-mcp-origin.<domain>/mcp`, authentication "custom headers":
   - `Authorization: Bearer <MCP_BEARER_TOKEN>`
   - `CF-Access-Client-Id: <service token id>`
   - `CF-Access-Client-Secret: <service token secret>`

   Use an Allow policy for your own email (not the Service Auth policy). It should turn "Ready" with 1 tool.
6. **Attach it to your portal** and save the portal.
7. **Reconnect the client.** claude.ai caches the portal's server list at connect time: disconnect and reconnect the connector, then start a new conversation.

To cut it off: remove the server from the portal, or revoke the service token.
