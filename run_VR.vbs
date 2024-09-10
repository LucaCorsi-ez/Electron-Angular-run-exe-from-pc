Set WshShell = CreateObject("WScript.Shell")



' Esegui lo script principale
WshShell.Run "pythonw monitor_olo_VR.pyw", 0

WshShell.Run "pythonw touchmainscreen.pyw", 0

' Attendere 2 secondi
WScript.Sleep 2000

' Esegui l'immagine in overlay
WshShell.Run "pythonw loading.pyw", 0, True

