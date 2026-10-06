# Public project showcase

URL: https://thereprocase.github.io/dell-5560-wall-mount/

Local server: Python serve.py, listening only on 127.0.0.1:8876.
Tailscale Serve adds /mount-showcase on the existing HTTPS service.
The pre-existing root route and TCP routes are retained. No Funnel enabled.
Only ../../docs/ is served; dependencies, source scripts and server logs stay outside it.
Three.js assets are local, with its MIT license in ../../docs/vendor/THREE-LICENSE.txt.

Features: real STL before/after geometry for all 14 parts, matched camera,
exploded view, family focus, arm ghosting, technical edges, annotated original
screenshots, measured-fit reports and six updated oriented STL downloads.
Before meshes come from the original Revision F parts/. After meshes come from
FinishValidation.FCStd. Public downloads are print_refinements_oriented STLs.

Run serve.py with Python to restart the local server after a reboot.
The Tailscale --bg route persists separately from the Python process.
Run node check.cjs URL for a desktop/mobile browser check using installed Edge.
Do not use tailscale serve reset or disable the whole 443 listener: other services
are present. Manage this route specifically using --set-path=/mount-showcase.

The page summarizes CAD evidence. It does not claim physical printer/retention
validation or that the current ribbon fully matches the extracted Fusion content.

Canonical public files now live in ../../docs, served by both GitHub Pages and serve.py. Regenerate web meshes with export_scene.py after validating the native model. CFD gallery is a baseline study, not Revision G validation.
