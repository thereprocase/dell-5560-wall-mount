# Revision F airflow decision

Use a shrouded 40 mm rear gap, 45° upward/wallward fans, a gradual lower turn,
and a 12 mm nominal top slot. Start the contraction above the estimated intake
at Z=198 mm, reach the throat at 226 mm and continue to 232 mm. Alternative
8/16 mm rails preserve the same mounting interfaces and printable wall slopes.

Dell's inside-cover image reveals two approximately 70 × 40 mm intake windows
near X=±111 mm and Z≈151–191 mm. The exterior grille spans a larger width but
its covered center is not fully open. The reconstruction has ±4 mm location
uncertainty. The conservative intake upper edge remains below the contraction.

CFD_Design_Report.md records an actual 2D OpenFOAM RANS comparison. A smaller
slot raises modeled intake static pressure but reduces bypass flow. The study
does not establish actual flow through the machine, outlet entrainment distance
or cooling performance. It omits side leakage and does not resolve the laptop's
internal resistance/blowers. Use pressure and temperature measurements with
the selected fans to calibrate the next study.

The cheek lips remain noncontact and stop behind the laptop's side ports. They
reduce the gross open sides, but the mount is not an airtight duct. Actual
clearance, wall flatness and joint leakage remain physical checks.
