import playwright from "file:///C:/Users/human-21/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.js";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const dir = "C:/Users/human-21/Documents/Final Project/docs/assets/troubleshooting-code";
const browser = await playwright.chromium.launch({
  headless: true,
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
});
const page = await browser.newPage({ viewport: { width: 1600, height: 600 }, deviceScaleFactor: 1 });

for (const name of fs.readdirSync(dir).filter((name) => name.endsWith(".html"))) {
  await page.goto(pathToFileURL(path.join(dir, name)).href);
  await page.screenshot({
    path: path.join(dir, name.replace(/\.html$/, ".png")),
    fullPage: true,
  });
}

await browser.close();
