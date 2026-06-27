# Mini CRM — Full-Stack Assignment

Stack: **HTML/CSS/JS frontend** + **Python (Flask) backend** + **MySQL database**

Features (matching the task brief):
- Login (with a one-time `/api/register` route to create your first user)
- Lead Management (create / edit / delete leads)
- Dashboard (total leads + count by status + recent leads)
- Search (by name, email, company, phone) + filter by status
- Notes (per-lead notes thread)
- Lead Status (New → Contacted → Qualified → Proposal → Won/Lost)
- External API integration: **Clearbit Logo API** — when you add a lead's
  company website, the backend automatically fetches that company's logo
  and shows it in the leads table and lead detail view. No API key needed.

```
crm-project/
├── backend/
│   ├── app.py            <- Flask app + all API routes
│   ├── requirements.txt
│   ├── schema.sql        <- run once on your MySQL database
│   ├── Procfile          <- tells Render how to start the app
│   └── .env.example      <- copy to .env locally
└── frontend/
    ├── index.html        <- login page
    ├── dashboard.html     <- main app (leads, dashboard, notes)
    ├── css/style.css
    └── js/{config.js, app.js}
```

---

## 1. What "Lead Management" means (quick explanation)

A **lead** is a potential customer — someone who showed interest but hasn't
bought anything yet (e.g. filled a contact form, called in, was referred by
someone). **Lead management** is the workflow a CRM gives you to handle
those people from "just a name" to "paying customer":

1. **Capture** — store their contact details and where they came from (the `source` field: website, referral, cold call...).
2. **Track status** — move them through a pipeline so your team knows where each one stands (`New → Contacted → Qualified → Proposal → Won/Lost` in this build).
3. **Record activity** — notes/calls/emails logged against that lead so anyone on the team has context.
4. **Search/filter** — quickly find a lead or see "all leads stuck at Proposal," etc.
5. **Report** — a dashboard showing totals and breakdowns, so management can see pipeline health at a glance.

That's exactly what Login, Dashboard, Search, Notes, and Lead Status in the task brief are asking you to build *around* — they're the supporting pieces of one feature: lead management.

---

## 2. Run it locally first

### Database
You need a MySQL server. Easiest for local dev: install MySQL locally, or just skip ahead and use the free Aiven database from step 3 even while developing locally.

```bash
mysql -u root -p -e "CREATE DATABASE crm_db;"
mysql -u root -p crm_db < backend/schema.sql
```

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env     # then edit .env with your DB credentials
python app.py            # runs on http://localhost:5000
```
On first run it also auto-creates tables if `schema.sql` wasn't run.

Create your first login:
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'
```

### Frontend
Just open `frontend/index.html` in a browser (or run `python -m http.server 8080` inside `frontend/` and visit `http://localhost:8080`). `js/config.js` already points at `http://localhost:5000`.

---

## 3. Deploy everything for free (no payment, no card)

You need 3 things online: a database, the backend API, and the frontend. Here's a path that's genuinely free with no credit card:

| Piece | Service | Why |
|---|---|---|
| MySQL database | **Aiven** (aiven.io) | Free MySQL plan, 1GB RAM/1GB disk, runs forever, no credit card |
| Backend (Flask API) | **Render** (render.com) | Free web service tier, no credit card, deploys straight from GitHub |
| Frontend (HTML/CSS/JS) | **GitHub Pages** or **Netlify** | Free static hosting, no credit card |

> Heads-up on the free tier: Render's free web service "sleeps" after 15 minutes of no traffic and takes ~30–60 seconds to wake up on the next request. That's fine for an assignment demo — just open the link a minute before your interview so it's already awake. If you want it always-on instantly, that requires a paid plan, which you said you want to avoid, so this is the trade-off.

### Step A — Create the free MySQL database (Aiven)
1. Sign up at https://aiven.io (no credit card required).
2. Create a new service → choose **MySQL** → pick the **Free** plan.
3. Once it's running, open the service → **Overview** tab → copy the **Host**, **Port**, **User**, **Password**, **Database name** (default is `defaultdb`, or create one called `crm_db`).
4. Run your schema against it from your machine:
   ```bash
   mysql -h <host> -P <port> -u <user> -p <database> < backend/schema.sql
   ```
   (Aiven requires SSL — if `mysql` CLI complains, add `--ssl-mode=REQUIRED`.)

### Step B — Deploy the backend (Render)
1. Push the `backend/` folder to a GitHub repo (you can push the whole `crm-project` folder, that's fine too).
2. Sign up at https://render.com (no credit card required) and connect your GitHub.
3. **New → Web Service** → select your repo.
   - Root directory: `backend` (if you pushed the whole project)
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Instance type: **Free**
4. Add Environment Variables (Render dashboard → your service → Environment):
   ```
   SECRET_KEY        = (any long random string)
   DB_HOST           = <your Aiven host>
   DB_PORT           = <your Aiven port>
   DB_USER           = <your Aiven user>
   DB_PASSWORD       = <your Aiven password>
   DB_NAME           = crm_db
   FRONTEND_ORIGIN   = <your frontend URL, e.g. https://yourname.github.io>
   ```
5. Deploy. Render gives you a URL like `https://your-app.onrender.com`. Test it: visit `https://your-app.onrender.com/api/health` — should return `{"status": "ok"}`.
6. Create your first user (replace the URL):
   ```bash
   curl -X POST https://your-app.onrender.com/api/register \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"yourpassword"}'
   ```

### Step C — Deploy the frontend (GitHub Pages)
1. In `frontend/js/config.js`, change the line to your Render URL:
   ```js
   const API_BASE = "https://your-app.onrender.com";
   ```
2. Push the `frontend/` folder to a GitHub repo.
3. Repo → Settings → Pages → Source: deploy from branch → select the branch/folder containing `frontend`.
4. GitHub gives you a URL like `https://yourname.github.io/your-repo/`. That's the link you submit.

(Netlify works the same way if you'd rather drag-and-drop the `frontend` folder at app.netlify.com — also free, no card.)

### One important gotcha: cookies across domains
Your frontend (`github.io`) and backend (`onrender.com`) are different domains, so the login session cookie needs `SameSite=None; Secure` — already set in `app.py`. This **requires HTTPS**, which both Render and GitHub Pages give you by default, so you don't need to do anything — just make sure you use the `https://` links, not `http://`.

---

## 4. For the live interview

Things to be ready to explain (these map to the mock questions in the brief):
- **If users doubled**: move off the free tiers (Render Starter $7/mo removes sleep, Aiven's paid tier adds RAM/connections), add connection pooling, add an index on `leads.status`/`leads.name` (already in `schema.sql`), consider caching dashboard stats.
- **Security**: passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2), sessions are server-side with `httponly` cookies, CORS is locked to your frontend origin via `FRONTEND_ORIGIN`, all SQL goes through SQLAlchemy's ORM (parameterized — no raw string SQL, so no SQL injection).
- **Architecture**: 3-tier — static frontend, stateless Flask API, managed MySQL — each deployed/scaled independently.
- **Troubleshooting a crash**: check Render's live logs first, check `/api/health`, check Aiven's connection limits/uptime, then check recent deploys for the change that broke it.
