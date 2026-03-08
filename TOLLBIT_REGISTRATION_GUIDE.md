# Tollbit Registration & Configuration Guide

## Carli Wines — Roberto Carli, CMS-Certified Sommelier

This guide covers everything you need to do to complete the Tollbit integration
for your sommelier consulting website. The infrastructure is already deployed —
you just need to complete the registration steps below.

---

## Architecture Summary

| Component | URL / Resource |
|-----------|---------------|
| **Website (SWA)** | https://happy-hill-02307e60f.4.azurestaticapps.net |
| **Front Door endpoint** | https://carliwines-gsd2gqgce4h0akew.z01.azurefd.net |
| **Target custom domain** | `carliwines.robertocarli.com` |
| **Tollbit bot subdomain** | `tollbit.carliwines.robertocarli.com` |
| **GitHub repo** | https://github.com/pascason/carliwines-tollbit |
| **Azure Resource Group** | `rg-tollbit` (East US) |
| **Front Door profile** | `carliwines-fd` (Standard SKU) |
| **Front Door ID** | `8512e3d7-a065-498f-9ed3-3fb75760318e` |

### How it works

```
Human visitor → Front Door → SWA (normal HTML page)
AI bot (GPTBot, ClaudeBot, etc.) → Front Door → 302 redirect → tollbit.carliwines.robertocarli.com → Tollbit edge → clean Markdown
```

The Front Door has a rule set called `TollbitBotRedirect` that detects AI bot
User-Agents and redirects them to the Tollbit subdomain.

---

## PART 1: GoDaddy DNS Configuration

Your domain `robertocarli.com` is registered at **GoDaddy** (nameservers:
`ns57.domaincontrol.com`, `ns58.domaincontrol.com`).

### Step 1: Log into GoDaddy

1. Go to https://sso.godaddy.com
2. Sign in with your account (likely `pascason@hotmail.com`)
3. If you forgot your password: https://sso.godaddy.com/account/recovery

### Step 2: Navigate to DNS Management

1. Go to **My Products** → find `robertocarli.com`
2. Click **DNS** or **Manage DNS**

### Step 3: Add CNAME record for `carliwines`

This points your custom subdomain to Azure Front Door.

| Field | Value |
|-------|-------|
| **Type** | `CNAME` |
| **Name** | `carliwines` |
| **Value** | `carliwines-gsd2gqgce4h0akew.z01.azurefd.net` |
| **TTL** | `600` (10 minutes) or `3600` (1 hour) |

### Step 4: Add TXT record for domain verification

Tollbit will give you a verification string when you add the property.
You'll add it as:

| Field | Value |
|-------|-------|
| **Type** | `TXT` |
| **Name** | `carliwines` (or `_tollbit-validation.carliwines` if needed) |
| **Value** | *(copy from Tollbit dashboard — looks like `tollbit-domain-verification=...`)* |
| **TTL** | `3600` |

### Step 5: Add NS records for `tollbit.carliwines`

These delegate the Tollbit subdomain to Tollbit's edge servers. You need **4 NS records**:

| Field | Value |
|-------|-------|
| **Type** | `NS` |
| **Name** | `tollbit.carliwines` |
| **Value** | `ns1.edge.tollbit.com` |

| **Type** | `NS` |
| **Name** | `tollbit.carliwines` |
| **Value** | `ns2.edge.tollbit.com` |

| **Type** | `NS` |
| **Name** | `tollbit.carliwines` |
| **Value** | `ns3.edge.tollbit.com` |

| **Type** | `NS` |
| **Name** | `tollbit.carliwines` |
| **Value** | `ns4.edge.tollbit.com` |

> **Note:** GoDaddy may not allow NS records for subdomains through the UI.
> If that's the case, you have two options:
> 1. Contact GoDaddy support and ask them to add the NS records
> 2. Delegate `carliwines.robertocarli.com` to Azure DNS, then add NS records there
> 3. Use Tollbit's alternative verification methods (they support multiple approaches)

### Step 6: Add custom domain to Front Door (after CNAME propagates)

After adding the CNAME in GoDaddy, run this command (or I can run it for you):

