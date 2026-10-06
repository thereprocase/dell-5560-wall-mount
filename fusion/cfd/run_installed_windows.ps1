param([ValidateSet('mesh','zones','solve')][string]$Phase)
$ErrorActionPreference='Stop'
$baramRoot=Join-Path $env:LOCALAPPDATA 'Programs\BARAM-26.3.0'
$env:WM_PROJECT_DIR=Join-Path $baramRoot 'solvers\openfoam'
$env:PATH="$baramRoot\solvers\mingw64\bin;$baramRoot\solvers\mingw64\lib;$env:WM_PROJECT_DIR\bin;$env:WM_PROJECT_DIR\lib;$env:WM_PROJECT_DIR\lib\msmpi;C:\Program Files\Microsoft MPI\Bin;$env:PATH"
$case=Join-Path $PSScriptRoot 'cases\OpenCFD_v2412\installed_pressure10_v3'
Set-Location -LiteralPath $case
function Run-Foam([string]$Tool,[string[]]$Arguments,[string]$Log){
 & (Join-Path $env:WM_PROJECT_DIR ('bin\'+$Tool+'.exe')) @Arguments > $Log 2>&1
 if($LASTEXITCODE -ne 0){throw "$Tool exit $LASTEXITCODE; see $Log"}
}
if($Phase -eq 'mesh'){
 if(-not (Test-Path -LiteralPath 'constant/polyMesh')){Run-Foam blockMesh @() 'log.blockMesh_windows';Run-Foam decomposePar @() 'log.decomposeMesh_windows'}
 & 'C:/Program Files/Microsoft MPI/Bin/mpiexec.exe' -n 8 (Join-Path $env:WM_PROJECT_DIR 'bin\snappyHexMesh.exe') -parallel -overwrite > log.snappyHexMesh_windows 2>&1
 if($LASTEXITCODE -ne 0){throw 'snappyHexMesh failed'}
 Run-Foam reconstructParMesh @('-constant') 'log.reconstructMesh_windows'
 Run-Foam checkMesh @('-constant','-allGeometry','-allTopology') 'log.checkMesh_windows'
 Get-Content log.checkMesh_windows -Tail 40
}elseif($Phase -eq 'zones'){
 Run-Foam topoSet @() 'log.topoSet_windows'
 Get-Content log.topoSet_windows -Tail 50
}else{
 Run-Foam decomposePar @('-force') 'log.decomposeSolve_windows'
 & 'C:/Program Files/Microsoft MPI/Bin/mpiexec.exe' -n 8 (Join-Path $env:WM_PROJECT_DIR 'bin\simpleFoam.exe') -parallel > log.simpleFoam_windows 2>&1
 if($LASTEXITCODE -ne 0){throw 'simpleFoam failed'}
 Run-Foam reconstructPar @('-latestTime') 'log.reconstructSolution_windows'
 Get-Content log.simpleFoam_windows -Tail 50
}
