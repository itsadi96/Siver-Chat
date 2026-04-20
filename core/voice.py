import speech_recognition as sr
import pyttsx3

class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.engine = pyttsx3.init()
    
    def listen(self):
        with self.microphone as source:
            print("Listening for command...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
        
        try:
            command = self.recognizer.recognize_google(audio)
            print(f"Recognized command: {command}")
            return command
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand the audio.")
            return ""
        except sr.RequestError:
            print("Could not request results; check your network connection.")
            return ""

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def stop_listening(self):
        print("Stopped listening.")
