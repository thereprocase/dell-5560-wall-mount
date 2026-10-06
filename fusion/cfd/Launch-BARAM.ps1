param([ValidateSet('Flow','Mesh')][string]$Application='Flow')
$ErrorActionPreference='Stop'
$baramRoot=Join-Path $env:LOCALAPPDATA 'Programs\BARAM-26.3.0'
$profilePath=[Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
if (-not $profilePath -or -not (Test-Path -LiteralPath $profilePath)) { throw 'Windows profile directory unavailable' }
$launchInfo=New-Object System.Diagnostics.ProcessStartInfo
$launchInfo.FileName=Join-Path $baramRoot ('Baram'+$Application+'.exe')
$launchInfo.WorkingDirectory=$baramRoot
$launchInfo.UseShellExecute=$false
# Some automation hosts omit USERPROFILE. Supply it only to this child process.
$launchInfo.EnvironmentVariables['USERPROFILE']=$profilePath
$mpiBin=[Environment]::GetEnvironmentVariable('MSMPI_BIN','Machine')
if ($mpiBin -and (Test-Path -LiteralPath (Join-Path $mpiBin 'mpiexec.exe'))) {
    $launchInfo.EnvironmentVariables['MSMPI_BIN']=$mpiBin
    $launchInfo.EnvironmentVariables['PATH']=$mpiBin+';'+$launchInfo.EnvironmentVariables['PATH']
}
$launched=[System.Diagnostics.Process]::Start($launchInfo)
[PSCustomObject]@{Id=$launched.Id;Application=$Application;Profile=$profilePath}
