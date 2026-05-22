import { launch } from "cloakbrowser";
import { writeFileSync, readFileSync, existsSync, mkdirSync } from "fs";

const DATA_FILE = "data/rotary_contacts.json";
const BLOCKED = ["clubrunner.ca","clubrunnersupport.com","google.com","facebook.com",
  "twitter.com","youtube.com","linkedin.com","instagram.com","maps.google.com",
  "schema.org","w3.org","example.com","doubleclick.net","googletagmanager.com"];

// Rough US zip -> rotary district mapping (first 1-2 digits of zip map to district prefixes)
function filterDirsByZip(dirs, zip) {
  const prefix = zip.replace(/\D/g, "").slice(0, 3);
  if (!prefix) return dirs;
  // Map common zip prefixes to likely district URL patterns
  const zipDistricts = {
    "0": ["500","501","502","503","504","505","506","507","508","509"],
    "1": ["510","511","512","513","514","515","516","517","518","519"],
    "2": ["520","521","522","523","524","525","526","527","528","529"],
    "3": ["530","531","532","533","534","535","536","537","538","539"],
    "4": ["540","541","542","543","544","545","546","547","548","549"],
    "5": ["550","551","552","553","554","555","556","557","558","559"],
    "6": ["560","561","562","563","564","565","566","567","568","569"],
    "7": ["570","571","572","573","574","575","576","577","578","579"],
    "8": ["580","581","582","583","584","585","586","587","588","589"],
    "9": ["590","591","592","593","594","595","596","597","598","599"],
  };
  const firstDigit = prefix[0];
  const candidates = zipDistricts[firstDigit] || [];
  return dirs.filter(d => candidates.some(c => d.includes(c)));
}

function getFirstName(name) {
  return name ? name.split(" ")[0].replace(/[^a-zA-Z-]/g, "") : "";
}

