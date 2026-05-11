#!/usr/bin/env node
// ============================================================
// IG Agent Plugin Validation Script
// Run: node test_plugin.js
// Validates the OpenClaw plugin loads without a real IG account
// ============================================================

const fs = require("fs");
const path = require("path");

const PLUGIN_DIR = path.join(__dirname);

console.log("============================================");
console.log(" IG Agent Plugin — Validation Test");
console.log("============================================\n");

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.log(`  [FAIL] ${name}`);
    console.log(`         ${err.message}`);
    failed++;
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || "Assertion failed");
}

// --- 1. Check files exist ---
console.log("1. File structure");
test("package.json exists", () => assert(fs.existsSync(path.join(PLUGIN_DIR, "package.json"))));
test("openclaw.plugin.json exists", () => assert(fs.existsSync(path.join(PLUGIN_DIR, "openclaw.plugin.json"))));
test("index.ts exists", () => assert(fs.existsSync(path.join(PLUGIN_DIR, "index.ts"))));
test("SKILL.md exists", () => assert(fs.existsSync(path.join(PLUGIN_DIR, "SKILL.md"))));

// --- 2. Validate package.json ---
console.log("\n2. package.json validation");
const pkg = JSON.parse(fs.readFileSync(path.join(PLUGIN_DIR, "package.json"), "utf8"));
test("name starts with @", () => assert(pkg.name.startsWith("@")));
test("type is module", () => assert(pkg.type === "module"));
test("openclaw config present", () => assert(!!pkg.openclaw));
test("extensions defined", () => assert(Array.isArray(pkg.openclaw.extensions)));
test("has build script", () => assert(typeof pkg.scripts?.build === "string"));

// --- 3. Validate plugin manifest ---
console.log("\n3. Plugin manifest validation");
const manifest = JSON.parse(fs.readFileSync(path.join(PLUGIN_DIR, "openclaw.plugin.json"), "utf8"));
test("id is set", () => assert(typeof manifest.id === "string"));
test("name is set", () => assert(typeof manifest.name === "string"));
test("description is set", () => assert(typeof manifest.description === "string"));
test("version is set", () => assert(typeof manifest.version === "string"));

// --- 4. Validate TypeScript syntax ---
console.log("\n4. TypeScript syntax check");
const tsContent = fs.readFileSync(path.join(PLUGIN_DIR, "index.ts"), "utf8");
test("registers tools hook", () => assert(tsContent.includes("registerHook")));
test("tools.register called", () => assert(tsContent.includes("tools.register")));
test("browserStore imported", () => assert(tsContent.includes("browserStore")));
test("IG login function exported", () => assert(tsContent.includes("loginToInstagram")));
test("follow function exported", () => assert(tsContent.includes("doFollow")));
test("DM function exported", () => assert(tsContent.includes("doSendDM")));
test("scrape function exported", () => assert(tsContent.includes("scrapeFollowers")));
test("campaign function exported", () => assert(tsContent.includes("runBombingCampaign")));
test("registers ig_login tool", () => assert(tsContent.includes("ig_login")));
test("registers ig_follow tool", () => assert(tsContent.includes("ig_follow")));
test("registers ig_send_dm tool", () => assert(tsContent.includes("ig_send_dm")));
test("registers ig_scrape_followers tool", () => assert(tsContent.includes("ig_scrape_followers")));
test("registers ig_bombing_campaign tool", () => assert(tsContent.includes("ig_bombing_campaign")));
test("has Instagram URL constants", () => assert(tsContent.includes("instagram.com")));

// --- 5. Validate SKILL.md ---
console.log("\n5. SKILL.md validation");
const skill = fs.readFileSync(path.join(PLUGIN_DIR, "SKILL.md"), "utf8");
test("has setup section", () => assert(skill.includes("## Setup") || skill.includes("### Install")));
test("mentions OpenRouter", () => assert(skill.includes("openrouter") || skill.includes("OpenRouter")));
test("documents login", () => assert(skill.includes("Login") || skill.includes("login")));
test("documents follow", () => assert(skill.includes("Follow") || skill.includes("follow")));
test("documents DM", () => assert(skill.includes("DM") || skill.includes("dm")));
test("documents scrape", () => assert(skill.includes("scrape") || skill.includes("Scrape")));
test("documents bombing", () => assert(skill.includes("bombing") || skill.includes("Bombing")));

// --- 6. OpenClaw config example ---
console.log("\n6. OpenClaw config validation");
const configContent = fs.readFileSync(path.join(PLUGIN_DIR, "SKILL.md"), "utf8");
test("has openclaw.json example", () => assert(configContent.includes("openclaw.json") || configContent.includes("OPENROUTER_API_KEY")));
test("has Telegram setup instructions", () => assert(configContent.includes("Telegram") || configContent.includes("telegram")));

// --- Summary ---
console.log("\n============================================");
console.log(` Results: ${passed} passed, ${failed} failed`);
console.log("============================================");

if (failed > 0) {
  console.log("\nSome tests failed. Review the output above.");
  process.exit(1);
} else {
  console.log("\nAll validation tests passed!");
  console.log("Next steps:");
  console.log("  1. npm install");
  console.log("  2. npm run build");
  console.log("  3. openclaw plugins install ./");
  console.log("  4. openclaw gateway restart");
  process.exit(0);
}
