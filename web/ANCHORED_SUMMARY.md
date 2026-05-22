# ANCHORED SUMMARY

## What we've done so far (entire conversation)

### Completed

1. **notary-sites script** — Created `notary_sites.mjs` for scraping notary sites via CloakBrowser, wired into `PLATFORM_SCRIPTS` in `app/main.py`, added to frontend campaigns page with FileText icon.

2. **Generalized VNC login for all social platforms** — Created `vnc_social.mjs` supporting Instagram, Twitter/X, Facebook, LinkedIn, TikTok, Substack, and Gmail with platform-specific login URLs + auth cookie detection. Runs as a persistent service on VPS (port 6100, VNC port 6082).

3. **API platform endpoints** — All platforms in `PlatformType` enum (instagram, twitter, facebook, linkedin, tiktok, substack, gmail, android). Backend endpoints:
   - `POST /api/accounts/{id}/vnc-login` — launches VNC browser for the account's platform
   - `GET /api/accounts/{id}/vnc-session-status` — checks if VNC detected a login
   - `POST /api/accounts/{id}/capture-cookies` — captures cookies from VNC session

4. **Docker volume mounts** — Added volumes for all `.mjs` scripts and `cookies/` directory in `docker-compose.yml`.

5. **CORS/DNS fix** — Updated `CORS_ALLOWED_ORIGINS` and `NEXT_PUBLIC_API_URL` to use `web.socialgrowthai.com` domain. Added `extra_hosts` for `host.docker.internal`.

6. **Frontend accounts page** — Generalized VNC login UI for ALL platforms (not just Gmail). Polls session status every 2s, auto-captures cookies on login detection. Updated API function names (`vncLogin`, `vncSessionStatus`, `captureCookies`).

7. **Deployment** — All files synced to VPS at `153.75.247.117`. Docker containers running. VNC service running under tmux session `vnc-social`. Successfully tested account creation + VNC endpoints for all 6 platforms.

8. **Platform switching fix** — VNC service now dynamically switches `platform`, `cfg`, and `accountId` on `/navigate` calls. Backend passes `account_id` param so cookies land in the right file. `capture-cookies` fallback tries `cookies/{account_id}_cookies.json` then `cookies/{platform}_cookies.json`.

### In Progress

- Testing VNC login flow end-to-end across platforms (user is testing today)

### Known issues / next
- Android platform has no script yet
- Substack platform VNC may need refinement
- VNC service starts with gmail by default, switches platform dynamically on each `/navigate` call
