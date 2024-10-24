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

# api_key = ""
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
                "TIME: ... WHERE: ... ACTION: ... PRIORITY: ...'For priority, only provide a number between 1 and 10, where 1 is the highest priority. " \
                " If any point is not present, write 'can't understand'. Predict the priority based on the urgency of the situation."
        audio_file = genai.upload_file(path=audio_path)
        response = model.generate_content([prompt, audio_file])

        response_total = response.text.split('\n')

        # Extract the first 5 relevant points
        data = {
            'who': "Can't understand",
            'what': "Can't understand",
            'when': "Can't understand",
            'where': "Can't understand",
            'action_priority': "Can't understand",
        }
        
        for line in response_total:
            if line.startswith("WHO'S SPEAKING:"):
                data['who'] = line.split(": ", 1)[1]
            elif line.startswith("WHAT IS BEING SAID:"):
                data['what'] = line.split(": ", 1)[1]
            elif line.startswith("TIME:"):
                data['when'] = line.split(": ", 1)[1]
            elif line.startswith("WHERE:"):
                data['where'] = line.split(": ", 1)[1]
            elif line.startswith("ACTION:") or line.startswith("PRIORITY:"):
                data['action_priority'] = line.split(": ", 1)[1]

        genai.delete_file(audio_file.name)

        # Extract priority separately
        priority_prompt = "Write only the priority value."
        priority_response = model.generate_content([priority_prompt, response.text])
        priority_value = priority_response.text.strip()

        return data, priority_value

class EmergencyCallApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Set the title and size of the window
        self.title("Echoes - Emergency Call Management")
        self.geometry("1000x800")

        # Define theme colors
        self.bg_color = "#1c1c1c"  # Darker background color for a modern look
        self.fg_color = "#ffffff"  # Main text color (white)
        self.accent_color = "#ff6b6b"  # Accent color (vibrant red)
        self.button_color = "#2d2d2d"  # Dark button background

        # Set the background color of the window
        self.configure(bg=self.bg_color)

        # Create the interface
        self.create_interface()

        # Variables for recording
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
        # Title of the app
        title_label = tk.Label(self, text="Echoes - Emergency Call Management", font=("Helvetica", 24, "bold"), bg=self.bg_color, fg=self.accent_color)
        title_label.pack(pady=20)

        # Call status
        self.call_status_label = tk.Label(self, text="Call Status: Waiting...", font=("Helvetica", 14), bg=self.bg_color, fg=self.fg_color)
        self.call_status_label.pack(pady=10)

        # Real-time transcription
        transcription_label = tk.Label(self, text="Real-Time Transcription:", font=("Helvetica", 18, "bold"), bg=self.bg_color, fg=self.fg_color)
        transcription_label.pack(pady=10)
        self.transcription_text = scrolledtext.ScrolledText(self, height=10, width=80, bg=self.button_color, fg=self.fg_color, font=("Helvetica", 12), relief="flat", borderwidth=0, padx=10, pady=10)
        self.transcription_text.pack(pady=10)

        # Automatic summary
        summary_label = tk.Label(self, text="Automatic Summary:", font=("Helvetica", 18, "bold"), bg=self.bg_color, fg=self.fg_color)
        summary_label.pack(pady=20)

        # Create the five summary fields
        self.create_summary_fields()

        # Assigned priority
        priority_label = tk.Label(self, text="Assigned Priority:", font=("Helvetica", 16), bg=self.bg_color, fg=self.fg_color)
        priority_label.pack(pady=10)
        self.priority_value = tk.Label(self, text="Not Assigned", font=("Helvetica", 18, "bold"), bg=self.bg_color, fg=self.accent_color)
        self.priority_value.pack(pady=10)

        # Add frame to hold the two buttons horizontally
        buttons_frame = tk.Frame(self, bg=self.bg_color)
        buttons_frame.pack(pady=20, fill=tk.X)

        # Use grid layout for precise positioning
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        # Button to forward the call on the left
        forward_button = tk.Button(buttons_frame, text="Forward Call", command=self.forward_call, bg=self.button_color, fg=self.fg_color, font=("Helvetica", 14, "bold"), relief="flat", activebackground=self.button_color, activeforeground=self.fg_color, borderwidth=0, padx=20, pady=10)
        forward_button.grid(row=0, column=0, sticky="w", padx=20)

        # Button to start recording on the right
        self.record_button = tk.Button(buttons_frame, text="Start Recording", command=self.toggle_recording, bg=self.accent_color, fg=self.fg_color, font=("Helvetica", 14, "bold"), relief="flat", activebackground=self.accent_color, activeforeground=self.fg_color, borderwidth=0, padx=20, pady=10)
        self.record_button.grid(row=0, column=1, sticky="e", padx=20)

        # Countdown label
        self.countdown_label = tk.Label(self, text="", font=("Helvetica", 14), bg=self.bg_color, fg=self.accent_color)
        self.countdown_label.pack(pady=10)

    def create_summary_fields(self):
        fields = [("Who's Speaking:", "who_text"), 
                  ("What's Being Said:", "what_text"), 
                  ("When (Time):", "when_text"), 
                  ("Where:", "where_text"), 
                  ("Action & Priority:", "action_priority_text")]

        for label_text, var_name in fields:
            label = tk.Label(self, text=label_text, font=("Helvetica", 14), bg=self.bg_color, fg=self.fg_color)
            label.pack(pady=5)
            text_box = tk.Text(self, height=1, width=80, bg=self.button_color, fg=self.fg_color, font=("Helvetica", 12), relief="flat", borderwidth=0, padx=10, pady=10)
            text_box.pack(pady=5)
            setattr(self, var_name, text_box)

    def forward_call(self):
        self.call_status_label.config(text="Call Status: Forwarded", fg=self.accent_color)
        print("Call forwarded to the specific dispatcher.")

    def toggle_recording(self):
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

# Run the application
if __name__ == "__main__":
    app = EmergencyCallApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