async function scrapeDirectory(page, url) {
  console.log(JSON.stringify({ status: "scraping", url }));
  try {
    await page.goto(url, { timeout: 12000, waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2000);
  } catch (e) {
    return [];
  }

  const data = await page.evaluate(() => {
    const html = document.documentElement.outerHTML;
    const re = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
    const all = (html.match(re) || []).map(e => e.toLowerCase());
    const names = [];
    const trs = document.querySelectorAll("#ClubDirectory tbody tr");
    trs.forEach(tr => {
      if (!tr.querySelector(".clubName")?.textContent?.trim()) return;
      const presEl = tr.querySelector(".clubPresident .memberNameLink");
      if (presEl?.textContent?.trim()) names.push(presEl.textContent.trim());
    });
    return { emails: all, names };
  });

  const blocked = [...BLOCKED];
  const seen = new Set();
  const contacts = [];
  let nameIdx = 0;

  for (const email of data.emails) {
    if (seen.has(email)) continue;
    seen.add(email);
    if (email.includes("example") || email.includes(".png") || email.includes("jpg")) continue;
    if (!email.split("@")[1]) continue;
    if (blocked.some(d => email.endsWith(d))) continue;
    const name = data.names.length > 0 ? data.names[nameIdx % data.names.length] : "";
    contacts.push({ email, name, firstName: getFirstName(name), source: url, district: "" });
    nameIdx++;
  }

  console.log(JSON.stringify({ status: "progress", url: url.split("/")[2] || url, found: contacts.length, named: contacts.filter(c => c.name).length }));
  return contacts;
}

async function main() {
  const target = parseInt(process.argv[2] || "500");
  const zipCode = process.argv[3] || "";
  const businessType = process.argv[4] || "";
  const filterDesc = [zipCode && `zip:${zipCode}`, businessType && `type:${businessType}`].filter(Boolean).join(", ") || "none";
  console.log(JSON.stringify({ status: "starting", target, zipCode, businessType, filter: filterDesc }));
  const browser = await launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  let contacts = [];
  if (existsSync(DATA_FILE)) {
    try { contacts = JSON.parse(readFileSync(DATA_FILE, "utf-8")); } catch {}
  }
  const existing = new Set(contacts.map(c => c.email));
  console.log(JSON.stringify({ status: "starting", target, existing: existing.size }));
  const dir = DATA_FILE.split("/").slice(0, -1).join("/");
  if (dir && !existsSync(dir)) mkdirSync(dir, { recursive: true });

  console.log(JSON.stringify({ status: "filter", zipCode, businessType, filter: filterDesc }));

  // All directory URLs to try
  const allDirs = [
    "https://rotary5340.org/ClubDirectory",
    "https://district5190.org/clubdirectory",
    "https://rotary5160.org/ClubDirectory",
    "https://rotary5040.org/clubdirectory",
    "https://portal.clubrunner.ca/50008/ClubDirectory",
    "https://portal.clubrunner.ca/50012/ClubDirectory",
    "https://portal.clubrunner.ca/50045/ClubDirectory",
    "https://portal.clubrunner.ca/50050/ClubDirectory",
    "https://portal.clubrunner.ca/50083/ClubDirectory",
    "https://portal.clubrunner.ca/50084/ClubDirectory",
    "https://portal.clubrunner.ca/50086/ClubDirectory",
    "https://portal.clubrunner.ca/50087/ClubDirectory",
    "https://portal.clubrunner.ca/50088/ClubDirectory",
    "https://portal.clubrunner.ca/50089/ClubDirectory",
    "https://portal.clubrunner.ca/50090/ClubDirectory",
    "https://portal.clubrunner.ca/50091/ClubDirectory",
    "https://portal.clubrunner.ca/50092/ClubDirectory",
    "https://portal.clubrunner.ca/50093/ClubDirectory",
    "https://portal.clubrunner.ca/50094/ClubDirectory",
    "https://portal.clubrunner.ca/50095/ClubDirectory",
    "https://portal.clubrunner.ca/50096/ClubDirectory",
    "https://portal.clubrunner.ca/50097/ClubDirectory",
    "https://portal.clubrunner.ca/50098/ClubDirectory",
    "https://portal.clubrunner.ca/50099/ClubDirectory",
    "https://portal.clubrunner.ca/50100/ClubDirectory",
    "https://portal.clubrunner.ca/50101/ClubDirectory",
    "https://portal.clubrunner.ca/50102/ClubDirectory",
    "https://portal.clubrunner.ca/50103/ClubDirectory",
    "https://portal.clubrunner.ca/50104/ClubDirectory",
    "https://portal.clubrunner.ca/50105/ClubDirectory",
    "https://portal.clubrunner.ca/50106/ClubDirectory",
    "https://portal.clubrunner.ca/50107/ClubDirectory",
    "https://portal.clubrunner.ca/50108/ClubDirectory",
    "https://portal.clubrunner.ca/50109/ClubDirectory",
    "https://portal.clubrunner.ca/50110/ClubDirectory",
    "https://portal.clubrunner.ca/50111/ClubDirectory",
    "https://portal.clubrunner.ca/50112/ClubDirectory",
    "https://portal.clubrunner.ca/50113/ClubDirectory",
    "https://portal.clubrunner.ca/50114/ClubDirectory",
    "https://portal.clubrunner.ca/50115/ClubDirectory",
    "https://portal.clubrunner.ca/50116/ClubDirectory",
    "https://portal.clubrunner.ca/50117/ClubDirectory",
    "https://portal.clubrunner.ca/50118/ClubDirectory",
    "https://portal.clubrunner.ca/50119/ClubDirectory",
    "https://portal.clubrunner.ca/50120/ClubDirectory",
    "https://portal.clubrunner.ca/50121/ClubDirectory",
    "https://portal.clubrunner.ca/50122/ClubDirectory",
    "https://portal.clubrunner.ca/50123/ClubDirectory",
    "https://portal.clubrunner.ca/50124/ClubDirectory",
    "https://portal.clubrunner.ca/50125/ClubDirectory",
    "https://portal.clubrunner.ca/50126/ClubDirectory",
    "https://portal.clubrunner.ca/50127/ClubDirectory",
    "https://portal.clubrunner.ca/50128/ClubDirectory",
    "https://portal.clubrunner.ca/50129/ClubDirectory",
    "https://portal.clubrunner.ca/50130/ClubDirectory",
    "https://portal.clubrunner.ca/50131/ClubDirectory",
    "https://portal.clubrunner.ca/50132/ClubDirectory",
    "https://portal.clubrunner.ca/50133/ClubDirectory",
    "https://portal.clubrunner.ca/50134/ClubDirectory",
    "https://portal.clubrunner.ca/50135/ClubDirectory",
    "https://portal.clubrunner.ca/50136/ClubDirectory",
    "https://portal.clubrunner.ca/50137/ClubDirectory",
    "https://portal.clubrunner.ca/50138/ClubDirectory",
    "https://portal.clubrunner.ca/50139/ClubDirectory",
    "https://portal.clubrunner.ca/50140/ClubDirectory",
    "https://portal.clubrunner.ca/50141/ClubDirectory",
    "https://portal.clubrunner.ca/50142/ClubDirectory",
    "https://portal.clubrunner.ca/50143/ClubDirectory",
    "https://portal.clubrunner.ca/50144/ClubDirectory",
    "https://portal.clubrunner.ca/50145/ClubDirectory",
    "https://portal.clubrunner.ca/50146/ClubDirectory",
    "https://portal.clubrunner.ca/50147/ClubDirectory",
    "https://portal.clubrunner.ca/50148/ClubDirectory",
    "https://portal.clubrunner.ca/50149/ClubDirectory",
    "https://portal.clubrunner.ca/50150/ClubDirectory",
    "https://portal.clubrunner.ca/100455/ClubDirectory",
    "https://rotary6310.com/clubdirectory",
    "https://rotary6430.org/clubdirectory",
    "https://rotary5130.org/clubdirectory",
    "https://rotary5280.org/clubdirectory",
    "https://rotary5360.org/clubdirectory",
    "https://rotary5440.org/clubdirectory",
    "https://rotary5490.org/clubdirectory",
    "https://rotary5500.org/clubdirectory",
    "https://rotary5530.org/clubdirectory",
    "https://rotary5560.org/clubdirectory",
    "https://rotary5580.org/clubdirectory",
    "https://rotary5620.org/clubdirectory",
    "https://rotary5630.org/clubdirectory",
    "https://rotary5640.org/clubdirectory",
    "https://rotary5660.org/clubdirectory",
    "https://rotary5710.org/clubdirectory",
    "https://rotary5720.org/clubdirectory",
    "https://rotary5730.org/clubdirectory",
    "https://rotary5740.org/clubdirectory",
    "https://rotary5750.org/clubdirectory",
    "https://rotary5760.org/clubdirectory",
    "https://rotary5770.org/clubdirectory",
    "https://rotary5780.org/clubdirectory",
    "https://rotary5790.org/clubdirectory",
    "https://rotary5810.org/clubdirectory",
    "https://rotary5820.org/clubdirectory",
    "https://rotary5830.org/clubdirectory",
    "https://rotary5840.org/clubdirectory",
    "https://rotary5850.org/clubdirectory",
    "https://rotary5860.org/clubdirectory",
    "https://rotary5870.org/clubdirectory",
    "https://rotary5880.org/clubdirectory",
    "https://rotary5890.org/clubdirectory",
    "https://rotary5910.org/clubdirectory",
    "https://rotary5920.org/clubdirectory",
    "https://rotary5930.org/clubdirectory",
    "https://rotary5940.org/clubdirectory",
    "https://rotary5950.org/clubdirectory",
    "https://rotary5960.org/clubdirectory",
    "https://rotary5970.org/clubdirectory",
    "https://rotary5980.org/clubdirectory",
    "https://rotary5990.org/clubdirectory",
    "https://rotary6110.org/clubdirectory",
    "https://rotary6120.org/clubdirectory",
    "https://rotary6130.org/clubdirectory",
    "https://rotary6140.org/clubdirectory",
    "https://rotary6150.org/clubdirectory",
    "https://rotary6160.org/clubdirectory",
    "https://rotary6170.org/clubdirectory",
    "https://rotary6180.org/clubdirectory",
    "https://rotary6190.org/clubdirectory",
    "https://rotary6200.org/clubdirectory",
    "https://rotary6210.org/clubdirectory",
    "https://rotary6220.org/clubdirectory",
    "https://rotary6230.org/clubdirectory",
    "https://rotary6240.org/clubdirectory",
    "https://rotary6250.org/clubdirectory",
    "https://rotary6260.org/clubdirectory",
    "https://rotary6270.org/clubdirectory",
    "https://rotary6280.org/clubdirectory",
    "https://rotary6290.org/clubdirectory",
    "https://rotary6300.org/clubdirectory",
    "https://rotary6320.org/clubdirectory",
    "https://rotary6330.org/clubdirectory",
    "https://rotary6340.org/clubdirectory",
    "https://rotary6350.org/clubdirectory",
    "https://rotary6360.org/clubdirectory",
    "https://rotary6370.org/clubdirectory",
    "https://rotary6380.org/clubdirectory",
    "https://rotary6390.org/clubdirectory",
    "https://rotary6400.org/clubdirectory",
    "https://rotary6410.org/clubdirectory",
    "https://rotary6420.org/clubdirectory",
    "https://rotary6440.org/clubdirectory",
    "https://rotary6450.org/clubdirectory",
    "https://rotary6460.org/clubdirectory",
    "https://rotary6470.org/clubdirectory",
    "https://rotary6480.org/clubdirectory",
    "https://rotary6490.org/clubdirectory",
    "https://rotary6500.org/clubdirectory",
    "https://rotary6510.org/clubdirectory",
    "https://rotary6520.org/clubdirectory",
    "https://rotary6530.org/clubdirectory",
    "https://rotary6540.org/clubdirectory",
    "https://rotary6550.org/clubdirectory",
    "https://rotary6560.org/clubdirectory",
    "https://rotary6570.org/clubdirectory",
    "https://rotary6580.org/clubdirectory",
    "https://rotary6590.org/clubdirectory",
    "https://rotary6600.org/clubdirectory",
    "https://rotary6610.org/clubdirectory",
    "https://rotary6620.org/clubdirectory",
    "https://rotary6630.org/clubdirectory",
    "https://rotary6640.org/clubdirectory",
    "https://rotary6650.org/clubdirectory",
    "https://rotary6660.org/clubdirectory",
    "https://rotary6670.org/clubdirectory",
    "https://rotary6680.org/clubdirectory",
    "https://rotary6690.org/clubdirectory",
    "https://rotary6700.org/clubdirectory",
    "https://rotary6710.org/clubdirectory",
    "https://rotary6720.org/clubdirectory",
    "https://rotary6730.org/clubdirectory",
    "https://rotary6740.org/clubdirectory",
    "https://rotary6750.org/clubdirectory",
    "https://rotary6760.org/clubdirectory",
    "https://rotary6770.org/clubdirectory",
    "https://rotary6780.org/clubdirectory",
    "https://rotary6790.org/clubdirectory",
    "https://rotary6800.org/clubdirectory",
    "https://rotary6810.org/clubdirectory",
    "https://rotary6820.org/clubdirectory",
    "https://rotary6830.org/clubdirectory",
    "https://rotary6840.org/clubdirectory",
    "https://rotary6850.org/clubdirectory",
    "https://rotary6860.org/clubdirectory",
    "https://rotary6870.org/clubdirectory",
    "https://rotary6880.org/clubdirectory",
    "https://rotary6890.org/clubdirectory",
    "https://rotary6900.org/clubdirectory",
    "https://rotary6910.org/clubdirectory",
    "https://rotary6920.org/clubdirectory",
    "https://rotary6930.org/clubdirectory",
    "https://rotary6940.org/clubdirectory",
    "https://rotary6950.org/clubdirectory",
    "https://rotary6960.org/clubdirectory",
    "https://rotary6970.org/clubdirectory",
    "https://rotary6980.org/clubdirectory",
    "https://rotary6990.org/clubdirectory",
  ];

  // Filter by zip code if provided
  const dirsToScrape = zipCode ? filterDirsByZip(allDirs, zipCode) : allDirs;
  console.log(JSON.stringify({ status: "dirs_filtered", total: allDirs.length, filtered: dirsToScrape.length, zipCode }));

  for (const url of dirsToScrape) {
    if (existing.size >= target) break;
    const newContacts = await scrapeDirectory(page, url);
    for (const c of newContacts) {
      if (!existing.has(c.email)) {
        contacts.push({ ...c, zipCode, businessType, scraped_at: new Date().toISOString() });
        existing.add(c.email);
      }
    }
    writeFileSync(DATA_FILE, JSON.stringify(contacts, null, 2));
  }

  const withNames = contacts.filter(c => c.name).length;
  console.log(JSON.stringify({ status: "complete", total: existing.size, withNames }));
  await browser.close();
}

main();
