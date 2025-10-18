const express  = require("express");
const path     = require("path");
const fs       = require("fs");
const chokidar = require("chokidar");
const { WebSocketServer } = require("ws");
const http     = require("http");

const app  = express();
const PORT = 3000;

const DATA_FILE      = path.join(__dirname, "dashboard_data.json");
const EVIDENCE_DIR   = path.join(__dirname, "static", "evidence");

// ── Ensure evidence folder exists ──────────────────────────
fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

// ── Static files (CSS, evidence images) ───────────────────
app.use("/static",   express.static(path.join(__dirname, "static")));
app.use("/evidence", express.static(EVIDENCE_DIR));

// ── Serve dashboard HTML ───────────────────────────────────
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "dashboard.html"));
});

// ── REST endpoint (fallback polling) ──────────────────────
app.get("/api/data", (req, res) => {
  try {
    const raw  = fs.readFileSync(DATA_FILE, "utf8");
    const data = JSON.parse(raw);
    data.evidence_images = getEvidenceImages();
    res.json(data);
  } catch {
    res.json(getDefaultData());
  }
});

// ── Evidence image list ────────────────────────────────────
function getEvidenceImages() {
  try {
    const exts = [".jpg", ".jpeg", ".png", ".webp"];
    return fs.readdirSync(EVIDENCE_DIR)
      .filter(f => exts.includes(path.extname(f).toLowerCase()))
      .sort()
      .reverse()
      .slice(0, 20);
  } catch { return []; }
}

function getDefaultData() {
  return {
    person: "—", vegetable: "—", platform: "—",
    counts: { person_clean:0, person_unhygienic:0, veg_fresh:0, veg_rotten:0, platform_clean:0, platform_unclean:0 },
    alerts: [],
    last_updated: new Date().toLocaleString(),
    evidence_images: []
  };
}

// ── HTTP + WebSocket server ────────────────────────────────
const server = http.createServer(app);
const wss    = new WebSocketServer({ server });

function broadcast(data) {
  const msg = JSON.stringify(data);
  wss.clients.forEach(client => {
    if (client.readyState === 1) client.send(msg);
  });
}

// ── Watch dashboard_data.json for changes ─────────────────
// Pushes updates to ALL connected browsers INSTANTLY via WebSocket
chokidar.watch(DATA_FILE, { usePolling: true, interval: 500 })
  .on("change", () => {
    try {
      const data = JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
      data.evidence_images = getEvidenceImages();
      broadcast({ type: "update", payload: data });
      console.log(`[WS] Pushed update at ${new Date().toLocaleTimeString()}`);
    } catch (e) {
      console.error("[WS] Failed to parse JSON:", e.message);
    }
  });

// Also watch evidence folder for new images
chokidar.watch(EVIDENCE_DIR, { usePolling: true, interval: 1000 })
  .on("add", () => {
    try {
      const data = JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
      data.evidence_images = getEvidenceImages();
      broadcast({ type: "update", payload: data });
    } catch {}
  });

wss.on("connection", (ws) => {
  console.log("[WS] Browser connected");
  // Send current state immediately on connect
  try {
    const data = JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
    data.evidence_images = getEvidenceImages();
    ws.send(JSON.stringify({ type: "update", payload: data }));
  } catch {
    ws.send(JSON.stringify({ type: "update", payload: getDefaultData() }));
  }
  ws.on("close", () => console.log("[WS] Browser disconnected"));
});

server.listen(PORT,"0.0.0.0", () => {
  console.log("╔════════════════════════════════════════════╗");
  console.log("║  Smart Kitchen Dashboard — Node.js Server  ║");
  console.log(`║  http://127.0.0.1:${PORT}                       ║`);
  console.log("║  Press Ctrl+C to stop                      ║");
  console.log("╚════════════════════════════════════════════╝");
});
