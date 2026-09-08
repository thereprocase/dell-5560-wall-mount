path = '/workspace/scratch/b0c00b792513/mount-review/topology/work/v25'
path_calculix = '/tmp/topo-runtime/usr/bin/ccx'
file_name = 'bracket.inp'
for name in ['DESIGN','KEEP']:
    domain_optimized[name] = name == 'DESIGN'
    domain_density[name] = [1e-6,1.0]
    domain_thickness[name] = [10.,10.]
    domain_material[name] = ['*ELASTIC\n0.001,0.35','*ELASTIC\n1000.,0.35']
    domain_FI[name] = []
mass_goal_ratio = 0.25
filter_list = [['simple',4.0]]
optimization_base = 'stiffness'
cpu_cores = 2
sensitivity_averaging = True
mass_addition_ratio = .01
mass_removal_ratio = .04
ratio_type = 'absolute'
iterations_limit = 55
tolerance = .001
displacement_graph = [['LOAD','total']]
save_iteration_results = 1
save_solver_files = 'dat'
save_resulting_format = 'csv vtk'
