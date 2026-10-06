param([string]$CasePath = "$PSScriptRoot/cases/OpenCFD_v2412/installed_pressure10_v3")
$ErrorActionPreference = 'Stop'
$env:WINDIR = [Environment]::GetFolderPath('Windows')
$env:SystemRoot = $env:WINDIR
$env:USERPROFILE = [Environment]::GetFolderPath('UserProfile')
Import-Module "$PSHOME/Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1"
Import-Module "$PSHOME/Modules/Microsoft.PowerShell.Management/Microsoft.PowerShell.Management.psd1"
Add-Type -AssemblyName PresentationFramework
$window = New-Object Windows.Window
$window.Title = 'Precision 5560 - live CFD run'
$window.Width = 1050
$window.Height = 760
$window.Background = '#F3F5F8'
$stack = New-Object Windows.Controls.StackPanel
$stack.Margin = '20'
$window.Content = $stack
function Label([string]$value, [int]$size) {
    $label = New-Object Windows.Controls.TextBlock
    $label.Text = $value
    $label.FontSize = $size
    $label.Margin = '0,0,0,12'
    $stack.Children.Add($label) | Out-Null
    return $label
}
$header = Label 'Precision 5560 | installed airflow exploration' 25
$engine = Label 'BARAM OpenFOAM v2412 | Windows MS-MPI | 8 workers | 836,278 cells' 16
$status = Label 'Reading solver log...' 21
$residuals = Label '' 15
$caution = Label 'Idealized 10 Pa fans; assumed internal ducts; no thermal prediction.' 14
$buttons = New-Object Windows.Controls.StackPanel
$buttons.Orientation = 'Horizontal'
$stack.Children.Add($buttons) | Out-Null
$folder = New-Object Windows.Controls.Button
$folder.Content = 'Open run folder'
$folder.Padding = '14,7'
$folder.Margin = '0,0,12,12'
$folder.Add_Click({ Start-Process explorer.exe -ArgumentList $CasePath })
$buttons.Children.Add($folder) | Out-Null
$preview = New-Object Windows.Controls.Button
$preview.Content = 'Open latest streamline image'
$preview.Padding = '14,7'
$preview.Margin = '0,0,0,12'
$preview.Add_Click({
    $latest = Get-ChildItem "$CasePath/results" -Filter airflow_streamlines.png -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { Start-Process $latest.FullName }
})
$buttons.Children.Add($preview) | Out-Null
$logView = New-Object Windows.Controls.TextBox
$logView.IsReadOnly = $true
$logView.FontFamily = 'Consolas'
$logView.FontSize = 12
$logView.Height = 430
$logView.VerticalScrollBarVisibility = 'Auto'
$logView.HorizontalScrollBarVisibility = 'Auto'
$stack.Children.Add($logView) | Out-Null
$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(2)
$timer.Add_Tick({
    try {
        $lines = Get-Content "$CasePath/log.simpleFoam_windows" -Tail 160
        $raw = $lines -join "`n"
        $times = [regex]::Matches($raw, '(?m)^Time = (\d+)')
        $iteration = if ($times.Count) { $times[$times.Count-1].Groups[1].Value } else { '?' }
        $state = if ($raw -match 'SIMPLE solution converged') { 'Converged' } elseif ($raw -match '(?m)^End\s*$') { 'Solver finished - review convergence' } elseif ((Get-Date) - (Get-Item "$CasePath/log.simpleFoam_windows").LastWriteTime -gt [TimeSpan]::FromSeconds(30)) { 'Log inactive - check process' } else { 'Running' }
        $status.Text = "$state | iteration $iteration / 1200 | refreshed $(Get-Date -Format HH:mm:ss)"
        $blocks = [regex]::Split($raw, '(?m)^Time = \d+\s*$')
        $block = $blocks[-1]
        if ($block -notmatch 'Solving for k,' -and $blocks.Length -gt 1) { $block = $blocks[-2] }
        $values = foreach ($field in @('Ux','Uy','Uz','p','k','omega')) {
            $match = [regex]::Match($block, "Solving for $field, Initial residual = ([^,]+)")
            if ($match.Success) { '{0}: {1:E2}' -f $field, [double]$match.Groups[1].Value }
        }
        $residuals.Text = "Initial residuals (target 1e-5):`n" + ($values -join '    ')
        $logView.Text = ($lines | Select-Object -Last 32) -join "`r`n"
        $logView.ScrollToEnd()
    } catch { $status.Text = $_.Exception.Message }
})
$window.Add_Closed({ $timer.Stop() })
$timer.Start()
$window.ShowDialog() | Out-Null
