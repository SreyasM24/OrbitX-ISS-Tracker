# Background video

OrbitX shows a looping, muted ISS video behind the mission-control dashboard:

```
frontend/assets/iss-background.mp4
```

The intended background video (`iss-background.mp4`, ~2.39 MB, 1080p H.264) is included in the repository and served directly via Streamlit static serving (`app/static/iss-background.mp4`).

### Custom Video Replacement

To replace the background with your own clip:

1. Choose footage permitted for redistribution (your own video, public domain NASA footage, or Creative Commons clips).
2. Save it as `frontend/assets/iss-background.mp4` (or configure the `ORBITX_BACKGROUND_VIDEO` environment variable).
3. Restart the application. OrbitX will synchronize the file to `frontend/static/` for Streamlit to serve.
4. If no video file is present or browser autoplay is blocked, OrbitX gracefully displays the static dark navy glassmorphic gradient background without crashing or obscuring text.

**Recommended format:** H.264 MP4, 1080p or 720p, 10–30 seconds, muted, < 5 MB.
