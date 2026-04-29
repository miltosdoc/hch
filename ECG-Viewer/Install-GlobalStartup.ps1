# Check for Administrator privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Administrator privileges required to add a global startup item."
    Write-Host "Relaunching with elevation... Please click 'Yes' on the prompt." -ForegroundColor Cyan
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$vbsPath = "c:\Users\Miltiadis.t\Desktop\Programming\ECG-Viewer\run_ecg_viewer.vbs"
$startupPath = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
$shortcutPath = Join-Path $startupPath "ECG_Viewer_Service.lnk"

# Create the shortcut
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$vbsPath`""
$Shortcut.WorkingDirectory = "c:\Users\Miltiadis.t\Desktop\Programming\ECG-Viewer"
$Shortcut.Description = "Starts the ECG Viewer backend service invisibly."
$Shortcut.Save()

Write-Host "===============================================" -ForegroundColor Green
Write-Host "SUCCESS! ECG Viewer Global Startup Configured." -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host "`nThe ECG Viewer will now automatically start in the background"
Write-Host "for ANY user that logs into this machine."
Write-Host "`nShortcut created at:" -ForegroundColor Yellow
Write-Host $shortcutPath -ForegroundColor DarkGray
Write-Host "`nPress any key to close this window..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
