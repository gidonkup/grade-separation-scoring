# Deploying as a public web page

This branch (`web-hosting-trial`) adds everything needed to run the tool as a real hosted web
page instead of a local server — a `Dockerfile` that installs dependencies, rebuilds the
reference-layer data from `data_sources/raw/` at build time, and starts the app, plus a
`render.yaml` blueprint for [Render](https://render.com)'s free web-service tier.

I can't create a hosting account on your behalf — that's the one step only you can do. Everything
else (the container, the config, verifying it actually builds and runs) is already done and
tested locally in a clean environment matching what the host will run.

## One-click deploy (Render, free tier)

1. Click: **https://render.com/deploy?repo=https://github.com/gidonkup/grade-separation-scoring/tree/web-hosting-trial**
2. Sign up / log in (GitHub login works, no credit card needed for the free tier).
3. Render reads `render.yaml` automatically and offers to create the web service - confirm.
4. First build takes a few minutes (installs dependencies + rebuilds the GIS reference layers).
   After that you'll get a public URL like `https://grade-separation-scoring.onrender.com`.

**Free-tier note:** the service spins down after 15 minutes of no traffic and takes ~30-60
seconds to wake back up on the next visit (cold start) - normal for a free instance, not a bug.

## Restricting access to your team

The repo (and therefore the deployed site) is public, so by default anyone with the URL can open
it. The app supports a simple shared username/password gate via HTTP Basic Auth (the browser's
native login popup - no custom login page, no user database) - it activates automatically as soon
as two environment variables are set on the host, and stays off otherwise (e.g. when you run it
locally).

**If you're deploying for the first time:** the blueprint (`render.yaml`) already declares
`AUTH_USERNAME` and `AUTH_PASSWORD` as required secrets - Render will prompt you to fill in values
for both during the one-click deploy in step 3 above. Pick any username/password you want and
share them with your team through whatever channel you'd normally share a password.

**If the service is already deployed:** go to the Render dashboard → your service → **Environment**
→ add `AUTH_USERNAME` and `AUTH_PASSWORD` with whatever values you want → save. Render redeploys
automatically and the site starts asking for that login within a minute or two.

To change the password later, or remove the gate entirely (delete both variables), same place.
Everyone on the team uses the same shared username/password - there's no per-person account system,
by design, since the ask was to keep this simple.

## What was verified before pushing this branch

- Installed `backend/requirements.txt` into a brand-new virtual environment (not the one already
  set up on this machine) to catch anything that only worked here by accident.
- Ran `backend/scripts/build_reference_data.py` in that clean environment against the real source
  files - succeeded (905 traffic zones, 89,227 built-up polygons, 140,906 intersections).
- Started the server from that clean environment and ran a real scoring request and an Excel
  export through it - both returned correct results.
- Tested the Basic Auth gate directly: with no credentials set the app stays fully open (matches
  local-dev behavior); with credentials set, `/healthz` stays reachable (so Render's own health
  check doesn't mistake the service for down), every other route returns 401 without a login,
  returns 401 for a wrong password, and returns 200 for the correct one.

This doesn't guarantee Render's specific build environment behaves identically, but it rules out
"forgot to pin a dependency" or "only works because of stuff already installed on this laptop" as
failure causes.
