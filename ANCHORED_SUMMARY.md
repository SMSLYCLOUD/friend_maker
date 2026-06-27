# ANCHORED SUMMARY

## What we've done so far (entire conversation)

### Completed

1. **notary-sites script** — Created `notary_sites.mjs` for scraping notary sites via CloakBrowser, wired into `PLATFORM_SCRIPTS` in `app/main.py`, added to frontend campaigns page with FileText icon.

2. **Generalized VNC login for all social platforms** — Created `vnc_social.mjs` supporting Instagram, Twitter/X, Facebook, LinkedIn, TikTok, Substack, and Gmail with platform-specific login URLs + auth cookie detection. Runs as a persistent service on VPS (port 6100, VNC port 6082).

3. **API platform endpoints** — All platforms in `PlatformType` enum (instagram, twitter, facebook, linkedin, tiktok, substack, gmail). Backend endpoints:
   - `POST /api/accounts/{id}/vnc-login` — launches VNC browser for the account's platform
   - `GET /api/accounts/{id}/vnc-session-status` — checks if VNC detected a login
   - `POST /api/accounts/{id}/capture-cookies` — captures cookies from VNC session

4. **Docker volume mounts** — Added volumes for all `.mjs` scripts and `cookies/` directory in `docker-compose.yml`.

5. **CORS/DNS fix** — Updated `CORS_ALLOWED_ORIGINS` and `NEXT_PUBLIC_API_URL` to use `web.socialgrowthai.com` domain. Added `extra_hosts` for `host.docker.internal`.

6. **Frontend accounts page** — Generalized VNC login UI for ALL platforms (not just Gmail). Polls session status every 2s, auto-captures cookies on login detection. Updated API function names (`vncLogin`, `vncSessionStatus`, `captureCookies`).

7. **Deployment** — All files synced to VPS at `153.75.247.117`. Docker containers running. VNC service running under tmux session `vnc-social`. Successfully tested account creation + VNC endpoints for all 6 platforms.

8. **Platform switching fix** — VNC service now dynamically switches `platform`, `cfg`, and `accountId` on `/navigate` calls. Backend passes `account_id` param so cookies land in the right file. `capture-cookies` fallback tries `cookies/{account_id}_cookies.json` then `cookies/{platform}_cookies.json`.

9. **LLM provider fallback chain** — Completely rewired Skyvern's LLM through a LiteLLM proxy with multi-provider fallback:
   - **Primary**: Groq (meta-llama/llama-4-scout-17b-16e-instruct, free)
   - **Fallback 1**: Xiaomi MiMo V2.5 (direct, vision-capable, paid) via `token-plan-sgp.xiaomimimo.com/v1`
   - **Fallback 2**: OpenRouter (Google Gemini Flash, paid, vision)
   - **Fallback 3**: Google Gemini (free tier, vision)
   - **Fallback 4**: SambaNova (free tier, Llama-4-Maverick)
   - **Fallback 5**: NVIDIA NIM (free tier, Llama-4-Maverick)
   - Chain defined in `litellm_config.yaml:62` with 2 retries, 60s timeout, 30s cooldown, 2 allowed failures.

10. **Xiaomi MiMo integration** — Added provider to `litellm_config.yaml` as first fallback (xiaomi-fallback). Added editable env vars `SKYVERN_LLM_XIAOMI_MIMO_API_KEY`, `SKYVERN_LLM_XIAOMI_MIMO_MODEL`, `SKYVERN_LLM_XIAOMI_MIMO_BASE_URL`, `SKYVERN_LLM_XIAOMI_MIMO_RPM_LIMIT` in `app/main.py:656-659`. Added `XIAOMI_MIMO_API_KEY` environment variable mapping in `docker-compose.yml:18`. Updated frontend settings page with Xiaomi MiMo section and provider order. Committed and pushed to main and main-fixes.

11. **Editable env vars** — Whitelist `EDITABLE_ENV_VARS` in `app/main.py:628-660` now includes keys for all 6 providers (Groq, OpenRouter, Google, SambaNova, NVIDIA, Xiaomi MiMo). Backed by `POST /api/settings/env` and `GET /api/settings/env` endpoints that read/write `.env` file and restart affected containers.

12. **Provider rotate API** — `POST /api/providers/rotate` at `app/main.py:847-877` allows manually switching primary provider by setting `ENABLE_*` flags and restarting Skyvern container.

### In Progress

- Testing VNC login flow end-to-end across platforms
- Xiaomi MiMo API key not yet set in `.env` — needs a real key to activate the fallback

### Known issues / next

- `.env` still missing `SKYVERN_LLM_XIAOMI_MIMO_API_KEY` placeholder — needs to be added for the Xiaomi MiMo fallback to work
- Substack platform VNC may need refinement
- VNC service starts with gmail by default, switches platform dynamically on each `/navigate` call
