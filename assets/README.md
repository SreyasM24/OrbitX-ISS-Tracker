# Background video (optional, not included)

OrbitX shows a looping, muted ISS video behind the dashboard when this file exists:

```
assets/iss-background.mp4
```

The video is **not part of this repository**. The footage the maintainers used is third-party stock
footage whose redistribution terms are not confirmed, so it is git-ignored (`assets/*.mp4`).
Without the file the dashboard shows a dark navy gradient instead and everything else works.

To use your own video:

1. Choose footage you are allowed to use (your own, public domain, or a licence that permits
   redistribution, such as NASA media or Pexels/Pixabay clips; check the exact licence).
2. Save it as `assets/iss-background.mp4`, or point `ORBITX_BACKGROUND_VIDEO` at another path.
3. Restart the app. OrbitX copies the file to `static/` (git-ignored) so Streamlit can serve it.

Tips: H.264 MP4, 1080p or lower, 10-30 seconds, no audio needed (it is always muted), a few MB.
The app crossfades the end of the clip into its start, so a clip that does not loop perfectly
still looks smooth.
