# Echoes: Securing Tomorrow. Today

**Echoes** is an AI-powered emergency call management system designed to transcribe, summarize, prioritize, and route emergency and customer service calls. By leveraging advanced AI technologies, Echoes helps reduce response times, eliminate communication errors, and streamline the call handling process across a range of industries, including emergency services, telecommunications, and customer support.

## Features
- **Real-time audio transcription** using the Gemini API.
- **Automatic call summarization**, including key details such as identity, location, situation, and urgency.
- **Priority assignment system**, ranking calls from 1 (highest) to 10 (lowest priority).
- **Call routing** based on priority, ensuring that the most urgent calls reach the appropriate department quickly.
- **User-friendly GUI** built with Tkinter, providing an intuitive and streamlined experience for operators.

## Problem Statement
Traditional call centers often face inefficiencies, especially when handling a high volume of calls. In emergency situations, even small delays can result in critical outcomes. Echoes addresses these issues by automating the transcription, summarization, and prioritization process, reducing manual tasks and improving the accuracy and speed of call handling.

## How It Works
1. **Audio Recording**: The system records incoming calls via the user’s microphone using the `sounddevice` library.
2. **Transcription**: The recorded audio is sent to the Gemini API, which transcribes the content in real time.
3. **Summarization**: The transcribed content is then summarized, highlighting key points such as caller identity, the nature of the incident, location, and required actions.
4. **Priority Assignment**: The system assigns a priority score to each call based on the urgency, allowing the most critical calls to be routed immediately.
5. **Call Forwarding**: Depending on the assigned priority, the call is forwarded to the relevant emergency response team or department.

## Technologies Used
- **Python**: Core programming language.
- **Tkinter**: Used for building the graphical user interface (GUI).
- **Gemini API**: For audio transcription and summarization.
- **Sounddevice**: Library for recording audio from the user’s microphone.
- **Multithreading**: Used to ensure responsive interaction while handling background tasks (e.g., recording, transcription).

## Getting Started

### Prerequisites
- Python 3.6 or higher.
- Gemini API key for transcription and summarization services.
- Dependencies installed (use `pip`):
  ```bash
  pip install sounddevice tkinter
