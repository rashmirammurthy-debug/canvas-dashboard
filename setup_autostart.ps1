# PowerShell script to register the monitor to start automatically on login.
# Run this once in PowerShell (as the child's user account).

$scriptPath = Join-Path $PSScriptRoot "start_monitor.pyw"
$startupFolder = [System.IO.Path]::Combine(
    [Environment]::GetFolderPath("Startup")
)

$shortcutPath = Join-Path $startupFolder "BrowserMonitor.lnk"
$pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = (Get-Command python -ErrorAction SilentlyContinue).Source
}

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$scriptPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7  # Minimized
$shortcut.Description = "Browser Activity Monitor"
$shortcut.Save()

Write-Host ""
Write-Host "Autostart configured!" -ForegroundColor Green
Write-Host "Shortcut created at: $shortcutPath"
Write-Host ""
Write-Host "The monitor will start automatically when this user logs in."
Write-Host "To remove, delete the shortcut from: $startupFolder"
