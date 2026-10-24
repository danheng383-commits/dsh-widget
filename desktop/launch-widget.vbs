' launch-widget.vbs - silent launcher for the fat fish desktop widget.
' Started by the Host half (index.js) when DSH opens; it also works when double
' clicked by hand. WScript.Shell.Run keeps the widget out of the Host's job
' object, so the fish stays on the desktop after DSH is closed.
Option Explicit
On Error Resume Next

Dim fso, shell, scriptDir, widgetPath, psPath, args
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
widgetPath = fso.BuildPath(scriptDir, "FatFishDesktop.ps1")

' Windows PowerShell 5.1 is present on every Windows install; the widget script
' stays ASCII-only so no code-page issue can break it.
psPath = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"

If fso.FileExists(widgetPath) Then
    args = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & widgetPath & """"
    shell.Run """" & psPath & """ " & args, 0, False
End If
