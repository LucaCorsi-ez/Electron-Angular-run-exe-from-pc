import time
import win32con
import win32gui
import pygetwindow as gw
import ctypes
import pyautogui
import threading
import sys
import os
import psutil
from screeninfo import get_monitors
import subprocess
import logging
import mss  # Libreria per la cattura dello schermo
import numpy as np
import cv2

# Imposta il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dimensioni della finestra di streaming
STREAM_WIDTH, STREAM_HEIGHT = 1536, 1536

# Variabili globali per il processo e la finestra di streaming
app_process = None
stream_thread = None
streaming_active = threading.Event()

def start_application():
    try:
        logging.info("Avvio dell'applicazione...")

        # Ottieni la directory corrente del file Python
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Costruisci il percorso relativo all'eseguibile
        exe_path = os.path.join(base_dir, 'programmi', 'v84', 'OLO_v84.exe')

        # Avvia l'applicazione
        return subprocess.Popen([exe_path])
    except Exception as e:
        logging.error(f"Errore durante l'avvio dell'applicazione: {str(e)}")
        sys.exit(1)


def find_window(title):
    windows = gw.getWindowsWithTitle(title)
    if windows:
        logging.info(f"Finestra trovata: {windows[0].title}")
        return windows[0]
    logging.warning(f"Finestra '{title}' non trovata.")
    return None

def move_window_to_position(window, x, y, width, height):
    try:
        hwnd = win32gui.FindWindow(None, window.title)
        if hwnd == 0:
            raise ValueError(f"Finestra '{window.title}' non trovata.")
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        logging.info(f"Finestra '{window.title}' spostata a ({x}, {y}) di dimensioni {width}x{height}.")
    except Exception as e:
        logging.error(f"Errore durante lo spostamento della finestra: {str(e)}")

def remove_frame(hwnd):
    try:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, win32con.GWL_STYLE)
        style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_SYSMENU)
        ctypes.windll.user32.SetWindowLongW(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)
    except Exception as e:
        logging.error(f"Errore durante la rimozione dei bordi: {str(e)}")

def set_window_topmost(hwnd):
    try:
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception as e:
        logging.error(f"Errore durante l'impostazione della finestra in primo piano: {str(e)}")

def is_fullscreen(hwnd):
    try:
        # Ottiene le dimensioni dello schermo principale
        screen = get_monitors()[0]
        rect = win32gui.GetWindowRect(hwnd)
        
        # Verifica se le dimensioni della finestra corrispondono a quelle dello schermo
        return (rect[0] == screen.x and rect[1] == screen.y and 
                rect[2] == screen.width and rect[3] == screen.height)
    except Exception as e:
        logging.error(f"Errore durante il controllo dello stato fullscreen: {str(e)}")
        return False        

def toggle_fullscreen_with_f11(hwnd, enable=True):
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.01)
        pyautogui.press('f11')
        time.sleep(0.01)
        action = "ripristino" if enable else "uscita"
        logging.info(f"Modalità fullscreen {action} con successo.")
    except Exception as e:
        logging.error(f"Errore durante il toggle della modalità fullscreen: {str(e)}")

def monitor_olo_window(hwnd_interactive):
    global streaming_active
    while not streaming_active.is_set():
        time.sleep(0.1)  # Ridotto il tempo di attesa per migliorare la reattività
        if app_process.poll() is not None:
            logging.info("L'applicazione OLO_v84 è stata chiusa.")
            streaming_active.set()
            terminate_stream()
            toggle_fullscreen_with_f11(hwnd_interactive, enable=True)
            time.sleep(0.1)
            check_and_restore_fullscreen(hwnd_interactive)
            logging.info("Ripristinata la modalità fullscreen di Interactive.")

            # Porta la finestra di Interactive in primo piano
            win32gui.SetForegroundWindow(hwnd_interactive)
            logging.info("Finestra 'Interactive' messa in primo piano.")

            terminate_script()
            break

        

def check_and_restore_fullscreen(hwnd_interactive):
    rect = win32gui.GetWindowRect(hwnd_interactive)
    screen = get_monitors()[0]

    if rect != (screen.x, screen.y, screen.width, screen.height):
        logging.info("La finestra 'Interactive' non è a schermo intero. Forzando la modalità fullscreen.")
        toggle_fullscreen_with_f11(hwnd_interactive, enable=True)
    else:
        logging.info("La finestra 'Interactive' è correttamente a schermo intero.")

def terminate_script():
    logging.info("Terminazione dello script.")
    current_process = psutil.Process(os.getpid())
    current_process.terminate()

