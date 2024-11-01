import asyncio
import click
import rich
import websockets
from typing import Optional
import pyaudio
import base64
import json
import threading

class Client:
    def __init__(self, url: str, agent_type: Optional[str] = None, voice: bool = False):
        self.base_url = url
        self.agent_type = agent_type
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.stop_recording = threading.Event()
        self.voice = voice

    async def connect(self):
        if self.voice:
            websocket_url = f"ws://{self.base_url.split('://')[-1]}/ws/voice-stream/{self.agent_type}"
        else:
            websocket_url = f"ws://{self.base_url.split('://')[-1]}/ws/{self.agent_type or 'main'}"
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
                        rich.print(f"[bold magenta]{self.agent_type or 'Agent'}:[/bold magenta] {message}")
                else:
                    rich.print(f"[bold magenta]{self.agent_type or 'Agent'}:[/bold magenta] {message}")
        except websockets.ConnectionClosed:
            rich.print(f"[bold red]⚠️  Connection to {self.agent_type} closed[/bold red]")

    async def send_message(self, message: str):
        if self.websocket:
            if self.voice:
                await self._record_and_send_audio()
            else:
                await self.websocket.send(json.dumps(message))
        else:
            raise Exception("WebSocket connection not established")

    async def _record_and_send_audio(self):
        print("Recording... Press Enter to stop.")
        self.is_recording = True
        self.stop_recording.clear()
        self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
        
        def input_thread():
            input()
            self.stop_recording.set()

        threading.Thread(target=input_thread, daemon=True).start()

        try:
            while not self.stop_recording.is_set():
                data = self.stream.read(1024)
                audio_payload = base64.b64encode(data).decode('utf-8')
                await self.websocket.send(json.dumps({
                    "event": "media",
                    "media": {
                        "payload": audio_payload
                    }
                }))
                await asyncio.sleep(0.01)  # Small delay to prevent flooding
        finally:
            self.is_recording = False
            self.stream.stop_stream()
            self.stream.close()
            print("Recording stopped.")

    def _play_audio(self, audio_data):
        stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()

    async def close(self):
        if self.websocket:
            await self.websocket.close()
        self.audio.terminate()

async def run_client(client: Client):
    await client.connect()
    while True:
        if client.voice:
            print("Press Enter to start recording...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            await client.send_message("")  # This will trigger audio recording
        else:
            message = await asyncio.get_event_loop().run_in_executor(
                None, 
                input,
                f"Enter message for {client.agent_type or 'main agent'} (or 'quit' to exit): "
            )
            if message.lower() == 'quit':
                break
            await client.send_message(message)
    await client.close()

@click.command()
@click.option('--url', default='http://localhost:8000', help='Server URL')
@click.option('--agent-type', required=True, help='Agent type to connect to')
@click.option('--voice', is_flag=True, help='Enable voice', default=False)
def cli(url: str, agent_type: Optional[str], voice: bool):
    """CLI for connecting to the multi-agent server."""
    client = Client(url, agent_type, voice)
    asyncio.run(run_client(client))

if __name__ == "__main__":
    cli()

# Usage example:
# asyncio.run(run_client(Client("http://localhost:8000")))
# or
# asyncio.run(run_client(Client("ws://localhost:8000", "AgentType1")))