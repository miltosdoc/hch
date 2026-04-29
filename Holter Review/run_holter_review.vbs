Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\Miltiadis.t\Desktop\WebdocAPI\Holter Review"
WshShell.Run "python app.py", 0, False
