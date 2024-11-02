import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import sounddevice as sd
import numpy as np
import threading
import os
import google.generativeai as genai
from scipy.io.wavfile import write
import queue
import time

# API key for the Google Cloud Speech-to-Text API
api_key = "YOUR_API_KEY"
if api_key is None:
    raise ValueError("API key is not set.")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-1.5-flash")


class GeminiAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def transcribe_audio(self, audio_path):
        prompt = "transcribe the content"
        audio_file = genai.upload_file(path=audio_path)
        response = model.generate_content([prompt, audio_file])
        genai.delete_file(audio_file.name)
        return response.text
    
    def summarize_text(self, audio_path):
        prompt = "Summarize the text, make a point list with the value of the point. Example: '1: WHO'S SPEAKING: A MALE 2: WHAT IS BEING SAID: ..." \
             "TIME: ... WHERE: ... ACTION: ... PRIORITY: ...' For priority, only provide a number between 1 and 10, where 1 is the highest priority. " \
             "If any point is not present, write 'can't understand'. Predict the priority based on the urgency of the situation."
    
        # Upload audio file and get response
        audio_file = genai.upload_file(path=audio_path)
        response = model.generate_content([prompt, audio_file])
    
    # Split the response into lines
        response_total = response.text.split('\n')
        print("Response Total:", response_total)  # Debug: Verifica il contenuto di response_total

    # Initialize data dictionary with default "Can't understand" values
        data = {
            'who': "Can't understand",
            'what': "Can't understand",
            'when': "Can't understand",
            'where': "Can't understand",
            'action_priority': "Can't understand",
        }
    
        # Iterate over each line in the response
        for line in response_total:
            # Pulisce gli asterischi e spazi indesiderati
            clean_line = line.replace("**", "").strip()
            print("Processing line:", clean_line)  # Debug: Verifica ogni linea

        # Verifica se la linea contiene il separatore ": " prima di effettuare split
            if ": " in clean_line:
                # Divide la linea in nome campo e valore
                field, value = clean_line.split(": ", 1)
                field = field.lower()

                # Controlla il campo e aggiorna `data` di conseguenza
                if "who's speaking" in field:
                    data['who'] = value.strip()
                elif "what is being said" in field:
                    data['what'] = value.strip()
                elif "time" in field:
                    data['when'] = value.strip()
                elif "where" in field:
                    data['where'] = value.strip()
                elif "action" in field or "priority" in field:
                    data['action_priority'] = value.strip()

    # Delete audio file after processing
        genai.delete_file(audio_file.name)

    # Extract priority separately
        priority_prompt = "Write only the priority value."
        priority_response = model.generate_content([priority_prompt, response.text])
        priority_value = priority_response.text.strip()
    
        print("Data Extracted:", data)  # Debug: Verifica il contenuto di data
        print("Priority Value:", priority_value)  # Debug: Verifica il valore della priorità

        return data, priority_value





class EmergencyCallApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Echoes - Emergency Call Management")
        self.geometry("1000x800")
        self.configure(bg="#1c1c1c")

        # Canvas con scrollbar
        self.canvas = tk.Canvas(self, bg="#1c1c1c", width=1000)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1c1c1c")

        # Centra gli elementi all'interno di un frame intermedio
        self.center_frame = tk.Frame(self.scrollable_frame, bg="#1c1c1c")
        self.center_frame.grid_columnconfigure(0, weight=1)

        # Configura scrollbar e canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=950)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Chiamata al metodo di creazione dell'interfaccia
        self.create_interface()
        self.is_recording = False
        self.fs = 44100  # Sampling frequency
        self.recording_time = 10  # Recording duration in seconds
        self.gemini_client = GeminiAPIClient(api_key=api_key)

        # Variable for handling the recording thread
        self.recording_thread = None
        self.countdown_thread = None

        # Queue to communicate between threads
        self.queue = queue.Queue()

        # Start the callback handling thread
        self.after(100, self.process_queue)

    def create_interface(self):
        title_label = tk.Label(self.center_frame, text="Echoes - Emergency Call Management", font=("Helvetica", 18, "bold"), bg="#1c1c1c", fg="#ff6b6b")
        title_label.pack(pady=5)

        self.call_status_label = tk.Label(self.center_frame, text="Call Status: Waiting...", font=("Helvetica", 12), bg="#1c1c1c", fg="#ffffff")
        self.call_status_label.pack(pady=5)

        transcription_label = tk.Label(self.center_frame, text="Real-Time Transcription:", font=("Helvetica", 16, "bold"), bg="#1c1c1c", fg="#ffffff")
        transcription_label.pack(pady=5)
        self.transcription_text = scrolledtext.ScrolledText(self.center_frame, height=10, width=80, bg="#2d2d2d", fg="#ffffff", font=("Helvetica", 12), relief="flat", borderwidth=0, padx=10, pady=10)
        self.transcription_text.pack(pady=5)

        # Bottoni subito sotto il campo di trascrizione
        self.forward_button = tk.Button(self.center_frame, text="Forward Call", command=self.forward_call, bg="#2d2d2d", fg="#ffffff", font=("Helvetica", 14, "bold"), relief="flat", activebackground="#2d2d2d", activeforeground="#ffffff", borderwidth=0, padx=20, pady=10)
        self.forward_button.pack(pady=5)

        self.record_button = tk.Button(self.center_frame, text="Start Recording", command=self.toggle_recording, bg="#ff6b6b", fg="#ffffff", font=("Helvetica", 14, "bold"), relief="flat", activebackground="#ff6b6b", activeforeground="#ffffff", borderwidth=0, padx=20, pady=10)
        self.record_button.pack(pady=5)

        self.countdown_label = tk.Label(self.center_frame, text="", font=("Helvetica", 12), bg="#1c1c1c", fg="#ff6b6b")
        self.countdown_label.pack(pady=5)

        summary_label = tk.Label(self.center_frame, text="Automatic Summary:", font=("Helvetica", 12, "bold"), bg="#1c1c1c", fg="#ffffff")
        summary_label.pack(pady=5)

        fields = [("Who's Speaking:", "who_text"),
                  ("What's Being Said:", "what_text"),
                  ("When (Time):", "when_text"),
                  ("Where:", "where_text"),
                  ("Action & Priority:", "action_priority_text")]

        for label_text, var_name in fields:
            label = tk.Label(self.center_frame, text=label_text, font=("Helvetica", 14), bg="#1c1c1c", fg="#ffffff")
            label.pack(pady=5)
            text_box = tk.Text(self.center_frame, height=1, width=80, bg="#2d2d2d", fg="#ffffff", font=("Helvetica", 12), relief="flat", borderwidth=0, padx=10, pady=10)
            text_box.pack(pady=5)
            setattr(self, var_name, text_box)

        priority_label = tk.Label(self.center_frame, text="Assigned Priority:", font=("Helvetica", 16), bg="#1c1c1c", fg="#ffffff")
        priority_label.pack(pady=10)
        self.priority_value = tk.Label(self.center_frame, text="Not Assigned", font=("Helvetica", 18, "bold"), bg="#1c1c1c", fg="#ff6b6b")
        self.priority_value.pack(pady=10)

        # Aggiunge il frame centrato alla finestra scrollabile
        self.center_frame.pack(pady=20)

    def forward_call(self):
        self.call_status_label.config(text="Call Status: Forwarded", fg="#ff6b6b")
        print("Call forwarded to the specific dispatcher.")

    def toggle_recording(self):
        if self.record_button.cget("text") == "Start Recording":
            self.record_button.config(text="Stop Recording", bg="#ff6b6b")
        else:
            self.record_button.config(text="Start Recording", bg="#ff6b6b")
        self.transcription_text.delete(1.0, tk.END)
        self.who_text.delete(1.0, tk.END)
        self.what_text.delete(1.0, tk.END)
        self.when_text.delete(1.0, tk.END)
        self.where_text.delete(1.0, tk.END)
        self.action_priority_text.delete(1.0, tk.END)

        if not self.is_recording:
            self.is_recording = True
            self.record_button.config(text=f"Recording: {self.recording_time} sec")
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()

            self.countdown_thread = threading.Thread(target=self.countdown_timer)
            self.countdown_thread.start()
        else:
            self.is_recording = False
            self.record_button.config(text="Start Recording")
            if self.recording_thread:
                self.recording_thread.join()
            if self.countdown_thread:
                self.countdown_thread.join()

    def countdown_timer(self):
        remaining_time = self.recording_time
        while remaining_time > 0 and self.is_recording:
            self.record_button.config(text=f"Recording: {remaining_time} sec")
            time.sleep(1)
            remaining_time -= 1
        if self.is_recording:
            self.record_button.config(text="Recording finished")

    def record_audio(self):
        audio_path = "audio.wav"
        recording = sd.rec(int(self.recording_time * self.fs), samplerate=self.fs, channels=1)
        sd.wait()
        write(audio_path, self.fs, recording)
        self.queue.put(('transcribe', audio_path))
    
    def process_queue(self):
        while not self.queue.empty():
            task, audio_path = self.queue.get()

            if task == 'transcribe':
                transcription = self.gemini_client.transcribe_audio(audio_path)
                if transcription:
                    self.update_transcription_text(transcription)
                    self.queue.put(('summarize', audio_path))
                else:
                    print("Transcription failed.")
            elif task == 'summarize':
                summary_data, priority = self.gemini_client.summarize_text(audio_path)
                if summary_data:
                    self.update_summary_fields(summary_data)
                    self.queue.put(('update_priority', priority))
                else:
                    print("Summary failed.")
            elif task == 'update_priority':
                priority_value = audio_path
                self.update_priority_value(priority_value)

        self.after(100, self.process_queue)

    def update_priority_value(self, priority_value):
        self.priority_value.config(text=f"Priority: {priority_value}")

    def on_closing(self):
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()
        if self.countdown_thread:
            self.countdown_thread.join()
        self.destroy()

    def update_transcription_text(self, transcription):
        self.transcription_text.insert(tk.END, f"{transcription}\n")
        self.transcription_text.see(tk.END)

    def update_summary_fields(self, data):
        self.who_text.insert(tk.END, data['who'])
        self.what_text.insert(tk.END, data['what'])
        self.when_text.insert(tk.END, data['when'])
        self.where_text.insert(tk.END, data['where'])
        self.action_priority_text.insert(tk.END, data['action_priority'])
        current_time = time.strftime("%Y%m%d_%H%M%S")
        file_name = f"EMERGENCY{self.priority_value}_{current_time}.txt"
        with open(file_name, "w") as file:
            file.write("Summary of the Emergency Call:\n")
            file.write(f"Who's Speaking: {data['who']}\n")
            file.write(f"What's Being Said: {data['what']}\n")
            file.write(f"When (Time): {data['when']}\n")
            file.write(f"Where: {data['where']}\n")
            file.write(f"Action & Priority: {data['action_priority']}\n")
            file.write(f"Assigned Priority: {self.priority_value}\n")


if __name__ == "__main__":
    app = EmergencyCallApp()
    app.mainloop()
