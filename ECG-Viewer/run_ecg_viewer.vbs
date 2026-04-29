Set objShell = CreateObject("WScript.Shell")
' Run the PowerShell script invisibly
objShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""c:\Users\Miltiadis.t\Desktop\Programming\ECG-Viewer\Start-ECGViewer.ps1""", 0, False
