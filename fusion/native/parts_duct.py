"""Native ruled channel, fan seat and keyed structural saddle."""
def build(b):
    levels=[((23,-128),(111,-40)),((8,-80),(66,-28)),((4,-35),(42,-10)),((4,0),(40,0))]
    with b.group('10 Air path | ruled wall sections'):
        outer=[b.section(f'Outer station {i+1}',*v) for i,v in enumerate(levels)]
        shells=[b.loft(f'Ruled outer span {i+1}',outer[i],outer[i+1]) for i in range(3)]
        shell=b.join('Unite three ruled spans',*shells)
        inner=[b.section(f'Inner station {i+1}',*v,inner=True) for i,v in enumerate(levels)]
        voids=[b.loft(f'Ruled inner span {i+1}',inner[i],inner[i+1]) for i in range(3)]
        shell=b.cut('Hollow air path | shared skin thickness',shell,*voids)
    with b.group('20 Fan interface | seat and retention'):
        deck=b.box('Fan mounting deck',1,140,4,136,-110,-104,fillet=3,axis='Z')
        deck=b.cut('Open circular fan inlet',deck,b.cylinder('Fan inlet',58,8,(70,70,-111),axis='Z'))
        deck=b.cut('Recess sliding tray seat',deck,b.box('Tray seat recess',11,130,8,132,-107.6,-103.9))
        bosses=[b.box(f'Pin socket boss {i+1}',a,z,122,136,-110,-97,fillet=2,axis='Z') for i,(a,z) in enumerate([(1,11),(130,140)])]
        deck=b.join('Join socket bosses to deck',deck,*bosses)
        for i,x in enumerate((5,135)):
            deck=b.cut(f'Cut sliding groove {i+1}',deck,b.tongue(f'Tray groove {i+1}',x,8.7,137,True))
            deck=b.cut(f'Drill pin socket {i+1}',deck,b.cylinder(f'Pin socket {i+1}','pinSocketDiameter/2',10,(x,128,-103)))
        deck=b.tilt('Orient fan seat',deck)
        shell=b.join('Join fan seat to channel inlet',shell,deck)
    with b.group('30 Load path | saddle and glued tenons'):
        saddle=b.box('Cradle joint saddle',139,175.5,26.3,36.3,-64,-12)
        ramp=b.prism('Diagonal saddle buttress','XZ',36.3,[(136,-91),(175.5,-51.5),(175.5,-12),(136,-12)],10)
        shell=b.join('Join saddle buttress and tenons',shell,saddle,ramp,*b.keys('Duct tenons','duct'))
    with b.group('40 Service | lower wall bolt access'):
        tool=b.roof_hole('Lower driver access',9,45,('wallBoltX',8,'lowerWallBoltZ'),roof='+Z',bridge=4)
        shell=b.cut('Open printable driver corridor',shell,tool)
    with b.group('50 Socket junction | preserve source clearance'):
        # The two kernels resolve this tiny tangent socket/channel intersection
        # differently. Clip the relief to the first inner ruled wall, preserving
        # the exported Revision F socket opening without redrilling the channel.
        n=(58**2+52**2)**.5
        y0='70 mm + 44 mm*sqrt(2) - ductSkin'
        y1=f'70 mm + (55 mm - ductSkin*{110/n:.14g})/sqrt(2)'
        z1=f'-104 mm + (57 mm + ductSkin*{6/n:.14g})/sqrt(2)'
        slope=f'(({y1})-({y0}))/(({z1})+104 mm)'
        ymax=f'({y0})+({slope})*ductSkin'
        clip=b.prism('Socket to channel boundary','YZ',0,
            [(128,-104),(y0,-104),(ymax,'-104 mm+ductSkin'),(128,'-104 mm+ductSkin')],
            '1 mm+ductSkin')
        hole=b.cylinder('Inboard socket junction relief','pinSocketDiameter/2',10,(5,128,-103))
        relief=b.intersect('Limit relief to inner ruled wall',hole,clip)
        relief=b.tilt('Orient socket junction relief',relief)
        shell=b.cut('Resolve source socket opening',shell,relief)
    return shell