```powershell
# Validate the domain
az afd custom-domain create `
  --custom-domain-name carliwines-domain `
  --profile-name carliwines-fd `
  --resource-group rg-tollbit `
  --host-name carliwines.robertocarli.com `
  --certificate-type ManagedCertificate `
  --minimum-tls-version TLS12

# Associate it with the route
az afd route update `
  --route-name default-route `
  --endpoint-name carliwines `
  --profile-name carliwines-fd `
  --resource-group rg-tollbit `
  --custom-domains carliwines-domain
```

---

## PART 2: Tollbit Publisher Registration

This is for **monetizing your website content** — letting AI bots pay to access
your sommelier content.

### Step 1: Create a Publisher Account

1. Go to **https://app.tollbit.com/sign-up**
2. Click **"Continue with Google"** or sign up with email
3. Create your organization:
   - **Organization name:** `Carli Wines` (or `Roberto Carli Sommelier`)
   - This represents your top-level entity

### Step 2: Add Your Property

1. Once logged in, you'll see the property overview page
2. Click to add a new property
3. Enter your domain: `carliwines.robertocarli.com`
4. Tollbit will attempt to fetch your `robots.txt` and sitemap

> **Note:** The site has a `robots.txt` and sitemap at:
> - `https://happy-hill-02307e60f.4.azurestaticapps.net/robots.txt`
> - After custom domain: `https://carliwines.robertocarli.com/robots.txt`

### Step 3: Verify Your Property

1. Tollbit will show you a **TXT record value** (something like `tollbit-domain-verification=abc123...`)
2. Go to GoDaddy and add the TXT record as described in Part 1, Step 4
3. Also add the 4 NS records for `tollbit.carliwines` (Part 1, Step 5)
4. Click "Verify" in the Tollbit dashboard
5. DNS changes can take up to 48 hours to propagate, but usually 15-30 minutes

### Step 4: Configure Azure Integration

Tollbit has specific Azure / Front Door integration documentation.

1. In the Tollbit dashboard, go to **Integrations**
2. Select **Microsoft (Azure)**
3. Follow their guide for:
   - **Setting up Logging** — Create a Diagnostic Setting in your Front Door instance that sends access logs to a Storage Account
   - **Bot Paywall** — Already done! The `TollbitBotRedirect` rule set is configured
4. Contact `team@tollbit.com` with your storage account log path pattern for analytics setup

> **What's already configured for you:**
> - Front Door rule set `TollbitBotRedirect` with rule `RedirectAIBots`
> - Detects: GPTBot, ChatGPT-User, ClaudeBot, Anthropic, Google-Extended, CCBot, PerplexityBot, Bytespider
> - 302 redirects matching bots to `tollbit.carliwines.robertocarli.com`

### Step 5: Configure Marketplace

1. Go to **Marketplace** in the Tollbit dashboard
2. **Set Rates** — Price your content (per-page or per-request)
3. **Licenses** — Choose a license type for your content
4. **Content Formatting** — Configure how your content is served to AI bots (Markdown is default)
5. **Content Controls** — Choose what content is available vs. blocked

---

## PART 3: Tollbit Developer Registration

This is for **consuming other publishers' content** via Tollbit's API — testing
the developer side.

### Step 1: Create a Developer Account

1. Go to **https://hack.tollbit.com/sign-up**
2. Sign up with Google or email (can be the same account)
3. You may need to use the same org or create a separate one

### Step 2: Register Your Agent ID

1. Go to **Dashboard > Home** at https://hack.tollbit.com/home
2. Register a unique **AgentID** — this is your bot's username
   - Suggestion: `carliwines-bot` or `roberto-sommelier`
   - This becomes part of your User-Agent header:
     ```
     Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; carliwines-bot/1.0; +https://carliwines.robertocarli.com
     ```

### Step 3: Copy Your Secret Key

1. Go to **Dashboard > Access** at https://hack.tollbit.com/access
2. Copy your **secret key** — keep it safe!
3. You'll use this key in the test harness

### Step 4: Set Up Billing

1. Go to **Dashboard > Billing** at https://hack.tollbit.com/billing
2. Add a payment method via Stripe (needed to actually access paid content)

### Step 5: Configure the Test Harness

1. Navigate to the test tool directory:
   ```powershell
   cd C:\Repos\tollbit\tools\developer
   ```

2. Copy the example env file:
   ```powershell
   Copy-Item .env.example .env
   ```

3. Edit `.env` with your actual values:
   ```
   TOLLBIT_API_KEY=your_secret_key_from_step_3
   TOLLBIT_AGENT_ID=carliwines-bot
   SITE_DOMAIN=carliwines.robertocarli.com
   ```

