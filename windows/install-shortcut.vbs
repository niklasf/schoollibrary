Dim Shell, Shortcut, Fso
Set Shell = CreateObject("WScript.Shell")
Set Fso = CreateObject("Scripting.FileSystemObject")
Set Shortcut = Shell.CreateShortcut(Shell.SpecialFolders("Desktop") & "\Schulbibliothek.lnk")
Shortcut.TargetPath = "C:\Python27\pythonw.exe"
Shortcut.WorkingDirectory = Fso.GetAbsolutePathName("..")
Shortcut.IconLocation = Fso.GetAbsolutePathName("..\usr\share\schoollibrary\schoollibrary.ico")
Shortcut.Arguments = """" & Fso.GetAbsolutePathName("..\schoollibrary-client") & """"
Shortcut.Save
