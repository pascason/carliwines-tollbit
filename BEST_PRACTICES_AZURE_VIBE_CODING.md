# Best Practices: Vibe-Coding with GitHub Copilot on Azure

## Purpose
Machine-readable best practices for AI-assisted development of Azure-hosted web applications, derived from the Podcastify project. Feed this file into your AI coding agent at the start of a project to avoid common pitfalls.

---

## 1. Account & Subscription Separation

### Problem
Corporate Microsoft accounts have Conditional Access policies, Service Tree requirements, and admin consent gates that block rapid prototyping. Using corporate Azure subscriptions for personal projects creates compliance entanglements.

### Best Practice
- Use a **personal Microsoft account** (e.g., `@hotmail.com`, `@outlook.com`) with Visual Studio Enterprise Azure credits ($150/month) for prototyping.
- Keep the **AI coding agent** (GitHub Copilot) running on your **corporate account** for token utilization, while the **Azure resources** run on your **personal account**.
- Use `az login` with explicit tenant selection to avoid cross-tenant confusion.
- Store credentials in a `.gitignore`d `AZURE_CREDENTIALS.md` file in the repo root so the AI agent can reference them without leaking secrets.

### Commands
```bash
# Login to personal Azure account
az login --use-device-code
# When prompted, sign in with your PERSONAL account (e.g., pascason@hotmail.com)

# Verify correct subscription
az account show --query "{name:name, id:id, tenantId:tenantId}" -o table

# If multiple subscriptions, set the correct one
az account set --subscription "<subscription-id>"
```

---

## 2. M365 Developer Sandbox for Enterprise API Testing

### Problem
Enterprise APIs (Microsoft Graph, SharePoint, Teams, Copilot) require an M365 tenant with proper licenses. Corporate tenants block unregistered apps. Personal accounts lack M365 features.

### Best Practice
- Sign up for the **M365 Developer Program** at https://developer.microsoft.com/en-us/microsoft-365/dev-program
- Choose **"Instant sandbox"** with sample data packs (Users, Mail & Events, Teams) for pre-populated test data.
- Use the sandbox admin account (e.g., `admin@<domain>.onmicrosoft.com`) for Entra app registration — you have full admin rights, no Service Tree required.
- Register your app in **this sandbox tenant**, not the corporate tenant.
- Grant admin consent for all delegated permissions immediately — you are the admin.

### Entra App Registration Checklist
```
1. Go to https://entra.microsoft.com (signed in as sandbox admin)
2. App registrations → New registration
3. Name: <your-app-name>
4. Supported account types: "Accounts in this organizational directory only"
5. Redirect URI: Platform = SPA, Value = http://localhost:5173
6. After creation, go to API permissions → Add:
   - Microsoft Graph → Delegated → User.Read, Sites.Read.All, Files.Read.All
7. Click "Grant admin consent for <tenant>"
8. Save the Application (client) ID and Directory (tenant) ID
```

---

## 3. Authentication Configuration

### Problem
MSAL authentication has multiple failure modes: popup blockers in InPrivate/Incognito, CORS mismatches between `localhost` and `127.0.0.1`, tenant selection confusion when multiple Microsoft accounts exist, redirect URI mismatches between environments.

### Best Practice
- Use **`loginRedirect`** instead of `loginPopup` — popups are blocked in InPrivate/Incognito browsers and fail silently.
- Set MSAL authority to `https://login.microsoftonline.com/<tenant-id>` for single-tenant apps, or `https://login.microsoftonline.com/common` for multi-tenant.
- Register **all redirect URIs upfront** in the Entra app registration:
  ```
  http://localhost:5173
  http://127.0.0.1:5173
  https://<staging-url>
  https://<production-url>
  ```
- Handle `handleRedirectPromise()` in your app's entry point before rendering.
- Save deep-link state (URL params like `?tab=audio&jobId=xxx`) to `sessionStorage` before MSAL redirect, restore after login.

### MSAL Config Template
```typescript
const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage', // Use sessionStorage for InPrivate compatibility
    storeAuthStateInCookie: false,
  },
};

const loginRequest = {
  scopes: ['openid', 'profile', 'User.Read'],
  // Add Graph scopes only if the account type supports them
};
```

### Common Auth Errors and Fixes
| Error | Cause | Fix |
|-------|-------|-----|
| `AADSTS50011: redirect URI mismatch` | Redirect URI not registered in Entra | Add the exact origin URL to app registration |
| `Selected user account does not exist in tenant` | Wrong account picked at login | Use InPrivate browser, click "Use another account" |
| `Need admin approval` | Corporate tenant blocks unverified apps | Use M365 Dev Sandbox tenant instead |
| `does not meet criteria to access this resource` | Conditional Access policy | Use Dev Sandbox, not corporate tenant |

