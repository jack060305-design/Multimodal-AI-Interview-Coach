#!/usr/bin/env node
/** Report Firebase + Supabase dual-auth env status (read-only). */
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(root, "..");

function loadEnvFile(path) {
  if (!existsSync(path)) return null;
  const out = {};
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i === -1) continue;
    const key = t.slice(0, i).trim();
    const val = t.slice(i + 1).trim();
    if (val) out[key] = val;
  }
  return out;
}

function mask(val) {
  if (!val) return "(missing)";
  if (val.length <= 8) return val;
  return `${val.slice(0, 6)}…${val.slice(-4)}`;
}

const frontendLocal = loadEnvFile(resolve(root, ".env.local")) || {};
const frontendProd = loadEnvFile(resolve(root, ".env.production")) || {};
const backendEnv = loadEnvFile(resolve(repo, "backend", ".env")) || {};

const firebaseKeys = [
  "NEXT_PUBLIC_FIREBASE_API_KEY",
  "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
  "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
  "NEXT_PUBLIC_FIREBASE_APP_ID",
];

console.log("=== Firebase project check ===\n");

let allFrontend = true;
for (const key of firebaseKeys) {
  const local = frontendLocal[key];
  const prod = frontendProd[key];
  const ok = Boolean(local);
  if (!ok) allFrontend = false;
  console.log(`${ok ? "OK " : "MISS"}  ${key}`);
  console.log(`      .env.local:      ${local ? mask(local) : "(not set)"}`);
  console.log(`      .env.production: ${prod ? mask(prod) : "(not set)"}`);
}

const backendProject =
  backendEnv.FIREBASE_PROJECT_ID || backendEnv.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
const frontendProject = frontendLocal.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
console.log("");
console.log(`${backendProject ? "OK " : "MISS"}  backend/.env FIREBASE_PROJECT_ID: ${backendProject || "(not set)"}`);

if (frontendProject && backendProject && frontendProject !== backendProject) {
  console.log("WARN  Frontend and backend Firebase project IDs do not match!");
}

const googleClientId = frontendLocal.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
if (googleClientId) {
  const m = googleClientId.match(/^(\d+)-/);
  console.log("");
  console.log("Note: NEXT_PUBLIC_GOOGLE_CLIENT_ID is set (Supabase GIS flow, not Firebase SDK).");
  if (m) {
    console.log(`      Google Cloud project number: ${m[1]}`);
    console.log("      Firebase often uses the same Google Cloud project — check:");
    console.log(`      https://console.firebase.google.com/project/_/overview`);
  }
}

console.log("");
if (allFrontend && backendProject) {
  console.log("Status: Firebase dual-auth READY — restart setup.cmd and test /login");
  if (frontendProject) {
    console.log(`Console: https://console.firebase.google.com/project/${frontendProject}/authentication/providers`);
  }
} else {
  console.log("Status: Firebase NOT configured yet.");
  console.log("");
  console.log("Next steps:");
  console.log("  1. https://console.firebase.google.com → create/select project");
  console.log("  2. Project settings → Your apps → Web app → copy firebaseConfig");
  console.log("  3. Authentication → Sign-in method → Google → Enable");
  console.log("  4. Add vars to frontend/.env.local + backend/.env (FIREBASE_PROJECT_ID)");
  console.log("  5. Run: npm run setup:firebase  (from frontend/)");
  process.exit(1);
}
