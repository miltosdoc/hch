Set WshShell = CreateObject("WScript.Shell")
' Run pythonw.exe so no console window appears
WshShell.Run "pythonw.exe app\app.py", 0, False
