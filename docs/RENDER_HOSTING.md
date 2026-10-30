# Put CricLive on the internet with Render (free)

After these steps your website, API and live scores all run at one address,
for example `https://criclive.onrender.com`. Anyone can open it on any phone
or computer, and the Android app can use it from anywhere (no Wi-Fi needed).

## What you get on the free plan (please read)

| Thing | Free plan limit | What it means for you |
|---|---|---|
| Web service (website + API + live) | Goes to **sleep after 15 minutes** with no visitors | The first visit after a quiet time takes about **1 minute** to load. After that it is fast. |
| PostgreSQL database | **Expires 30 days** after you create it (Render gives a short grace period, then deletes it) | Before day 30, either upgrade the database to a paid plan, or move to a free database that does not expire (see "Keep your data after 30 days" below). |
| Uploaded logos / photos | Not kept | Pictures you upload are lost when the service restarts or redeploys. Scores, teams and players are safe in the database. |
| Free hours | 750 hours per month | Enough for one service running all month. |

Render can change these limits; check https://render.com/docs/free if something looks different.

## Step 1: Make a Render account

1. Open https://render.com and click **Get Started**.
2. Choose **Sign up with GitHub** and allow access. Use the same GitHub
   account that owns the `cricket` repository.

## Step 2: Create everything with one click (Blueprint)

1. In Render, click **New +** (top right) → **Blueprint**.
2. Pick the **cricket** repository. (If you don't see it, click
   **Configure account** and give Render access to it.)
3. Branch: **main**. Render reads the file `render.yaml` and shows:
   - `criclive` (web service, Free)
   - `criclive-db` (PostgreSQL, Free)
4. It asks for **ADMIN_PASSWORD**. Type a strong password and write it down.
   This is the password for the `admin` account and for all demo accounts.
5. Click **Apply** (or **Deploy Blueprint**).
6. Wait 5–10 minutes for the first build. Open the `criclive` service; when
   it says **Live**, click the address at the top (like
   `https://criclive.onrender.com`).

## Step 3: Log in

- Website: open your address and click **Log in**.
- Username **admin**, password = your ADMIN_PASSWORD.
- Demo accounts also work with the same password: `superadmin`, `tadmin`,
  `scorer1` … `scorer4`, `viewer`.
- Django admin page: `https://<your-address>/admin/`

Don't want the demo tournaments? Before Step 2's **Apply**, or later in
`criclive` → **Environment**, set `SEED_DEMO` to `false`. (Demo data is only
added once, on the very first start, when the database is empty.)

## Step 4: Point the Android app at Render

1. Install the latest app from the GitHub release page (the APK built after
   this change knows how to use `https` addresses).
2. In the app: **More → Settings → Server address**.
3. Type your Render address, for example `https://criclive.onrender.com`
   (no `:8000` at the end).
4. Tap **Save & Test connection**. If it fails the first time, the server was
   asleep; wait one minute and try again.

## Updating the site later

Every time new code is pushed to the `main` branch, Render rebuilds and
restarts the site by itself (takes a few minutes).

## Keep your data after 30 days

Pick one, before the free database expires:

- **Upgrade**: in Render open `criclive-db` → **Upgrade** to the cheapest
  paid plan. Nothing else changes.
- **Free database that doesn't expire** (for example Neon, https://neon.tech):
  create a database there, copy its connection string
  (`postgresql://...?sslmode=require`), then in Render open `criclive` →
  **Environment** → set `DATABASE_URL` to that string → **Save**. The app
  creates the tables itself. Old data is not copied over automatically.

## If something goes wrong

- Open `criclive` → **Logs** in Render to see errors.
- "Application failed to respond" right after opening: the service is waking
  up; wait a minute and reload.
- Changing `ADMIN_PASSWORD` later does not change the password of an account
  that already exists. Change passwords from the admin pages instead.