---

## 4. Deploy to Azure Container Apps (Not Localhost)

### Problem
Running on localhost means only you can access the app. Teammates can't test. Demos require your machine to be on. CORS configuration is fragile with localhost.

### Best Practice
- Deploy to **Azure Container Apps** (consumption plan) from day one. Cost is ~$0-5/month for low-traffic prototypes (scales to zero).
- Use a **single container** that serves both the Express API and the React SPA from the same origin — eliminates all CORS issues.
- Create **both staging and production** environments immediately.
- Use a simple `deploy.ps1` script to build, push, and deploy.

### Initial Setup Commands
```bash
# Create resource group
az group create --name rg-<project> --location eastus

# Create container registry
az acr create --resource-group rg-<project> --name <project>acr --sku Basic --admin-enabled true

# Create Container Apps environment
az containerapp env create \
  --name <project>-env \
  --resource-group rg-<project> \
  --location eastus

# Create production app
az containerapp create \
  --name <project> \
  --resource-group rg-<project> \
  --environment <project>-env \
  --image <project>acr.azurecr.io/<project>:latest \
  --target-port 3001 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 0.5 --memory 1Gi \
  --registry-server <project>acr.azurecr.io \
  --env-vars KEY1=value1 KEY2=value2

# Create staging app (identical config, different name)
az containerapp create \
  --name <project>-staging \
  --resource-group rg-<project> \
  --environment <project>-env \
  --image <project>acr.azurecr.io/<project>:latest \
  --target-port 3001 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 0.5 --memory 1Gi \
  --registry-server <project>acr.azurecr.io \
  --env-vars KEY1=value1 KEY2=value2
```

### Deployment Script Template
```powershell
# deploy.ps1
param(
    [ValidateSet('staging','production')]
    [string]$Target = 'staging'
)

$appName = if ($Target -eq 'staging') { '<project>-staging' } else { '<project>' }
$tag = Get-Date -Format 'yyyyMMdd-HHmmss'

Write-Host "Building and deploying to $Target..." -ForegroundColor Cyan

docker build -t <project>acr.azurecr.io/<project>:$tag .
az acr login --name <project>acr
docker push <project>acr.azurecr.io/<project>:$tag

az containerapp update `
  --name $appName `
  --resource-group rg-<project> `
  --image <project>acr.azurecr.io/<project>:$tag

Write-Host "$Target deployed: $tag" -ForegroundColor Green
```

---

## 5. Staging and Production Environments

### Problem
Pushing untested changes directly to production breaks the app for other users. Rolling back is manual and error-prone.

### Best Practice
- Always deploy to **staging first**, test, then promote to production.
- Both environments share the same Container Apps Environment (saves cost) but are separate Container Apps.
- Use the same Docker image tag for both — promote by updating the production app's image to the verified staging tag.
- Store environment-specific config (redirect URIs, feature flags) as Container App environment variables, not in code.

### Environment Variables Per Environment
```
# Shared (same in both)
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_SPEECH_KEY=<key>
AZURE_SPEECH_REGION=eastus
AZURE_STORAGE_CONNECTION_STRING=<conn-string>
ACS_EMAIL_CONNECTION_STRING=<conn-string>

# Per-environment
VITE_AZURE_CLIENT_ID=<same-app-id>
VITE_AZURE_TENANT_ID=<same-tenant-id>
# Redirect URIs are handled by MSAL using window.location.origin
```

---

## 6. Azure OpenAI Setup

### Problem
Azure OpenAI has regional availability constraints, model deployment requirements, and quota limits that differ from the OpenAI consumer API.

### Best Practice
- Create the Azure OpenAI resource in a region with GPT-4.1 availability (check https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models).
- Deploy the model via CLI or portal before making API calls.
- Use `DefaultAzureCredential` or API key auth — API key is simpler for prototypes.
- Set `max_tokens` to the model's actual limit (32,768 for GPT-4.1), never higher.
- For long-running inference (>60s), use async job patterns — return a job ID immediately, run inference in background, poll for results.

### Setup Commands
```bash
# Create Azure OpenAI resource
az cognitiveservices account create \
  --name <project>-openai \
  --resource-group rg-<project> \
  --kind OpenAI \
  --sku S0 \
  --location eastus2

# Deploy a model
az cognitiveservices account deployment create \
  --name <project>-openai \
  --resource-group rg-<project> \
  --deployment-name gpt-4.1 \
  --model-name gpt-4.1 \
  --model-version "2025-04-14" \
  --model-format OpenAI \
  --sku-capacity 80 \
  --sku-name Standard

