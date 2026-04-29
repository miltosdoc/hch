$startup = [Environment]::GetFolderPath('Startup')
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$startup\start_all_services.lnk")
$sc.TargetPath = 'c:\Users\Miltiadis.t\Desktop\WebdocAPI\start_all_services.vbs'
$sc.WorkingDirectory = 'c:\Users\Miltiadis.t\Desktop\WebdocAPI'
$sc.Description = 'Start Pulsus + Integrationsportalen'
$sc.Save()
Write-Output "Shortcut created at: $startup\start_all_services.lnk"
