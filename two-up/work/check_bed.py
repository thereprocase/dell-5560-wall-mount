import json
BED = 256.0
rows = json.load(open('measured.json'))
fail = []
print(f"{'part':<30}{'bbox (mm)':<28}{'max':>8}{'brim+16':>9}  status")
for r in rows:
    bb = r['bbox']
    # print orientation: largest two dims lie on the bed, third is height
    dims = sorted(bb, reverse=True)
    height, bed_dims = dims[0], dims[1:]
    bedx, bedy = sorted(bed_dims, reverse=True)
    fits = bedx + 16.0 <= BED and bedy + 16.0 <= BED and height <= BED
    if not fits:
        fail.append(r['key'])
    print(f"{r['key']:<30}{str(bb):<28}{max(bb):8.1f}{bedx+16:9.1f}  {'PASS' if fits else 'FAIL'}")
print('FAILURES', fail)
