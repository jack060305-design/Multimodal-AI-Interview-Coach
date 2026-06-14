#!/usr/bin/env node
/** Validate Supabase auth env before dev/build. */
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const envPath = resolve(root, ".env.local");
const prodPath = resolve(root, ".env.production");

function loadEnvFile(path) {
  if (!existsSync(path)) return {};
  const out = {};
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i === -1) continue;
    out[t.slice(0, i).trim()] = t.slice(i + 1).trim();
  }
  return out;
}

const env = { ...loadEnvFile(prodPath), ...loadEnvFile(envPath), ...process.env };
const required = ["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"];
const missing = required.filter((k) => !env[k] && !env[k.replace("PUBLISHABLE", "ANON")]);

console.log("Interview Coach — auth env check\n");

if (missing.length) {
  console.error("Missing:", missing.join(", "));
  console.error("Copy frontend/.env.local.example → .env.local and fill values.");
  process.exit(1);
}

console.log("OK  Supabase URL:", env.NEXT_PUBLIC_SUPABASE_URL);
console.log("OK  Publishable key:", (env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "").slice(0, 24) + "…");
console.log("    Google OAuth:", env.NEXT_PUBLIC_OAUTH_GOOGLE_ENABLED === "true" ? "enabled" : "disabled (email-only)");
console.log("    Facebook OAuth:", env.NEXT_PUBLIC_OAUTH_FACEBOOK_ENABLED === "true" ? "enabled" : "disabled (email-only)");
console.log("    Site URL:", env.NEXT_PUBLIC_SITE_URL || "(default localhost:3000)");
console.log("    API URL:", env.NEXT_PUBLIC_API_URL || "(not set)");
