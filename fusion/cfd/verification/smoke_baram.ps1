$ErrorActionPreference='Stop'
$baramRoot=Join-Path $env:LOCALAPPDATA 'Programs\BARAM-26.3.0'
$env:WM_PROJECT_DIR=Join-Path $baramRoot 'solvers\openfoam'
$env:PATH="$baramRoot\solvers\mingw64\bin;$baramRoot\solvers\mingw64\lib;$env:WM_PROJECT_DIR\bin;$env:WM_PROJECT_DIR\lib;$env:WM_PROJECT_DIR\lib\msmpi;$env:PATH"
$sourceCase=Join-Path $PSScriptRoot 'tutorial_cavity_v2412'
$testCase=Join-Path $PSScriptRoot 'tutorial_cavity_baram_windows'
if(Test-Path -LiteralPath $testCase){throw 'Preserve existing test; refusing overwrite'}
New-Item -ItemType Directory -Path $testCase | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceCase '0'),(Join-Path $sourceCase 'system') -Destination $testCase -Recurse
New-Item -ItemType Directory -Path (Join-Path $testCase 'constant') | Out-Null
Get-ChildItem -LiteralPath (Join-Path $sourceCase 'constant') -File | Copy-Item -Destination (Join-Path $testCase 'constant')
$results=@()
foreach($exeName in @('blockMesh','checkMesh','icoFoam')){
    $arguments=@('-case',$testCase)
    if($exeName -eq 'checkMesh'){$arguments+=@('-allGeometry','-allTopology')}
    $log=Join-Path $testCase ('log.'+$exeName)
    & (Join-Path $env:WM_PROJECT_DIR ('bin\'+$exeName+'.exe')) @arguments > $log 2>&1
    $exitCode=$LASTEXITCODE
    $results+=@{executable=$exeName;exit_code=$exitCode;log=$log}
    if($exitCode -ne 0){$results|ConvertTo-Json|Set-Content (Join-Path $testCase 'result.json');throw "$exeName failed; see $log"}
}
$results|ConvertTo-Json|Set-Content (Join-Path $testCase 'result.json')
$results|ConvertTo-Json
