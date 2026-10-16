Option Explicit
Dim shell, files, folder, command, result, q
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
q = Chr(34)
command = q & shell.ExpandEnvironmentStrings("%ComSpec%") & q & " /d /c " & q & q & folder & "\launch_staged.cmd" & q & q
If WScript.Arguments.Count > 0 Then
    If WScript.Arguments(0) = "--validate" Then
        WScript.Echo command
        WScript.Quit 0
    End If
End If
result = shell.Run(command, 0, True)
If result <> 0 Then
    MsgBox "Veil could not start. Ensure the full release is extracted and 64-bit Python 3.11 or newer with Tcl/Tk is installed. See launcher-error.txt beside this launcher.", vbExclamation, "Veil"
End If
