# Fast, Easy & Cheap Production Guide: GitHub + Render.com + `bikozava.com` Domain

This guide walks you through publishing **Bikozava** live on **`https://bikozava.com`** using the **fastest, easiest, and lowest-cost** stack (~**$10.44/year** total for the domain, plus **$0/month** on Render Free + Supabase Free, or **$7/month** on Render Starter for 24/7 instant wake).

---

## Step 1: Upload Your Project to GitHub (2 Minutes on Windows)

1. Create a free account at **[github.com](https://github.com)** (if you don't already have one) and click **New Repository**:
   - **Repository name**: `bikozava`
   - **Visibility**: **Private** (recommended so your code stays private)
   - Click **Create repository** and copy the repository URL (e.g. `https://github.com/YOUR_USERNAME/bikozava.git`).
2. Make sure **Git for Windows** is installed (**[git-scm.com/download/win](https://git-scm.com/download/win)**).
3. Inside your extracted `bikozava` folder on Windows, double-click **`push_to_github.bat`** (or run `.\push_to_github.ps1` in PowerShell).
4. Paste your GitHub repository URL when prompted.
   - Your `.gitignore` file automatically prevents `.env` and local database files from ever being uploaded to GitHub.

---

## Step 2: Create a Free Permanent PostgreSQL Database on Supabase (2 Minutes)

Because Render's Free tier resets local disk files whenever the server restarts, connecting a free **Supabase PostgreSQL** database ensures your wedding invitations and RSVPs are stored permanently for **$0/month**:

1. Sign in at **[supabase.com](https://supabase.com)** and click **New Project** (Name: `bikozava`).
2. Once the project is ready, click **Connect** (top bar) → **URI** → **Transaction Pooler (Port 6543)** or **Session Pooler (Port 5432)** and copy the connection string:
   ```text
   postgresql://postgres.[PROJECT-REF]:[YOUR-DB-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
3. *(Optional)* Bikozava automatically creates all tables and seeds all **24 templates** + the `ismail_shrin` demo on first startup! You can also run `migrations/001_initial_schema.sql` in the Supabase SQL Editor if you prefer.

---

## Step 3: Deploy on Render.com (2 Minutes)

Your project already includes **`render.yaml`**, **`Procfile`**, **`runtime.txt`**, and **`gunicorn.conf.py`**:

1. Sign in at **[dashboard.render.com](https://dashboard.render.com)**.
2. Click **New +** → **Web Service** (or **Blueprint**) and select your **`bikozava`** GitHub repository.
3. Render automatically fills in the settings from `render.yaml` (or use these if entering manually):
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c gunicorn.conf.py wsgi:app`
4. Under **Environment Variables**, set:
   | Key | Value |
   | :--- | :--- |
   | `SECRET_KEY` | Click **Generate** (or paste a 64-character hex string) |
   | `DATABASE_URL` | Paste your **Supabase PostgreSQL URI** from Step 2 |
   | `ADMIN_INITIAL_USERNAME` | `admin` |
   | `ADMIN_INITIAL_PASSWORD` | Choose a strong password (e.g. `BikozavaRoyal!2026#`) |
   | `PUBLIC_BASE_URL` | `https://bikozava.com` |
   | `SESSION_COOKIE_SECURE` | `1` |
   | `TRUST_PROXY_HEADERS` | `1` |
5. Click **Create Web Service**.
   - Within ~90 seconds, your site will be live at `https://bikozava-wedding-platform.onrender.com`!
   - **Tip on Free vs. $7/month Starter Plan**: Render's **$0/month Free plan** sleeps after 15 minutes of inactivity (taking ~20 seconds to wake up on the next visit). You can keep it awake for free by adding your `/healthz` URL (`https://bikozava.com/healthz`) to **[UptimeRobot.com](https://uptimerobot.com)** (free 5-minute ping monitor), or upgrade to Render's **$7/month Starter** plan with Persistent Disk (`/var/data`) during busy wedding months.

---

## Step 4: Buy `bikozava.com` Cheaply & Connect It with Free SSL (5 Minutes)

### Best & Cheapest Places to Buy `bikozava.com`
1. **[Cloudflare Registrar](https://www.cloudflare.com/products/registrar/)** *(Cheapest long-term — ~$10.44/year with $0 markup and free renewal at wholesale ICANN cost, plus free CDN & DDoS protection)*
2. **[Porkbun.com](https://porkbun.com)** *(~$10.73/year, very simple interface, supports cards & PayPal)*
3. **[Namecheap.com](https://www.namecheap.com)** *(~$10–$12 first year, easy DNS management)*

### Connecting `bikozava.com` to Render
1. In your **Render Dashboard**, open your `bikozava` Web Service → click **Settings** → scroll to **Custom Domains**.
2. Click **Add Custom Domain**, type **`bikozava.com`**, and click **Save** (Render will also add `www.bikozava.com`).
3. In your domain provider's **DNS Settings** (Cloudflare, Porkbun, or Namecheap), add the two records shown by Render:
   - **Record 1 (Root domain `@`)**:
     - **Type**: `A`
     - **Name / Host**: `@`
     - **Value / Points to**: `216.24.57.1`
   - **Record 2 (`www` subdomain)**:
     - **Type**: `CNAME`
     - **Name / Host**: `www`
     - **Target**: `bikozava-wedding-platform.onrender.com` *(your `.onrender.com` hostname)*
   - *(Note: If using Cloudflare DNS, set the proxy cloud icon to **DNS Only / Grey Cloud** for 2 minutes while Render clicks **Verify** and issues your free Let's Encrypt SSL certificate, then you can turn Orange Cloud back on with SSL mode set to **Full (Strict)**).*
4. Render automatically provisions your **HTTPS / SSL certificate** for free. Your invitations will immediately work at:
   - `https://bikozava.com/ismail_shrin`
   - `https://bikozava.com/ahmad_lavin`
   - `https://bikozava.com/admin/login`
