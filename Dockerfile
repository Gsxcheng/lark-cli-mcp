FROM python:3.12-slim
ARG LARK_CLI_VERSION=1.0.98
# Set LARK_CLI_PREFER_MIRROR=1 to download from npmmirror first (mainland China).
ARG LARK_CLI_PREFER_MIRROR=
ARG PIP_INDEX_URL=https://pypi.org/simple
COPY deploy/fetch_lark_cli.py /tmp/fetch_lark_cli.py
RUN python3 /tmp/fetch_lark_cli.py && rm /tmp/fetch_lark_cli.py && lark-cli --version
COPY pyproject.toml README.md /src/
COPY src /src/src
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" /src && rm -rf /src
RUN useradd -u 10001 -m -d /data lark
USER lark
ENV HOME=/data PORT=3000
VOLUME /data
EXPOSE 3000
CMD ["lark-cli-mcp"]
