# Smart Kitchen Dashboard — Node.js + Express

## Project Structure

```
smart_kitchen_node/
├── server.js                 ← Node.js Express + WebSocket server
├── package.json              ← Dependencies
├── start.bat                 ← One-click launcher (Windows)
├── dashboard_data.json       ← Written by yolo_main.py (place here)
├── public/
│   └── dashboard.html        ← Dashboard UI

```

## Setup (One Time Only)

### Step 1 — Install Node.js
Download and install from: https://nodejs.org  
Choose the **LTS** version.

### Step 2 — Install dependencies
```powershell
cd E:\Aditya\smart-Kitchen-Hygiene\smart_kitchen_node
npm install
```

### Step 3 — Copy your files
- Copy `dashboard_data.json` from your project root into this folder

## Running the Dashboard

### Option A — Double-click
Just double-click **`start.bat`** — it installs deps automatically and starts the server.

### Option B — Terminal
```powershell
cd E:\Aditya\smart-Kitchen-Hygiene\smart_kitchen_node
node server.js
```

Then open: **http://127.0.0.1:3000**

## Auto-start on Windows Boot

1. Press `Win + R` → type `shell:startup` → Enter
2. Create a shortcut to `start.bat` in that folder
3. Done — dashboard starts automatically every boot!

## How it works

```
yolo_main.py  →  writes dashboard_data.json  (every 3 seconds)
                          ↓
server.js     →  detects file change via chokidar
                          ↓
WebSocket     →  pushes update to ALL browsers INSTANTLY
                          ↓
Dashboard     →  updates live with no page refresh needed
```

## Key upgrade over Flask

| Feature        | Flask        | Node.js        |
|----------------|--------------|----------------|
| Updates        | Poll every 10s | WebSocket INSTANT |
| Connection indicator | ❌ | ✅ Live dot |
| Auto-reconnect | ❌ | ✅ Built-in |
| Start method   | Python venv  | Double-click .bat |

## Point yolo_main.py to this folder

Update the `DATA_FILE` path in `yolo_main.py`:
```python
DATA_FILE = r"E:\Aditya\smart-Kitchen-Hygiene\smart_kitchen_node\dashboard_data.json"
```
