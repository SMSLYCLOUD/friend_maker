---
name: ig-agent
description: Instagram automation tool that can login, follow, unfollow, send DMs, and scrape followers. Runs as a node.js script via the exec tool.
metadata:
  {
    "openclaw": {
      "emoji": "📸",
      "requires": { "exec": true }
    }
  }
---

# Instagram Automation (ig.mjs)

Automates Instagram through the `ig.mjs` Node.js script. Run these commands with the `exec` tool and parse JSON output.

## Login
```
node /root/friend_maker/web/ig.mjs login <username> <password>
```
Returns `{"success": true}` on success.

## Follow a user
```
node /root/friend_maker/web/ig.mjs follow <target_username>
```

## Unfollow a user
```
node /root/friend_maker/web/ig.mjs unfollow <target_username>
```

## Send DM
```
node /root/friend_maker/web/ig.mjs dm <target_username> <message>
```

## Search
Not available for Instagram.
