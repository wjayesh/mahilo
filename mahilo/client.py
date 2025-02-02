import asyncio
import rich
import websockets
from typing import Optional
import base64
import json
import threading

# Optional import for voice features
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

class Client:
    def __init__(self, url: str, agent_name: Optional[str] = None, voice: bool = False):
        self.base_url = url
        self.agent_name = agent_name
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.voice = voice
        self.audio = None
        self.stream = None
        self.is_recording = False
        self.stop_recording = threading.Event()
        
        if self.voice:
            if not PYAUDIO_AVAILABLE:
                raise ImportError("PyAudio is required for voice features. Learn how to install it for your OS here: https://pypi.org/project/PyAudio/.")
            self.audio = pyaudio.PyAudio()
            
            # Add device check
            try:
                default_input = self.audio.get_default_input_device_info()
            except OSError:
                raise RuntimeError("No audio input device found. Check your microphone configuration.")

    async def connect(self):
        if self.voice:
            websocket_url = f"ws://{self.base_url.split('://')[-1]}/ws/voice-stream/{self.agent_name}"
        else:
            websocket_url = f"ws://{self.base_url.split('://')[-1]}/ws/{self.agent_name or 'main'}"
        print(f"Connecting to {websocket_url}")
        self.websocket = await websockets.connect(websocket_url)
        asyncio.create_task(self._listen())

    async def _listen(self):
        try:
            while True:
                message = await self.websocket.recv()
                if self.voice:
                    # Handle non-JSON system messages
                    if not message.startswith('{'):
                        rich.print(f"[bold blue]mahilo:[/bold blue] {message}")
                        continue
                    
                    data = json.loads(message)
                    if data['event'] == 'media':
                        audio_data = base64.b64decode(data['media']['payload'])
                        rich.print(f"[bold green]🎵  Received audio data[/bold green] ([italic]{len(audio_data)} bytes[/italic])")
                        self._play_audio(audio_data)
                    else:
                        rich.print(f"[bold magenta]{self.agent_name or 'Agent'}:[/bold magenta] {message}")
                else:
                    rich.print(f"[bold magenta]{self.agent_name or 'Agent'}:[/bold magenta] {message}")
        except websockets.ConnectionClosed:
            rich.print(f"[bold red]⚠️  Connection to {self.agent_name} closed[/bold red]")

    async def send_message(self, message: str):
        if self.websocket:
            if self.voice:
                # Start recording task if not already recording
                if not self.is_recording:
                    asyncio.create_task(self._record_and_send_audio())
            else:
                await self.websocket.send(json.dumps(message))
        else:
            raise Exception("WebSocket connection not established")

    async def _record_and_send_audio(self):
        if not self.voice:
            raise RuntimeError("Voice features are not enabled. Initialize the client with voice=True to use voice features.")
        
        print("Recording started... (press Ctrl+C to stop recording)")
        self.is_recording = True
        loop = asyncio.get_event_loop()
        
        # Open stream in a thread-safe way
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
            start=False
        )
        self.stream.start_stream()
        
        try:
            while True:
                # Run blocking read in executor
                data = await loop.run_in_executor(
                    None, 
                    self.stream.read, 
                    1024,
                    False  # Non-blocking read (though actual non-blocking needs special handling)
                )
                audio_payload = base64.b64encode(data).decode('utf-8')
                await self.websocket.send(json.dumps({
                    "event": "media",
                    "media": {
                        "payload": audio_payload
                    }
                }))
        except asyncio.CancelledError:
            print("Recording task cancelled")
        except Exception as e:
            print("Recording error:", e)
        finally:
            self.is_recording = False
            self.stream.stop_stream()
            self.stream.close()
            print("Recording stopped.")

    def _play_audio(self, audio_data):
        if not self.voice:
            raise RuntimeError("Voice features are not enabled. Initialize the client with voice=True to use voice features.")
            
        stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=8050, output=True)
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()

    async def close(self):
        if self.websocket:
            await self.websocket.close()
        if self.audio:
            self.audio.terminate()