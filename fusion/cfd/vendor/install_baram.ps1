param([ValidateSet('mpi','baram')][string]$Phase)
$ErrorActionPreference = 'Stop'
# Elevated Windows PowerShell can inherit a PowerShell 7 module search path.
# Resolve built-in modules against the executing shell before integrity checks.
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1')
$vendorRoot = 'F:\Code\dell-5560-wall-mount\fusion\cfd\vendor'
$payloadRoot = Join-Path $vendorRoot 'downloads\baram-extracted\$TEMP'
if ($Phase -eq 'mpi') {
    $installer = Join-Path $payloadRoot 'msmpisetup.exe'
    $expected = 'C305CE3F05D142D519F8DD800D83A4B894FC31BCAD30512CEFB557FEACCBE8B4'
    if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expected) { throw 'MPI hash mismatch' }
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') { throw 'MPI signature invalid' }
    $process = Start-Process -FilePath $installer -ArgumentList '-unattend' -WindowStyle Hidden -Wait -PassThru
    @{phase=$Phase;exit_code=$process.ExitCode;sha256=$expected} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $vendorRoot 'mpi_install.json')
    if ($process.ExitCode -notin @(0,3010)) { throw "MPI installer exit $($process.ExitCode)" }
} else {
    $installer = Join-Path $payloadRoot 'BARAM-26.3.0-win64.msi'
    $expected = 'FF87AEA71706425F76A098BDBD3B648F3C2247F1B1D82E02A358B5FC126075BE'
    if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expected) { throw 'BARAM hash mismatch' }
    $target = Join-Path $env:LOCALAPPDATA 'Programs\BARAM-26.3.0'
    if (Test-Path -LiteralPath (Join-Path $target 'BaramFlow.exe')) { throw 'Target already installed; inspect before changing' }
    $log = Join-Path $vendorRoot 'baram_install.log'
    $arguments = '/i "{0}" /qn /norestart /L*v "{1}" TARGETDIR="{2}" ALLUSERS=2 MSIINSTALLPERUSER=1' -f $installer,$log,$target
    $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    @{phase=$Phase;exit_code=$process.ExitCode;sha256=$expected;target=$target} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $vendorRoot 'baram_install.json')
    if ($process.ExitCode -notin @(0,3010)) { throw "BARAM installer exit $($process.ExitCode); see $log" }
}