def terminate_stream():
    global stream_thread
    if stream_thread and stream_thread.is_alive():
        logging.info("Terminazione dello streaming.")
        streaming_active.set()  # Forza l'uscita immediata dallo streaming
        stream_thread.join()    # Assicura che il thread di streaming sia terminato
    cv2.destroyAllWindows()

    # Forza la chiusura della finestra residua
    hwnd_stream = win32gui.FindWindow(None, "Stream")
    if hwnd_stream != 0:
        win32gui.PostMessage(hwnd_stream, win32con.WM_CLOSE, 0, 0)
        logging.info("Finestra di streaming forzata a chiudersi.")
    else:
        logging.info("Nessuna finestra di streaming da chiudere.")

def capture_stream(olo_window):
    cv2.namedWindow("Stream", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Stream", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    hwnd = win32gui.FindWindow(None, olo_window.title)
    if hwnd == 0:
        raise ValueError(f"Finestra '{olo_window.title}' non trovata.")

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    capture_width = right - left
    capture_height = bottom - top

    # Valore di ritaglio in altezza (modifica qui per cambiare la porzione tagliata)
    height_to_crop = 10  # Pixel da tagliare (puoi regolare questo valore)

    # Calcolo delle nuove dimensioni dell'area da catturare
    capture_height -= height_to_crop

    screen = get_monitors()[1]  # Indice del secondo monitor
    x_offset = screen.x + (screen.width - STREAM_WIDTH) // 2
    y_offset = screen.y + (screen.height - STREAM_HEIGHT) // 2

    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": capture_width, "height": capture_height}

        while not streaming_active.is_set():
            img = sct.grab(monitor)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # Selezione della porzione da ritagliare
            frame = frame[:-height_to_crop, :]  # Ritaglia dall'alto (puoi regolare questa parte)

            # Ridimensiona il frame per adattarlo alla finestra di streaming
            resized_frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT))

            cv2.imshow('Stream', resized_frame)

            hwnd_stream = win32gui.FindWindow(None, "Stream")
            if hwnd_stream != 0:
                remove_frame(hwnd_stream)
                win32gui.MoveWindow(hwnd_stream, x_offset, y_offset, STREAM_WIDTH, STREAM_HEIGHT, True)
                set_window_topmost(hwnd_stream)

            if cv2.getWindowProperty('Stream', cv2.WND_PROP_VISIBLE) < 1:
                break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                streaming_active.set()  # Interrompe immediatamente lo streaming
                break

    cv2.destroyAllWindows()
    logging.info("Finestra di streaming chiusa correttamente.")

    # Forza la chiusura della finestra residua
    hwnd_stream = win32gui.FindWindow(None, "Stream")
    if hwnd_stream != 0:
        win32gui.PostMessage(hwnd_stream, win32con.WM_CLOSE, 0, 0)
        logging.info("Finestra di streaming forzata a chiudersi.")
    else:
        logging.info("Nessuna finestra di streaming da chiudere.")

def main():
    global app_process, stream_thread

    try:
        monitors = get_monitors()
        if len(monitors) < 2:
            logging.warning("Il secondo monitor non è disponibile.")
            return

        main_screen, second_screen = monitors[0], monitors[1]

        interactive_window = find_window('Emedia')
        if interactive_window:
            hwnd_interactive = win32gui.FindWindow(None, interactive_window.title)
            #set_window_topmost(hwnd_interactive)
            app_process = start_application()
            time.sleep(2)  # Attendi per dare tempo all'applicazione di avviarsi completamente
            toggle_fullscreen_with_f11(hwnd_interactive, enable=False)
            move_window_to_position(interactive_window, main_screen.x, main_screen.y, main_screen.width // 2, main_screen.height)
            remove_frame(hwnd_interactive)
            if is_fullscreen(hwnd_interactive):
                 logging.info("La finestra 'Emedia' è in modalità fullscreen, forzando l'uscita.")
                 toggle_fullscreen_with_f11(hwnd_interactive, enable=False)
                 move_window_to_position(interactive_window, main_screen.x, main_screen.y, main_screen.width // 2, main_screen.height)
  
            
            monitor_thread = threading.Thread(target=monitor_olo_window, args=(hwnd_interactive,))
            monitor_thread.start()
        else:
            logging.warning("Finestra Interactive non trovata, lo streaming sarà avviato comunque.")

        olo_window = find_window('OLO_v84 (64-bit Development PCD3D_SM6)')
        if olo_window:
            move_window_to_position(olo_window, main_screen.x + main_screen.width // 2, main_screen.y, main_screen.width // 2, main_screen.height)
            hwnd_olo = win32gui.FindWindow(None, olo_window.title)
            #set_window_topmost(hwnd_olo)
            remove_frame(hwnd_olo)
        else:
            logging.error("Finestra OLO_v84 non trovata.")
            return

        streaming_active.clear()
        stream_thread = threading.Thread(target=capture_stream, args=(olo_window,))
        stream_thread.start()

    except Exception as e:
        logging.error(f"Errore durante l'esecuzione: {str(e)}")

if __name__ == "__main__":
    main()