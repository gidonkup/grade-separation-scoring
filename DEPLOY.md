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

## What was verified before pushing this branch

- Installed `backend/requirements.txt` into a brand-new virtual environment (not the one already
  set up on this machine) to catch anything that only worked here by accident.
- Ran `backend/scripts/build_reference_data.py` in that clean environment against the real source
  files - succeeded (905 traffic zones, 89,227 built-up polygons, 140,906 intersections).
- Started the server from that clean environment and ran a real scoring request and an Excel
  export through it - both returned correct results.

This doesn't guarantee Render's specific build environment behaves identically, but it rules out
"forgot to pin a dependency" or "only works because of stuff already installed on this laptop" as
failure causes.
