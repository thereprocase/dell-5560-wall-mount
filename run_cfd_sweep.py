from cfd_study import make_case,run
cases=[('straight_12',12,False,2,20,.4),('curved_8',8,True,2,20,.4),('curved_12',12,True,2,20,.4),('curved_16',16,True,2,20,.4),('curved_12_medium',12,True,1.3,20,.4),('curved_12_fine',12,True,.85,20,.4),('curved_12_low_pressure',12,True,2,10,.4),('curved_12_high_draw',12,True,2,20,.8)]
for name,gap,curved,h,p,d in cases:run(make_case(name,gap,curved,h,p,d))
