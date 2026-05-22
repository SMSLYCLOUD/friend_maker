import { readFileSync, writeFileSync, existsSync } from "fs";

const CA_SOURCES = [
  "rotary5040.org", "rotary5130.org", "rotary5160.org",
  "rotary5170.org", "rotary5190.org", "district5190.org",
  "rotary5220.org", "rotary5300.org", "rotary5320.org",
  "rotary5330.org", "rotary5340.org", "rotary5360.org",
];

const contacts = JSON.parse(readFileSync("data/rotary_contacts.json", "utf8"));
const before = contacts.length;
const kept = contacts.filter(c => CA_SOURCES.some(s => (c.source || "").includes(s)));
const after = kept.length;
writeFileSync("data/rotary_contacts.json", JSON.stringify(kept, null, 2));
console.log(`Purged ${before - after} non-CA contacts. Kept ${after}`);

// Rebuild campaign with only CA contacts
const campaignEmails = new Set(kept.map(c => c.email.toLowerCase()));
if (existsSync("data/campaign.json")) {
  const campaign = JSON.parse(readFileSync("data/campaign.json", "utf8"));
  const beforeC = campaign.contacts.length;
  campaign.contacts = campaign.contacts.filter(ct => campaignEmails.has(ct.email));
  writeFileSync("data/campaign.json", JSON.stringify(campaign, null, 2));
  console.log(`Campaign: ${beforeC} -> ${campaign.contacts.length} contacts`);
}

// Clean sent_emails.json too
if (existsSync("data/sent_emails.json")) {
  const sent = JSON.parse(readFileSync("data/sent_emails.json", "utf8"));
  const beforeS = sent.length;
  const keptSent = Array.isArray(sent) ? sent.filter(s => campaignEmails.has((s.to || s.email || "").toLowerCase())) : sent;
  writeFileSync("data/sent_emails.json", JSON.stringify(keptSent, null, 2));
  console.log(`Sent emails: purged ${beforeS - (Array.isArray(keptSent) ? keptSent.length : 0)} non-CA entries`);
}

console.log("Done");
