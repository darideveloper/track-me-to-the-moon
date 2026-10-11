Option Explicit

' Console-free Windows entry point. The Flet window remains visible.
Dim shell, fso, command, i
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

command = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " _
    & Quote(fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "run.ps1")) & " -Hidden"

For i = 0 To WScript.Arguments.Count - 1
    command = command & " " & Quote(WScript.Arguments(i))
Next

shell.Run command, 0, False

Function Quote(value)
    Quote = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
