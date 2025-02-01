import asyncio
import click
from .client import Client

@click.group()
def cli():
    """Command line interface for mahilo."""
    pass

@cli.command()
@click.option('--url', default='http://localhost:8000', help='Server URL')
@click.option('--agent-name', required=True, help='Name of the agent to connect to')
@click.option('--voice', is_flag=True, help='Enable voice', default=False)
def connect(url: str, agent_name: str, voice: bool):
    """Connect to a mahilo server."""
    client = Client(url, agent_name, voice)
    asyncio.run(run_client(client))

async def run_client(client: Client):
    await client.connect()
    while True:
        if client.voice:
            if not client.is_recording:
                print("Press Enter to start recording...")
                await asyncio.get_event_loop().run_in_executor(None, input)
                await client.send_message("")  # This will trigger audio recording
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        else:
            message = await asyncio.get_event_loop().run_in_executor(
                None, 
                input,
                f"Enter message for {client.agent_name or 'main agent'} (or 'quit' to exit): "
            )
            if message.lower() == 'quit':
                break
            await client.send_message(message)
    await client.close()

if __name__ == "__main__":
    cli() 