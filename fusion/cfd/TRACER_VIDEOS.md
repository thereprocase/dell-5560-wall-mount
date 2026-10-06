# Moving-tracer CFD videos

The original arrows report velocity at fixed locations. They can remain
stationary even when air is moving rapidly. The new `latest-tracers.mp4`
companions show moving visualization particles with fading trails over static
pressure in the front-lip and hinge sections.

Particles follow `U_y` and `U_z` on the saved plane at X = +111 mm. Integration
uses physical seconds and velocities in m/s, second-order midpoint RK2, and a
maximum 12.5 microsecond step. Spatial interpolation uses the actual sampled
triangles, including their holes; temporal interpolation is linear between
saved fields. Samples are checked against the checkpoint's SHA-256 manifest.
MPI-induced point reordering is accepted only after exact coordinate and
triangle-set equivalence checks.

The movies show projected 2D motion. They omit out-of-plane velocity and do not
reconstruct full 3D particle trajectories. Pressure is interpolated for display.
Particles are randomly reseeded at exits, sampled solids and age limits, so dot
density is not a concentration measurement. Underlying CFD limitations still
apply.

Both clips run at 60 fps and five times the original playback speed, with a
0.1 second final hold. Original videos and raw CFD samples remain available.
`latest-tracers.json` records the source checkpoint, hashes, physical interval,
integration settings, particle travel and video verification. The ordinary
hourly page builders regenerate the companions when the source changes.

Validation includes uniform transport with physical-unit conversion, linear
spatial and temporal fields, solid-body rotation and a solid-gap reseeding check:

```powershell
& 'C:/Program Files/FreeCAD 1.1/bin/python.exe' fusion/cfd/test_revh_tracers.py
```

Publication checks cover all source samples, end time, particle displacement,
full MP4 decoding, browser playback and seeking, and deployed file hashes.
