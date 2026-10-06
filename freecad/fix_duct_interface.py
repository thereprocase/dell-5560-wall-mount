"""Keep wall-side duct sections fixed while the fan inlet width varies."""
def apply(d):
    count=0
    for o in d.Objects:
        if o.TypeId=='Sketcher::SketchObject' and 'duct section' in o.Label:
            for prop,expression in list(o.ExpressionEngine):
                if 'Parameters.fanFrameWidth' in expression:
                    expression=expression.replace('(Parameters.fanFrameWidth / 1 mm - 120) / 2','0')
                    o.setExpression(prop,expression); count+=1
    d.recompute()
    return count
