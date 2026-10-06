"""Prepare four pin occurrences in one documented transformed-instance request."""
import json
import math
from prepare_pin import OUT, save

s = math.sqrt(.5)
instance = json.loads((OUT / 'insert-pin.json').read_text())
# Source installed_pin: Rx(45) * (Rx(90) * local + (x,76,1)) + (0,67,-84).
# Pin is symmetric about local X=0; the same proper rotation serves both handed positions.
groups = []
for x in (-135, -5, 5, 135):
    transform = [1,0,0,x/1000, 0,-s,-s,(67+75*s)/1000,
                 0,s,-s,(-84+77*s)/1000, 0,0,0,1]
    assert len(transform) == 16
    groups.append(dict(instances=[instance.copy()],transform=transform))
save('insert-four-pins',dict(transformGroups=groups))
