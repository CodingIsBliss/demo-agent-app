# AI Agent App – Azure App Service Deployment

A LangChain ReAct agent built with FastAPI, powered by Azure OpenAI GPT-4o, instrumented with OpenTelemetry GenAI semantic conventions, and connected to Application Insights.

## Project Structure

```
├── README.md
├── requirements.txt
├── startup.sh
└── app/
    ├── __init__.py
    ├── main.py          # FastAPI routes (/, /chat, /health, /config)
    ├── agent.py          # LangChain ReAct agent + OTel tracing
    ├── telemetry.py      # OpenTelemetry + Azure Monitor setup
    ├── tools.py          # Agent tools (calculator, weather, web search)
    └── templates/
        └── index.html    # Chat UI
```

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and authenticated (`az login`)
- PowerShell 7+ (pwsh)
- An Azure App Service (Linux, Python 3.14)
- An Azure OpenAI resource with a GPT-4o deployment
- An Application Insights resource

## Deploy to Azure App Service

### 1. Create the App Service (if needed)

```bash
az group create --name Demo --location eastus

az appservice plan create \
  --name demo-agent-plan \
  --resource-group Demo \
  --sku B1 \
  --is-linux

az webapp create \
  --name demo-agent-app-sbussa \
  --resource-group Demo \
  --plan demo-agent-plan \
  --runtime "PYTHON|3.14"
```

### 2. Set Required Secrets

These must be set as app settings on the Web App. Replace the placeholder values with your own:

```bash
az webapp config appsettings set \
  --resource-group Demo \
  --name demo-agent-app-sbussa \
  --settings \
    APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxxxx;IngestionEndpoint=https://eastus-x.in.applicationinsights.azure.com/" \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_API_KEY="your-api-key" \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o" \
    AZURE_OPENAI_API_VERSION="2024-08-06"
```

| Setting | Description |
|---------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Connection string from your Application Insights resource |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | API version (e.g. `2024-08-06`) |

> **Tip:** For production, use [Key Vault references](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references) instead of storing secrets directly in app settings.

### 3. Configure the App Service

```bash
# Set Python runtime and startup command
az webapp config set \
  --resource-group Demo \
  --name demo-agent-app-sbussa \
  --linux-fx-version "PYTHON|3.14" \
  --startup-file "startup.sh"

# Set non-secret app settings
az webapp config appsettings set \
  --resource-group Demo \
  --name demo-agent-app-sbussa \
  --settings \
    OTEL_SERVICE_NAME="demo-agent-app" \
    PORT="8000" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### 4. Deploy

Zip the repo contents and deploy:

```powershell
# From the repo root
Compress-Archive -Path app, requirements.txt, startup.sh -DestinationPath deploy.zip -Force

az webapp deploy `
  --resource-group Demo `
  --name demo-agent-app-sbussa `
  --src-path deploy.zip `
  --type zip
```

Verify:

```bash
curl https://demo-agent-app-sbussa.azurewebsites.net/health
```

## App Settings Reference

| Setting | Set by `-Setup` | Value |
|---------|:-:|-------|
| `OTEL_SERVICE_NAME` | ✅ | `demo-agent-app` |
| `PORT` | ✅ | `8000` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | ✅ | `true` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | ❌ | *(your connection string)* |
| `AZURE_OPENAI_ENDPOINT` | ❌ | *(your endpoint)* |
| `AZURE_OPENAI_API_KEY` | ❌ | *(your key)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | ❌ | *(your deployment, e.g. gpt-4o)* |
| `AZURE_OPENAI_API_VERSION` | ❌ | *(e.g. 2024-08-06)* |

## Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Chat web UI |
| `/chat` | POST | JSON chat endpoint (`{ "message": "..." }`) |
| `/health` | GET | Health check |
| `/config` | GET | Configuration status (non-sensitive) |

## OpenTelemetry Instrumentation

The app emits spans following the [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/):

| Span | Kind | Name Pattern | Key Attributes |
|------|------|-------------|----------------|
| LLM call | `CLIENT` | `chat gpt-4o` | `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.provider.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| Tool execution | `INTERNAL` | `execute_tool calculator` | `gen_ai.operation.name`, `gen_ai.tool.name`, `gen_ai.tool.type` |
| Agent run | `INTERNAL` | `invoke_agent react_agent` | `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.agent.id`, `gen_ai.request.model` |

> **Important:** In [app/agent.py](app/agent.py), replace the placeholder `gen_ai.agent.id` value with your App Service's ARM resource ID:
> ```
> /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Web/sites/<app-name>
> ```

These spans power the **Application Insights → Agents (preview)** blade showing Agent Runs, Tool Calls, Models, and Token Consumption.