4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

5. Run the full test flow:
   ```powershell
   python tollbit_test.py full-flow "wine education"
   ```

### Available Test Commands

| Command | Description |
|---------|-------------|
| `python tollbit_test.py search "wine pairing"` | Licensed search across Tollbit |
| `python tollbit_test.py rate carliwines.robertocarli.com` | Check content rates |
| `python tollbit_test.py get-content carliwines.robertocarli.com/learn/blind-tasting-guide` | Fetch a specific page |
| `python tollbit_test.py catalog carliwines.robertocarli.com` | List available content |
| `python tollbit_test.py full-flow "sommelier"` | End-to-end test of all APIs |

---

## PART 4: Post-Registration Checklist

- [ ] GoDaddy: CNAME record `carliwines` → Front Door endpoint
- [ ] GoDaddy: TXT record for Tollbit domain verification
- [ ] GoDaddy: 4 NS records for `tollbit.carliwines` → Tollbit edge servers
- [ ] Azure: Custom domain added to Front Door
- [ ] Azure: Front Door diagnostic logging → Storage Account (for Tollbit analytics)
- [ ] Tollbit Publisher: Account created at app.tollbit.com
- [ ] Tollbit Publisher: Property `carliwines.robertocarli.com` added
- [ ] Tollbit Publisher: Property verified via DNS
- [ ] Tollbit Publisher: Azure integration configured
- [ ] Tollbit Publisher: Marketplace rates and licenses set
- [ ] Tollbit Developer: Account created at hack.tollbit.com
- [ ] Tollbit Developer: AgentID registered
- [ ] Tollbit Developer: Secret key copied
- [ ] Tollbit Developer: Test harness `.env` configured
- [ ] Tollbit Developer: `full-flow` test passes

---

## Costs Summary

| Service | Cost |
|---------|------|
| Azure Static Web Apps | **Free** (Free tier) |
| Azure Front Door Standard | **~$35/month** |
| Azure DNS (if used) | **~$0.50/month** per zone |
| Tollbit Publisher | **Free** (you earn from AI bots) |
| Tollbit Developer | **Pay-per-use** (varies by publisher) |
| GoDaddy domain (robertocarli.com) | Already owned |

---

## Useful Links

- **Tollbit Publisher Dashboard:** https://app.tollbit.com
- **Tollbit Developer Dashboard:** https://hack.tollbit.com
- **Tollbit Docs (Publisher):** https://docs.tollbit.com/docs/a-tollbooth-for-your-content
- **Tollbit Docs (Developer):** https://docs.tollbit.com/docs/introduction
- **Tollbit Azure Integration:** https://docs.tollbit.com/docs/azure
- **Tollbit Python SDK:** https://github.com/tollbit/tollbit-python-sdk
- **Azure Front Door Portal:** https://portal.azure.com/#@/resource/subscriptions/5e2ef634-40ff-4c58-bc2d-ac0ed59dbb6f/resourceGroups/rg-tollbit/providers/Microsoft.Cdn/profiles/carliwines-fd/overview
- **SWA Portal:** https://portal.azure.com/#@/resource/subscriptions/5e2ef634-40ff-4c58-bc2d-ac0ed59dbb6f/resourceGroups/rg-tollbit/providers/Microsoft.Web/staticSites/carliwines-tollbit/overview
- **GitHub Repo:** https://github.com/pascason/carliwines-tollbit

---

## Troubleshooting

### Front Door still showing 404
Azure Front Door Standard deployments can take 10-30 minutes to propagate.
The `deploymentStatus` starts at `NotStarted` → `InProgress` → `Deployed`.
Check status with:
```powershell
az afd endpoint show --endpoint-name carliwines --profile-name carliwines-fd --resource-group rg-tollbit --query "deploymentStatus" -o tsv
```

### SWA direct access works but Front Door doesn't
This is normal during initial deployment. The SWA is always accessible at:
https://happy-hill-02307e60f.4.azurestaticapps.net

### DNS changes not propagating
Use https://www.whatsmydns.net/ to check DNS propagation worldwide.
GoDaddy DNS changes typically propagate within 15-30 minutes.

### Can't add NS records in GoDaddy
GoDaddy's UI may not support NS records for subdomains.
Contact GoDaddy support or consider delegating the subdomain to Azure DNS.
