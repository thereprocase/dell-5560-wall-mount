workspace=app.userInterface.workspaces.itemById('SimulationEnvironment')
result['activation_result']=workspace.activate()
result['active_workspace']=app.userInterface.activeWorkspace.name
result['active_command']=app.userInterface.activeCommand
