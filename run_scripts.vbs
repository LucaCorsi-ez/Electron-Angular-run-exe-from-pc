Set WshShell = CreateObject("WScript.Shell")


' Esegui lo script principale
WshShell.Run "pythonw C:\Users\Utente\Desktop\source\noprompt\monitor_olo_corretto.pyw", 0

' Attendere 2 secondi
WScript.Sleep 1000

' Esegui l'immagine in overlay
WshShell.Run "pythonw C:\Users\Utente\Desktop\source\noprompt\loading.pyw", 0, True

