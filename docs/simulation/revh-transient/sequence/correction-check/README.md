# Short correction-count comparison

Six physical steps compare two and three PIMPLE outer correction passes from identical Revision H steady-iteration-300 fields. Both cases retain two pressure correctors and one nonorthogonal correction. Native binary internal fields are compared directly.

The acceptance limits were written before each solve: RMS error at most 0.1% of reference RMS, maximum error at most 1% of reference maximum, plus 1e-6 absolute tolerance for each of U, p, k, omega and nut; maximum Courant 0.5; boundary flux imbalance ratio at most 1e-4.

- The 25 microsecond comparison passed every field-difference check but failed the Courant criterion (approximately 0.734).
- The 12.5 microsecond comparison passed all criteria (maximum Courant approximately 0.367). Its largest absolute U-component difference was 0.001868 m/s; largest pressure difference was 0.05241 m2/s2, or 0.06289 Pa at the assumed density of 1.2 kg/m3. Neither comparison logged turbulence bounding.

The new flowing-field transient therefore uses two outer correction passes, starts at 12.5 microseconds, and adapts toward Courant 0.5 with a 25 microsecond maximum. Its source is the later iteration-400 field, explicitly unconverged, and it remains under monitoring.

The reported wall-time ratios are not isolated speed benchmarks: other solves were running, and the steady preparation ended during the smaller-step comparison. Do not interpret the approximately 2.03 ratio as a proven twofold solver speedup.

These are short coupling checks. They do not establish time-step independence, mesh independence, long-time shedding statistics, or thermal performance. All source fields remain preserved locally; reports and solver logs are archived here.
