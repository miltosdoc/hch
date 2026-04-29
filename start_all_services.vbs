Set WshShell = CreateObject("WScript.Shell")
' Run start_all_services.bat minimized so it doesn't block the desktop
WshShell.Run """c:\Users\Miltiadis.t\Desktop\WebdocAPI\start_all_services.bat""", 7, False