# Get the key
az cognitiveservices account keys list \
  --name <project>-openai \
  --resource-group rg-<project> \
  --query "key1" -o tsv
```

---

## 7. Azure Speech Service Setup

### Problem
Azure Speech has multiple tiers (free F0 vs standard S0), voice quality tiers (standard, HD, DragonHD), and per-request duration limits.

### Best Practice
- Use **S0 Standard tier** for production (F0 free tier has strict rate limits).
- Use **DragonHD voices** (`en-US-Andrew:DragonHDLatestNeural`) for highest quality — they auto-detect emotion from text.
- Split long text into **segments of ~1200 words** (~8 minutes of audio) to stay within the 600,000ms per-request limit.
- Concatenate audio segments in-memory using Buffer before returning.
- Add **retry logic** (3 attempts with backoff) for transient Speech API failures.

### Setup Commands
```bash
az cognitiveservices account create \
  --name <project>-speech \
  --resource-group rg-<project> \
  --kind SpeechServices \
  --sku S0 \
  --location eastus
```

---

## 8. Persistent Storage with Azure Blob

### Problem
Azure Container Apps (consumption plan) have ephemeral file systems. Generated files (audio, images) are lost on container restart, scale-to-zero, or redeployment.

### Best Practice
- **Never store generated files only on the local filesystem.** Always upload to Azure Blob Storage.
- Use the pattern: generate locally → upload to blob → serve via a download endpoint that checks local cache first, falls back to blob.
- Create a dedicated container in Blob Storage for each file type (e.g., `audio`, `images`).

### Setup Commands
```bash
az storage account create \
  --name <project>storage \
  --resource-group rg-<project> \
  --sku Standard_LRS \
  --location eastus

az storage container create \
  --name audio \
  --account-name <project>storage
```

### Code Pattern
```typescript
import { BlobServiceClient } from '@azure/storage-blob';

const blobClient = BlobServiceClient.fromConnectionString(process.env.AZURE_STORAGE_CONNECTION_STRING!);
const container = blobClient.getContainerClient('audio');

// Upload after generation
async function uploadToBlob(filename: string, buffer: Buffer): Promise<string> {
  const blob = container.getBlockBlobClient(filename);
  await blob.uploadData(buffer, { blobHTTPHeaders: { blobContentType: 'audio/mpeg' } });
  return blob.url;
}

// Download with local cache fallback
async function getAudio(filename: string): Promise<Buffer> {
  const localPath = path.join(AUDIO_DIR, filename);
  if (fs.existsSync(localPath)) return fs.readFileSync(localPath);

  const blob = container.getBlockBlobClient(filename);
  const download = await blob.download(0);
  const buffer = await streamToBuffer(download.readableStreamBody!);
  fs.writeFileSync(localPath, buffer); // Cache locally
  return buffer;
}
```

---

## 9. Email Notifications with Azure Communication Services

### Problem
SMTP-based email (nodemailer) requires configuring an external SMTP server. Ethereal (test SMTP) accepts but never delivers emails.

### Best Practice
- Use **Azure Communication Services Email** — native Azure service, no SMTP config needed.
- Create an ACS resource + Email Communication Service + managed domain (auto-verified, SPF/DKIM/DMARC configured).
- Sender address is `DoNotReply@<guid>.azurecomm.net` — functional but not branded.

### Setup Commands
```bash
# Create ACS resource
az communication create \
  --name <project>-comm \
  --resource-group rg-<project> \
  --data-location "United States"

# Create Email service (portal only — CLI support limited)
# Go to Azure Portal → Create "Email Communication Service" → link to ACS resource
```

---

## 10. Handling Long-Running Operations

### Problem
Azure Container Apps has a ~240 second ingress proxy timeout. Any HTTP request that takes longer is killed with a 502/504, regardless of server-side timeout settings. This affects LLM inference for long content and audio synthesis for long episodes.

### Best Practice
- **Never run operations >60s synchronously in an HTTP request handler.**
- Use the **async job pattern**:
  1. `POST /api/start-job` → validate input, create job ID, start async work, return `{ jobId }` in <1s
  2. Background function runs the actual work (LLM call, TTS synthesis)
  3. `GET /api/job/:id` → return `{ status: 'running' | 'completed' | 'failed', result?, error? }`
  4. Frontend polls every 5-10 seconds

### Code Pattern
```typescript
const jobs = new Map<string, { status: string; result?: any; error?: string }>();

app.post('/api/start-job', (req, res) => {
  const jobId = crypto.randomUUID();
  jobs.set(jobId, { status: 'running' });
  res.json({ jobId }); // Return immediately

  // Run in background (not awaited)
  doExpensiveWork(req.body)
    .then(result => jobs.set(jobId, { status: 'completed', result }))
    .catch(err => jobs.set(jobId, { status: 'failed', error: err.message }));
});

