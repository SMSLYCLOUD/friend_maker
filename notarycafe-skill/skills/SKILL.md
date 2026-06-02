---
name: notarycafe-agent
description: NotaryCafe.com automation for searching notaries, viewing profiles, login, and sending messages. Runs as a node.js script via the exec tool.
metadata:
  {
    "openclaw": {
      "emoji": "📋",
      "requires": { "exec": true }
    }
  }
---

# NotaryCafe Automation (nc.mjs)

Automates NotaryCafe.com through the `nc.mjs` Node.js script. Run these commands with the `exec` tool and parse JSON output.

## Search Notaries
```
node /root/friend_maker/web/nc.mjs search <zip_or_city>
```
Returns JSON array of notaries with names, locations, phones.

## View Profile
```
node /root/friend_maker/web/nc.mjs profile <profile_url>
```

## Login
```
node /root/friend_maker/web/nc.mjs login <email> <password>
```

## Send Message
```
node /root/friend_maker/web/nc.mjs message <profile_url> <message_text>
```

## Create Account
```
node /root/friend_maker/web/nc.mjs register <full_name> <email> <password>
```
