from pathlib import Path
import json
base=Path(__file__).resolve().parent
src=base/'geometry_traced_repaired/fluid_boundary.stl'
for digits in (9,8,7):
 out=base/f'geometry_traced_repaired/fluid_boundary_round{digits}.stl'
 lines=[];maxdelta=0
 for line in src.read_text().splitlines():
  cols=line.split()
  if cols and cols[0]=='vertex':
   a=[float(x) for x in cols[1:]];b=[round(x,digits) for x in a]
   maxdelta=max(maxdelta,sum((x-y)**2 for x,y in zip(a,b))**.5)
   line='      vertex '+' '.join(f'{x:.{digits}f}' for x in b)
  lines.append(line)
 out.write_text('\n'.join(lines)+'\n')
 print(digits,maxdelta)