app.get('/api/job/:id', (req, res) => {
  const job = jobs.get(req.params.id);
  if (!job) return res.status(404).json({ error: 'Job not found' });
  res.json(job);
});
```

---

## 11. Frontend Serving Strategy

### Problem
Vite dev server doesn't work reliably in all environments. Separate frontend/backend ports create CORS complexity. SPA routing breaks with static file servers.

### Best Practice
- **Build the React app and serve it from Express** in the same container. Zero CORS issues.
- In the Dockerfile: `npm run build` the frontend, copy `dist/` into the backend's static directory.
- Express serves the SPA with a catch-all route for client-side routing.

### Dockerfile Pattern
```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
COPY shared/ ../shared/
ARG VITE_AZURE_CLIENT_ID
ARG VITE_AZURE_TENANT_ID
RUN npm run build

# Stage 2: Build backend
FROM node:20-alpine AS backend
WORKDIR /app/backend
COPY backend/package*.json ./
RUN npm ci
COPY backend/ .
COPY shared/ ../shared/
RUN npm run build

# Stage 3: Production
FROM node:20-alpine
WORKDIR /app
COPY --from=backend /app/backend/dist ./dist
COPY --from=backend /app/backend/node_modules ./node_modules
COPY --from=backend /app/backend/package.json ./
COPY --from=frontend /app/frontend/dist ./public

EXPOSE 3001
CMD ["node", "dist/index.js"]
```

### Express SPA Serving
```typescript
import path from 'path';
import express from 'express';

const app = express();

// API routes first
app.use('/api', apiRouter);

// Serve static frontend
app.use(express.static(path.join(__dirname, '..', 'public')));

// SPA catch-all (must be last)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});
```

---

## 12. Cost Management

### Estimated Monthly Costs on Personal Azure Credits ($150/month)
| Resource | Estimated Cost |
|----------|---------------|
| Container Apps (consumption, scale-to-zero) | $0–5 |
| Container Registry (Basic) | ~$5 |
| Azure OpenAI (GPT-4.1, ~500K tokens/month) | ~$15–30 |
| Azure Speech (S0, ~2M characters/month) | ~$16 |
| Blob Storage (Standard LRS, <1GB) | ~$0.02 |
| Azure Communication Services Email | ~$0 (first 1K emails free) |
| **Total** | **~$36–56/month** |

### Cost Optimization Tips
- Set Container Apps `min-replicas: 0` to scale to zero when idle.
- Use Container Registry Basic tier (not Standard/Premium).
- Monitor Azure OpenAI token usage — long podcast scripts consume 15K–30K tokens each.
- Use Speech F0 (free tier) during development, S0 only for production.
- Use `az cost` CLI or Azure Portal Cost Analysis to track spend weekly.

---

## 13. Git & Deployment Workflow

### Best Practice
```
main branch → always deployable
  ↓
deploy.ps1 -Target staging → test on staging URL
  ↓
manual verification by stakeholder
  ↓
deploy.ps1 -Target production → promote to production
  ↓
update CHANGELOG.md with user-facing changes
```

### Commit Discipline
- Commit after each logical feature or fix, not in bulk.
- Use descriptive commit messages: `"fix: PDF parsing failure due to pdf-parse v2 API change"`
- Push to remote frequently — AI agent sessions are ephemeral, uncommitted code can be lost.
- Keep `AZURE_CREDENTIALS.md` and `.env` files in `.gitignore`.

---

## 14. Common Pitfalls Summary

| Pitfall | Impact | Prevention |
|---------|--------|------------|
| Using `loginPopup` for MSAL | Fails in InPrivate/Incognito | Use `loginRedirect` |
| CORS with `localhost` vs `127.0.0.1` | "Failed to fetch" errors | Register both origins, or serve from same origin |
| Storing files on container filesystem | Files lost on restart/deploy | Upload to Azure Blob Storage immediately |
| Synchronous HTTP for LLM/TTS calls | 502 timeout after 240s | Use async job pattern with polling |
| `pdf-parse` v2 vs v1 API | Silent PDF extraction failure | Pin `pdf-parse@^1.1.1` |
| Azure OpenAI `max_tokens` > model limit | API rejection | Cap at model's actual limit (32,768 for GPT-4.1) |
| Not setting up staging environment | Broken production deploys | Create staging Container App from day one |
| Hardcoding client IDs in Dockerfile | Auth breaks across environments | Use build args: `ARG VITE_AZURE_CLIENT_ID` |
