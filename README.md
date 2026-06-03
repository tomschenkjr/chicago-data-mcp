# chicago-data-mcp

MCP server for the Chicago Open Data Portal (data.cityofchicago.org).

Deployed at `https://chicago-data-mcp.tomschenkjr.net/sse`.

## Tools

| Tool | Description |
|------|-------------|
| `search_chicago_datasets` | Search the data portal catalog by keyword |
| `get_dataset_columns` | Get column names and types for a dataset |
| `query_chicago_dataset` | Execute a SOQL query against any dataset |
| `geocode_chicago_location` | Convert a neighborhood/address to coordinates |

## Local development

```bash
pip install -r requirements.txt
python http_server.py        # HTTP/SSE on port 3000
# or
python server.py             # stdio for Claude Desktop
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SOCRATA_APP_TOKEN` | No | App token from data.cityofchicago.org for higher rate limits |
| `PORT` | No | HTTP port (default: 3000) |

## Deployment

Deploys automatically to ECS Fargate on push to `main` via GitHub Actions.
Infrastructure defined in `mcp-aws-infra/`. Hosted at `chicago-data-mcp.tomschenkjr.net`.
