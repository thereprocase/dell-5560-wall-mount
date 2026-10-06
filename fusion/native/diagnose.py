import adsk.fusion as f
d=f.Design.cast(app.activeProduct)
result['components']=[]
for comp in d.allComponents:
    entry={'name':comp.name,'sketches':[]}
    for s in comp.sketches:
        entry['sketches'].append({'name':s.name,'fully':s.isFullyConstrained,
            'points':[{'xyz':p.geometry.asArray(),'fixed':p.isFixed,'fully':p.isFullyConstrained} for p in s.sketchPoints],
            'lines':[{'construction':p.isConstruction,'fixed':p.isFixed,'fully':p.isFullyConstrained} for p in s.sketchCurves.sketchLines],
            'dims':[{'expression':p.parameter.expression,'value':p.parameter.value} for p in s.sketchDimensions],
            'constraints':[p.objectType for p in s.geometricConstraints]})
    result['components'].append(entry)
