#!/usr/bin/env node

const { spawn, spawnSync } = require("child_process");
const path = require("path");

// Function to detect the best Python command to use
function detectPythonCommand() {
  // Try different Python commands in order of preference
  const pythonCommands = ["python3.11", "python3", "python"];

  for (const cmd of pythonCommands) {
    try {
      const result = spawnSync(cmd, ["--version"], { stdio: "pipe" });
      if (result.status === 0) {
        console.log(`🐍 Found Python: ${cmd}`);
        return cmd;
      }
    } catch (error) {
      // Command not found, continue to next
    }
  }

  // Fallback to python if nothing else works
  console.log("🐍 Falling back to: python");
  return "python";
}

// Check if uv is available
function hasUv() {
  try {
    const result = spawnSync("uv", ["--version"], { stdio: "pipe" });
    return result.status === 0;
  } catch (error) {
    return false;
  }
}

// Check for USE_UV environment variable - disabled by default for Replit compatibility
const forceUv = process.env.USE_UV === "1";
const disableUv =
  process.env.DISABLE_UV === "1" ||
  process.env.REPLIT_ENVIRONMENT === "1" ||
  true; // Disable uv by default in Replit environment

async function startBackend() {
  const useUv = forceUv && !disableUv && hasUv();
  const pythonCmd = detectPythonCommand();

  // Set environment variables to prevent Unicode encoding issues
  process.env.PYTHONIOENCODING = "utf-8";
  process.env.LC_ALL = "C.UTF-8";
  process.env.LANG = "C.UTF-8";

  // Generate secure keys for development if not set
  if (!process.env.JWT_SECRET) {
    process.env.JWT_SECRET = require("crypto").randomBytes(32).toString("hex");
    console.log("🔐 Generated temporary JWT_SECRET for development");
  }
  if (!process.env.ADMIN_SECRET_KEY) {
    process.env.ADMIN_SECRET_KEY = require("crypto")
      .randomBytes(32)
      .toString("hex");
    console.log("🔐 Generated temporary ADMIN_SECRET_KEY for development");
  }
  
  // ⚠️  DEVELOPMENT MODE: Enable email verification bypass for faster testing
  // This auto-verifies new user registrations without requiring email confirmation
  if (!process.env.DEV_BYPASS_EMAIL_VERIFICATION) {
    process.env.DEV_BYPASS_EMAIL_VERIFICATION = "true";
    console.log("⚠️  DEV MODE: Email verification bypass enabled");
  }

  console.log(
    `🐍 Using ${useUv ? "uv" : "pip"} for Python dependency management`
  );

  if (useUv) {
    console.log("📦 Syncing dependencies with uv...");
    const syncResult = spawnSync("uv", ["sync"], {
      stdio: "inherit",
      cwd: process.cwd(),
    });

    if (syncResult.status !== 0) {
      console.error("❌ uv sync failed");
      process.exit(1);
    }

    console.log("🚀 Starting backend with uv...");
    const backend = spawn(
      "uv",
      [
        "run",
        "uvicorn",
        "api.main:app",
        "--host",
        "localhost",
        "--port",
        "8000",
        "--reload",
        "--reload-dir",
        "api",
      ],
      {
        stdio: "inherit",
        cwd: process.cwd(),
      }
    );

    backend.on("exit", (code) => {
      process.exit(code);
    });
  } else {
    console.log("📦 Installing dependencies with pip...");
    const installResult = spawnSync(
      pythonCmd,
      [
        "-m",
        "pip",
        "install",
        "--break-system-packages",
        "-r",
        "requirements.txt",
      ],
      {
        stdio: "inherit",
        cwd: process.cwd(),
      }
    );

    if (installResult.status !== 0) {
      console.error("❌ pip install failed");
      process.exit(1);
    }

    console.log("📦 Installing additional packages...");
    const additionalResult = spawnSync(
      pythonCmd,
      [
        "-m",
        "pip",
        "install",
        "--break-system-packages",
        "duckdb",
        "fsspec",
        "pyarrow",
        "pandas",
        "numpy",
      ],
      {
        stdio: "inherit",
        cwd: process.cwd(),
      }
    );

    if (additionalResult.status !== 0) {
      console.error("❌ Additional packages install failed");
      process.exit(1);
    }

    console.log(`🚀 Starting backend with ${pythonCmd} -m uvicorn...`);
    const backend = spawn(
      pythonCmd,
      [
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "localhost",
        "--port",
        "8000",
        "--reload",
        "--reload-dir",
        "api",
      ],
      {
        stdio: "inherit",
        cwd: process.cwd(),
      }
    );

    backend.on("exit", (code) => {
      process.exit(code);
    });
  }
}

startBackend().catch((error) => {
  console.error("❌ Failed to start backend:", error);
  process.exit(1);
});
