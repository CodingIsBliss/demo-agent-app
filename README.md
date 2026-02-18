# AI Agent App – Azure App Service Deployment

A LangChain ReAct agent built with FastAPI, powered by Azure OpenAI GPT-4o, instrumented with OpenTelemetry GenAI semantic conventions, and connected to Application Insights.

## Project Structure

```
├── deploy.ps1            # One-step Azure deploy script (repo root)
├── src/
│   ├── Dockerfile        # Container image definition
│   ├── README.md
│   ├── requirements.txt
│   ├── startup.sh        # Azure App Service startup command
│   └── app/
│       ├── __init__.py
│       ├── main.py       # FastAPI routes (/, /chat, /health, /config)
│       ├── agent.py      # LangChain ReAct agent + OTel tracing
│       ├── telemetry.py  # OpenTelemetry + Azure Monitor setup
│       ├── tools.py      # Agent tools (calculator, weather, web search)
│       └── templates/
│           └── index.html  # Chat UI
```

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and authenticated (`az login`)
- PowerShell 7+ (pwsh)
- An Azure App Service (Linux, Python 3.12)
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
  --runtime "PYTHON|3.12"
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
    AZURE_OPENAI_API_VERSION="2024-10-21" \
    AGENT_RESOURCE_ID="/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Web/sites/<app-name>"
```

| Setting | Description |
|---------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Connection string from your Application Insights resource |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | API version (e.g. `2024-10-21`) |
| `AGENT_RESOURCE_ID` | ARM resource ID of the App Service (e.g. `/subscriptions/.../Microsoft.Web/sites/<app-name>`) |

> **Tip:** For production, use [Key Vault references](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references) instead of storing secrets directly in app settings.

### 3. Configure the App Service

```bash
# Set Python runtime and startup command
az webapp config set \
  --resource-group Demo \
  --name demo-agent-app-sbussa \
  --linux-fx-version "PYTHON|3.12" \
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

Use the included `deploy.ps1` script at the repo root:

```powershell
# First-time setup + deploy
.\deploy.ps1 -Setup

# Subsequent deploys
.\deploy.ps1
```

The script zips `src/` (using forward-slash paths for Linux compatibility), deploys via `az webapp deploy`, and polls the `/health` endpoint to verify.

Verify manually:

```bash
curl https://demo-agent-app-sbussa.azurewebsites.net/health
```

### 5. Docker (Alternative)

Build and run the container image locally or push to a registry:

```bash
cd src
docker build -t demo-agent-app .
docker run -p 8000:8000 --env-file .env demo-agent-app
```

## Run Locally

### 1. Create a virtual environment

```bash
cd src
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

Create a `.env` file inside `src/` (the app loads it via `python-dotenv`):

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21

# Optional – leave unset to disable telemetry locally
# APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
# OTEL_SERVICE_NAME=demo-agent-app
# AGENT_RESOURCE_ID=/subscriptions/.../Microsoft.Web/sites/<app-name>
```

> **Note:** The `.env` file is loaded automatically by `python-dotenv` and is silently skipped when absent (e.g., in production where env vars are set via App Settings).

### 4. Start the dev server

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser to use the chat UI.

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
| `AZURE_OPENAI_API_VERSION` | ❌ | *(e.g. 2024-10-21)* |
| `AGENT_RESOURCE_ID` | ❌ | *(ARM resource ID of the App Service)* |

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

The `gen_ai.agent.id` attribute is read from the `AGENT_RESOURCE_ID` environment variable (set in app settings above).

These spans power the **Application Insights → Agents (preview)** blade showing Agent Runs, Tool Calls, Models, and Token Consumption.
