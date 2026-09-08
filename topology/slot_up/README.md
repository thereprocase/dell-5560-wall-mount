# Slot-inclusive 3D topology studies

Selected geometry: `tilted_grip`, with 32 mm minimum rear finger clearance over
the upper 80 mm grasp region. See `../HUMAN_FACTORS.md` and `../JOURNAL.md`.
`near_wall` (8 mm gap) and `hand_clearance` (20 mm parallel gap) are comparison
studies, not selected ergonomic designs. The original `study.py` uses a 28 mm gap.

Run from the repository root after `python topology/bootstrap.py`:

```bash
topology/runtime/venv/bin/python topology/slot_up/tilted_grip/study.py
topology/runtime/venv/bin/python topology/slot_up/recheck.py topology/slot_up/tilted_grip
topology/runtime/venv/bin/python topology/slot_up/grip_layout.py
```

Study scripts refuse to overwrite an existing case. Rename or archive an old
`work` directory to make a fresh run. C3D8 elements have a nominal 2 mm spacing;
the tilted trial maps the XY coordinates while keeping the wall pads fixed.
The BESO casting filter has a documented copied-file sector allocation patch.
Each search uses up to 50 iterations and does not establish a global optimum.

Rechecks close build columns and repair diagonal-only surface contacts by adding
permitted cells. They then require one face-connected, watertight, consistently
wound mesh and compare its volume with the sum of its element prism volumes.
The layer estimator uses the transformed polygons, 1.2 mm walls, five 0.2 mm
solid top and bottom layers, and 20% internal material. Each element's resulting
solid fraction scales an assumed orthotropic PETG stiffness tensor; deleted
elements are absent from the recheck. Numerical material assumptions, ideal wall
clamps, coarse mesh and lack of explicit friction/contact mean these are
screening results, not validated strength or creep predictions.

`results/*_screening.stl` files are intermediate meshes without finished screw
holes, final chamfers or validated fit. No final mount or G-code is implied.
OrcaSlicer 2.4.2 was downloaded and extracted but could not launch due to missing
host OpenGL runtime libraries; layer CSVs are geometric estimates rather than
slicer extrusion paths. PETG density is assumed 1.27 g/cm³.
