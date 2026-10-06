import adsk.core as c
import adsk.fusion as f
from native.kernel import Builder
doc=app.documents.add(c.DocumentTypes.FusionDesignDocumentType)
doc.name='Native API validation - disposable'
d=f.Design.cast(app.activeProduct);d.designType=f.DesignTypes.ParametricDesignType
o=d.rootComponent.occurrences.addNewComponent(c.Matrix3D.create())
b=Builder(d,o.component,'Probe')
with b.group('Constrained datum profile and section radii'):
    body=b.box('Rounded block',140,184,0,10,-65,184,fillet=4)
result.update(sketches=[dict(name=s.name,fully_constrained=s.isFullyConstrained) for s in b.sketches],volume=body.volume*1000)
app.activeViewport.fit()
