# Mission 1 — Data Detective: Where Does the ISS Data Come From?

## Learning objective

Understand where OrbitX obtains orbital data, how to verify its origin and freshness, and how automatic fallback keeps the tracker reliable when networks fail.

## Estimated duration

15 minutes (Hands-on Workshop Phase 1)

## Concept

A satellite tracker cannot function without orbital data. Unlike ground vehicles tracked by cellular GPS, the International Space Station (ISS) orbits Earth at approximately 27,600 km/h (7.66 km/s) in the harsh environment of Low Earth Orbit (LEO).

Instead of streaming direct, continuous GPS telemetry to web browsers, the satellite tracking community relies on an international standard known as a **TLE (Two-Line Element set)**. A TLE is a compact, two-line text record containing mean orbital elements (inclination, eccentricity, mean motion, and drag terms) generated from radar and optical tracking observations by the U.S. Space Surveillance Network.

Every TLE corresponds to a specific point in time called the **epoch**:
- Low Earth Orbit satellites experience upper atmospheric drag and occasional reboost maneuvers, causing their actual path to slowly drift away from old mathematical fits.
- A TLE with an epoch less than 24 hours old provides excellent tracking accuracy (sub-kilometer).
- A TLE that is two weeks old will drift by tens or hundreds of kilometers, making pass predictions unreliable.

For this reason, a scientific satellite tracker must be completely honest about **where** its data came from, **when** the orbital fit was made, and **how fresh** that data is.

## What to investigate

In this mission, you and your partner will investigate the live data pipeline of OrbitX:
1. **Data Source Mode:** Determine whether OrbitX is currently running in **LIVE**, **CACHED**, or **SAMPLE** mode.
2. **TLE Epoch & Data Age:** Find the exact date and UTC time the orbital elements were calculated, and how many hours or days old they are.
3. **Download Timestamp:** Distinguish between when OrbitX *downloaded* the text record versus the *epoch* of the orbital elements themselves.
4. **Data Provider:** Identify which external provider (CelesTrak, ARISS live mirror, or WhereTheISS.at mirror) supplied the elements.
5. **Fallback Resilience:** Understand how OrbitX behaves when internet connectivity is lost or when a provider times out.

## Guided steps

### Step 1: Inspect the Mission Control Header
Open the running OrbitX dashboard in your browser (at [https://orbitx-iss-tracker.streamlit.app](https://orbitx-iss-tracker.streamlit.app) or locally via `http://localhost:8501`). Look at the **Data status** panel directly below the header:

- **Left column (Data source):** Check the badge:
  - 🟢 **LIVE · [Provider]**: The elements were fetched directly over the network during this session.
  - 🔵 **CACHED · [Provider]**: The elements were downloaded recently and are being reused within the 2-hour courtesy window.
  - 🔴 **SAMPLE · bundled offline file, NOT live**: No network or cache was available; OrbitX fell back to `backend/data/sample_iss.tle`.
- **Middle column (Orbital element epoch):** Note the UTC timestamp and the relative age (e.g. `7.2 h old`).
- **Right column (Element freshness):** Note the freshness badge: **FRESH** (< 3 days), **STALE** (3–14 days), or **EXPIRED** (> 14 days).

### Step 2: Uncover Provenance Details
Click on the expander titled **🔍 Network & Provenance Details** directly below the status cards. Record:
- **Application Version**
- **Last Fetch Attempt (UTC)**
- **Data Source Mode**
- **Local Cache Active** (Yes/No)
- **Retrieved At (UTC)**
- **Endpoint Probe History:** Review the response latency and HTTP status code of recent server checks.

### Step 3: Inspect the Source Configuration
Open the project repository in your code editor (e.g. VS Code). Open [`backend/config.py`](backend/config.py) and locate lines 34–45:
- Identify `DEFAULT_TLE_URLS`: notice that OrbitX configures a sequential failover list:
  1. `CELESTRAK_URL` (official CelesTrak NORAD 25544 GP endpoint)
  2. `ARISS_TLE_URL` (Amateur Radio on the ISS live mirror)
  3. `WHERETHEISS_TLE_URL` (WhereTheISS.at live REST mirror)
  4. `CELESTRAK_FALLBACK_URL` (CelesTrak stations group feed)
- Notice `CACHE_TTL_S = 7200` (2 hours): why do we wait 2 hours before re-downloading? (CelesTrak only updates elements every few hours, and asks clients not to spam their servers).

### Step 4: Test Offline Fallback (Local Laptops)
If running locally in PowerShell, stop the app and launch it in offline mode:
```powershell
.\scripts\run.ps1 -Offline
```
Observe how the dashboard responds:
- Does it crash? No!
- What does the data source badge say now? (It switches to `CACHED` if a recent cache exists, or `SAMPLE` if cache is absent).
- What warning appears at the top of the screen?

## Investigation questions

Discuss these questions with your partner and record your answers:

1. **What is a TLE, and what information does it contain?**
2. **What is the difference between the TLE Epoch and the Download Timestamp?**
3. **If you download a TLE right now, does that guarantee the orbital data is only 1 minute old? Why or why not?**
4. **What does LIVE mean in OrbitX? Does LIVE mean you have a direct telemetry radio signal from the astronauts?**
5. **Why does OrbitX implement multiple backup mirrors (ARISS, WhereTheISS.at) rather than relying exclusively on CelesTrak?**
6. **What are the scientific limitations of predicting satellite passes using a TLE that is 20 days old?**

## Deliverable

Each pair must write down or share in the workshop showcase:
- The currently observed **Data Source** and **Provider Name**.
- The **TLE Epoch** (UTC) and its exact **Data Age**.
- The **Download Timestamp** and how long ago it was cached.
- A one-sentence explanation of why OrbitX falls back to bundled sample data instead of crashing when internet access is unavailable.

---
*Learning Outcome: You understand the origin, freshness limits, and architectural failover of satellite orbital data.*
