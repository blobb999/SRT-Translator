import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from googletrans import Translator, LANGUAGES
import re
import threading
import time
import math

# Improved language display
LANGUAGE_DISPLAY = {code: f"{name} ({code})" for code, name in LANGUAGES.items()}

# Globals for timing and control
start_time = None
estimated_total_time = 0
stop_translation = False
translated_blocks = []


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def load_srt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise Exception("SRT file not found.")
    except UnicodeDecodeError:
        raise Exception("Unable to decode file. Ensure it is UTF-8 encoded.")

def save_srt(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        raise Exception(f"Failed to save file: {str(e)}")

def detect_language(text):
    translator = Translator()
    detection = translator.detect(text)
    return detection.lang

def translate_srt(content, dest_language, progress_callback=None):
    global start_time, estimated_total_time, stop_translation, translated_blocks
    translator = Translator()
    blocks = re.split(r'\n\n', content.strip())
    translated_blocks = []
    total_blocks = len(blocks)

    # Detect source language
    source_sample = "\n\n".join(blocks[:5])
    source_language = detect_language(source_sample)
    detected_language_var.set(f"Detected source language: {LANGUAGES.get(source_language, source_language).capitalize()} ({source_language})")

    start_time = time.time()

    for idx, block in enumerate(blocks):
        if stop_translation:
            break

        lines = block.split('\n')
        if len(lines) < 2:
            translated_blocks.append(block)
            continue

        number = lines[0]
        timestamp = lines[1]
        text_lines = lines[2:] if len(lines) > 2 else []
        text = '\n'.join(text_lines)

        if text.strip():
            try:
                translation = translator.translate(text, src=source_language, dest=dest_language)
                translated_text = translation.text
                translated_lines = translated_text.split('\n') if '\n' in translated_text else [translated_text]
                if len(translated_lines) < len(text_lines):
                    translated_lines += [''] * (len(text_lines) - len(translated_lines))
                elif len(translated_lines) > len(text_lines):
                    translated_lines = [''.join(translated_lines)]
            except Exception:
                translated_lines = ["[Translation Error]"] + [''] * (len(text_lines) - 1)
        else:
            translated_lines = text_lines

        translated_block = '\n'.join([number, timestamp] + translated_lines)
        translated_blocks.append(translated_block)

        if progress_callback:
            progress_callback(idx + 1, total_blocks)
            time.sleep(0.1)

    return '\n\n'.join(translated_blocks)

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
    if file_path:
        entry_file_path.delete(0, tk.END)
        entry_file_path.insert(0, file_path)

def start_translation():
    global stop_translation
    stop_translation = False
    file_path = entry_file_path.get()
    target_language = language_var.get().split('(')[-1].strip(')')

    if not file_path:
        messagebox.showerror("Error", "Please select an SRT file.")
        return
    if not target_language:
        messagebox.showerror("Error", "Please select a target language.")
        return
    if button_translate["state"] == "disabled":
        messagebox.showwarning("Warning", "Translation already in progress.")
        return

    button_translate["state"] = "disabled"
    button_stop["state"] = "normal"

    def translate_thread():
        try:
            content = load_srt(file_path)
            translated_content = translate_srt(content, target_language, update_progress)
            save_path = filedialog.asksaveasfilename(
                defaultextension=".srt", filetypes=[("SRT files", "*.srt")]
            )
            if save_path:
                save_srt(save_path, '\n\n'.join(translated_blocks))
                messagebox.showinfo("Success", f"Translation saved to {save_path}")
            else:
                messagebox.showinfo("Info", "Translation cancelled.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            button_translate["state"] = "normal"
            button_stop["state"] = "disabled"
            progress_var.set(0)
            progress_label.config(text="Progress: 0%")
            eta_label.config(text="ETA: 0s")

    threading.Thread(target=translate_thread, daemon=True).start()

def stop_translation_action():
    global stop_translation
    stop_translation = True

def update_progress(current, total):
    global start_time
    percent = int((current / total) * 100)
    progress_var.set(percent)
    elapsed_time = time.time() - start_time
    eta = (elapsed_time / current) * (total - current) if current > 0 else 0
    eta_label.config(text=f"ETA: {math.ceil(eta)}s")
    progress_label.config(text=f"Progress: {percent}% ({current}/{total})")
    root.update_idletasks()

# GUI setup
root = tk.Tk()
root.title("SRT Translator")
root.iconbitmap(resource_path("SRT-Translator.ico"))
root.configure(bg="#2e2e2e")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TCombobox", fieldbackground="#1e1e1e", background="#1e1e1e", foreground="white")
style.configure("TProgressbar", background="#28a745", troughcolor="#1e1e1e")

frame = tk.Frame(root, padx=10, pady=10, bg="#2e2e2e")
frame.pack(fill=tk.BOTH, expand=True)

label_file = tk.Label(frame, text="SRT File:", fg="white", bg="#2e2e2e")
label_file.grid(row=0, column=0, sticky=tk.W)

entry_file_path = tk.Entry(frame, width=50, bg="#1e1e1e", fg="white", insertbackground='white')
entry_file_path.grid(row=0, column=1, padx=5)

button_browse = tk.Button(frame, text="Browse", command=select_file, bg="#007acc", fg="white", relief=tk.FLAT)
button_browse.grid(row=0, column=2)

label_language = tk.Label(frame, text="Target Language:", fg="white", bg="#2e2e2e")
label_language.grid(row=1, column=0, sticky=tk.W)

language_var = tk.StringVar()
language_dropdown = ttk.Combobox(frame, textvariable=language_var, values=list(LANGUAGE_DISPLAY.values()), state="readonly")
language_dropdown.grid(row=1, column=1, sticky=tk.W, padx=5)
language_dropdown.set("Select a language")

detected_language_var = tk.StringVar()
detected_language_label = tk.Label(frame, textvariable=detected_language_var, fg="white", bg="#2e2e2e")
detected_language_label.grid(row=2, column=0, columnspan=3, pady=(5,0))

button_translate = tk.Button(frame, text="Translate", command=start_translation, bg="#28a745", fg="white", relief=tk.FLAT)
button_translate.grid(row=3, column=0, columnspan=2, pady=10)

button_stop = tk.Button(frame, text="Stop", command=stop_translation_action, bg="#dc3545", fg="white", relief=tk.FLAT, state="disabled")
button_stop.grid(row=3, column=2, pady=10)

progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100, length=400)
progress_bar.grid(row=4, column=0, columnspan=3, pady=5)

progress_label = tk.Label(frame, text="Progress: 0%", fg="white", bg="#2e2e2e")
progress_label.grid(row=5, column=0, columnspan=3)

eta_label = tk.Label(frame, text="ETA: 0s", fg="white", bg="#2e2e2e")
eta_label.grid(row=6, column=0, columnspan=3)

root.mainloop()
