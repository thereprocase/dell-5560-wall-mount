import adsk.fusion as f
closed=[]
for doc in list(app.documents):
    if doc.name.startswith('Native API validation - disposable'):
        closed.append(doc.name)
        doc.close(False)
for doc in app.documents:
    d=f.Design.cast(doc.products.itemByProductType('DesignProductType'))
    if d and d.attributes.itemByName('Dell5560','nativePort'):
        doc.activate()
        for o in list(d.rootComponent.occurrences):
            if o.component.name=='pin | reusable' and o.component.bRepBodies.count==0:
                o.deleteMe()
        result['active']=doc.name
        break
result['closed_tests']=closed
