# IG Agent — Instagram Automation Skill for OpenClaw

> Automates all Instagram actions through natural language. Built for social growth campaigns.

## What it does

This skill gives OpenClaw full Instagram automation capabilities:

- **Login** with credentials or session cookies
- **Follow / Unfollow** any public or mutual account
- **Send DMs** to individual users
- **Scrape followers** from any account (for audience building)
- **Run bombing campaigns** — mass follow or mass DM across a target list

## Setup

### 1. Install the plugin

```bash
openclaw plugins install @friendmaker/openclaw-ig-agent
openclaw gateway restart
```

### 2. Configure OpenRouter (optional)

This skill works best with a strong reasoning model. Add to your `~/.openclaw/openclaw.json`:

```json
{
  "env": {
    "OPENROUTER_API_KEY": "sk-or-v1-..."
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/google/gemini-2.5-flash-preview-05-20"
      }
    }
  }
}
```

### 3. Connect via Telegram (recommended)

Set up Telegram to control campaigns from your phone:

```bash
openclaw channels install telegram
# Follow the botFather setup, get your API token, then:
openclaw channels config telegram --token YOUR_BOT_TOKEN
openclaw gateway restart
```

## Usage

Start a conversation with OpenClaw (via Telegram, Discord, or the Control UI) and use natural language:

```
Login to Instagram as @mybot with password SuperSecret123
```

```
Scrape 200 followers from @techinfluencer
```

```
Run a bombing campaign on these targets: @user1, @user2, @user3
using mass follow, count 30
```

```
Send a DM to @potential_client saying: Hey! Saw your posts on AI agents,
would love to connect. Check out friendmaker.ai
```

```
Run mass follow campaign targeting followers of @targetaccount, count 50
```

## How it works

The skill uses OpenClaw's built-in Playwright/CDP browser with stealth settings.
Each action includes human-like delays (3-7 seconds) to avoid detection.
The browser runs headless on your VPS — no emulator needed.

## Safety

- Rate limit actions: max ~20 follows/DMs per hour per account
- Use session cookies for faster login (avoids repeated 2FA triggers)
- Run campaigns overnight or during off-peak hours
- Always have 2FA enabled on your IG account

## Troubleshooting

**"No browser available"** — Run `ig_login` first to establish a session.

**Login fails** — Instagram may require email/phone verification. Use session cookies after first successful login.

**Actions silently fail** — Instagram updates its UI regularly. The plugin uses multiple selector fallbacks but may need updates after IG changes.

## Campaign Examples

### Warm outreach campaign
```
Scrape followers from @target_niche_account count 200
Then send DMs to the first 30: "Hey! Love your content on [niche].
We're building something in that space — happy to connect?"
```

### Follow-for-follow campaign
```
Login to @my_bot_account
Scrape followers from @similar_account count 100
Run mass follow campaign targeting those users, count 50
```

### Competitor audience mining
```
Scrape 500 followers from @competitor
Run mass follow campaign on those followers, count 200
Wait 3 days
Run mass unfollow targeting anyone who didn't follow back
```
