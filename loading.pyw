from PIL import Image, ImageTk
import tkinter as tk

def fade_in(window, alpha=0.0, increment=0.05):
    if alpha < 1.0:
        window.attributes("-alpha", alpha)
        window.after(10, fade_in, window, alpha + increment)
    else:
        window.attributes("-alpha", 1.0)

def fade_out(window, alpha=1.0, decrement=0.05):
    if alpha > 0.0:
        window.attributes("-alpha", alpha)
        window.after(20, fade_out, window, alpha - decrement)
    else:
        window.destroy()

def show_overlay_image(image_path, duration=2):
    root = tk.Tk()
    root.title("Overlay Image")
    root.attributes('-topmost', True)
    root.overrideredirect(True)  # Rimuove i bordi della finestra
    root.attributes("-alpha", 0.0)  # Imposta l'inizio come completamente trasparente

    # Ottieni la risoluzione dello schermo
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Carica e ridimensiona l'immagine per adattarla alla risoluzione dello schermo
    img = Image.open(image_path)
    img = img.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
    tk_image = ImageTk.PhotoImage(img)

    # Aggiungi l'immagine alla finestra
    label = tk.Label(root, image=tk_image)
    label.image = tk_image  # Mantieni una referenza all'immagine per evitare che venga garbage collected
    label.pack()

    # Imposta la finestra a schermo intero
    root.geometry(f'{screen_width}x{screen_height}+0+0')

    # Effettua la dissolvenza in entrata
    fade_in(root)

    # Effettua la dissolvenza in uscita dopo la durata specificata
    root.after(duration * 5000, fade_out, root)

    root.mainloop()

# Path all'immagine
image_path = r"C:\\Users\\Utente\\Desktop\\source\\noprompt\\black.png"
show_overlay_image(image_path)
