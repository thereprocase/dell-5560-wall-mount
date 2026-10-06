import adsk.core as c
result['workspaces']=[{'id':w.id,'name':w.name,'active':w.isActive} for w in app.userInterface.workspaces]
result['simulation_commands']=[{'id':cmd.id,'name':cmd.name} for cmd in app.userInterface.commandDefinitions if any(k in (cmd.id+' '+cmd.name).lower() for k in ('cooling','simulation','newstudy','fan '))]
