# Mission 3 — Mission Upgrade: Find the Flaws. Build What's Next.

## Learning objective

Think like professional space software engineers: audit a live application, identify meaningful improvements, limitations, or usability flaws, propose an architectural solution, and begin an engineering workflow that you can continue developing after the workshop.

## Estimated duration

10 minutes (Hands-on Workshop Phase 3 — with continued development at home)

## Concept

In professional aerospace and software engineering, software is never "finished" on the first release. Real development involves exploring existing systems, understanding design trade-offs, uncovering subtle limitations, and planning iterative upgrades.

In this mission, you and your partner will step into the shoes of the OrbitX core engineering team. You have 10 minutes to audit the application, pinpoint one high-impact opportunity for improvement, locate where it lives in the code, and propose how to build it. A small implementation during the session is optional; your primary goal is engineering discovery and planning.

### Distinguish Your Findings:
Before reporting an issue, classify it into the correct engineering category:
- **Confirmed Bug:** The application behaves contrary to its specifications or produces an error under reproducible conditions.
- **System Limitation:** A deliberate trade-off or boundary of the current design (e.g. SGP4 accuracy degrading after 7 days, or map tiles requiring internet access).
- **Usability Flaw:** The interface is confusing, hard to read on small screens, or lacks clear context for beginners.
- **Feature Request:** A brand new capability that expands the application's scientific or educational usefulness.

## Exploration areas

Explore the deployed dashboard at [https://orbitx-iss-tracker.streamlit.app](https://orbitx-iss-tracker.streamlit.app) and inspect the codebase. Consider investigating one of these areas:

1. **Dashboard Usability & Visual Clarity:**
   - Are the coordinate numbers and units immediately clear to someone without an astrophysics degree?
   - How does the layout look on mobile devices or smaller laptop screens?
2. **Telemetry & Unit Conversions:**
   - Altitude is shown in kilometers (`km`). What if international users or news outlets need altitude in miles (`mi`)?
   - The ISS travels at $\approx 7.66\text{ km/s}$ relative to Earth's center, but its ground track moves at $\sim 7.2\text{ km/s}$ relative to the ground. Could we show both?
3. **Pass Predictions & Visual Observation:**
   - In the **🔭 Passes** tab, OrbitX notes that a geometric pass does not guarantee visual sightings. Could we add an indicator for whether the pass happens during twilight when the ISS is illuminated by the sun against a dark sky?
4. **Data Freshness & Error States:**
   - What happens when a user enters an impossible latitude (e.g. 100° N) in the observer sidebar? Does OrbitX give a friendly, helpful error message?
5. **Testing & Edge-Case Robustness:**
   - Look inside the `tests/` directory. Are there edge cases (e.g. observer exactly at the South Pole, or passes crossing midnight) that could use additional automated test coverage?

## Practical workflow

Follow this 6-step engineering workflow with your partner:

1. **Explore:** Click through the tabs (**Map**, **Telemetry**, **Passes**, **Missions**) and sidebar controls.
2. **Identify:** Choose ONE specific limitation, usability issue, or new feature idea.
3. **Reproduce & Inspect:** Write down the exact steps to reproduce it, or articulate the missing capability.
4. **Locate Code:** Search the repository to find the relevant file and function (e.g. [`backend/formatting.py`](backend/formatting.py), [`frontend/components.py`](frontend/components.py), or [`frontend/tabs.py`](frontend/tabs.py)).
5. **Propose Solution:** Formulate a concrete, realistic design for the fix or feature.
6. **Decide:** If you have time and are running locally, implement a small code change. Otherwise, record your proposal for your workshop showcase and home development!

## Suggested challenges

Choose an upgrade that matches your team's interest and experience:

### Beginner: Add Altitude in Miles (Quick Code Upgrade)
Space-news broadcasts frequently quote the ISS altitude in miles. You can add this in just two small edits!

1. In [`backend/formatting.py`](backend/formatting.py), add this helper function:
```python
def format_altitude(altitude_km: float) -> str:
    """Format altitude with both kilometers and miles."""
    miles = altitude_km * 0.621371
    return f"{altitude_km:.0f} km ({miles:.0f} mi)"
```

2. In [`frontend/components.py`](frontend/components.py) inside `render_telemetry()`, import `format_altitude` and update line 117 to use it:
```python
c3.metric("Altitude", format_altitude(position.altitude_km),
          help="Height above the WGS84 ellipsoid.")
```
Refresh the browser to see: `422 km (262 mi)`!

### Intermediate: Custom Pass Countdown or Audio Alerts
- Design a card in the **Passes** tab that calculates a live countdown timer (`X hours Y minutes until next pass`) to the next visible flyover for the observer's city.
- Add an automated test in `tests/test_pass_table.py` that verifies the countdown formatting.

### Advanced: Solar Illumination & Sunlit Passes
- Use Skyfield's ephemeris to calculate whether the ISS is in Earth's shadow (umbra) or direct sunlight during each pass event.
- Filter the pass table to highlight true "Naked-Eye Viewing Opportunities" (observer in darkness, ISS in sunlight).

## Deliverable

Each pair will summarize their engineering proposal in the workshop showcase:
- **Discovery:** What issue, limitation, or improvement did you investigate?
- **Category:** Confirmed Bug / System Limitation / Usability Flaw / Feature Request.
- **Impact:** Why does this improvement matter to users or satellite observers?
- **Technical Path:** Which file(s) and function(s) in the repository would you modify?
- **Proposed Solution:** What is your planned approach or code change?

## Continue developing at home

**The 10 minutes in today's workshop is your launchpad — not the finish line!**

The complete OrbitX codebase is open source and designed for continued hands-on learning:
1. **Fork the Repository:** Visit [https://github.com/SreyasM24/OrbitX-ISS-Tracker](https://github.com/SreyasM24/OrbitX-ISS-Tracker) and click **Fork** to create your own copy on GitHub.
2. **Clone & Set Up Locally:** Follow the quickstart steps in the root [`README.md`](README.md) to set up your Python virtual environment on your personal computer.
3. **Create a Feature Branch:** In your terminal, create a branch for your upgrade:
   ```bash
   git checkout -b feature/my-iss-upgrade
   ```
4. **Build & Test:** Implement your idea, run the automated test suite with `pytest`, and verify that all 168 tests pass without regressions.
5. **Share Your Work:** Push your changes to your fork, document your work in your README, and share your project link with your GAAC mentors or open a Pull Request!

---
*Learning Outcome: You know how to evaluate a live codebase, specify software improvements, and participate in real open-source satellite software engineering.*
