from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from pathlib import Path
import asyncio
from agent import run_agent
from functions import record_audio

# Initialize rich console
console = Console()

def get_audio_files():
    """Get list of audio files from data directory."""
    data_dir = Path("data")
    audio_extensions = {".mp3", ".m4a"}
    return [f for f in data_dir.iterdir() if f.suffix.lower() in audio_extensions]

def select_audio_file():
    """Display available audio files and let user select one."""
    files = get_audio_files()
    if not files:
        console.print("\nNo audio files found in data/ directory!\n", style="bold red")
        return None
        
    console.print("\nAvailable audio files:", style="bold blue")
    for i, file in enumerate(files, 1):
        console.print(f"{i}. {file.name}")
        
    choice = IntPrompt.ask("\nSelect a file number", choices=[str(i) for i in range(1, len(files) + 1)])
    return files[choice - 1]

def main():
    """Main application loop."""
    console.print("\n🎵 Welcome to the Audio Analysis Terminal!\n", style="bold blue")
    
    while True:
        # Ask user if they want to use an existing file or record a new one
        console.print("\n1. Use existing audio file\n2. Record new audio", style="bold blue")
        source_choice = Prompt.ask(
            "Choice",
            choices=["1", "2"],
            default="1"
        )
        
        selected_file = None
        
        if source_choice == "1":
            # Select existing audio file
            console.print("Using existing audio file", style="bold blue")
            selected_file = select_audio_file()
        else:
            # Record new audio
            console.print("\nRecording new audio", style="bold blue")
            
            # Ask for recording duration
            duration = IntPrompt.ask(
                "Enter recording duration in seconds",
                default=10
            )
            
            # Record audio
            console.print("\nPreparing to record...", style="bold yellow")
            selected_file = record_audio(duration=duration)
            console.print(f"\nRecording saved to {selected_file}", style="bold green")
        
        if not selected_file:
            break
            
        # Get instructions
        default_instructions = f"Analyze the audio file at {selected_file} and perform a spectral analysis to characterize processes near me"
        instructions = Prompt.ask("Enter analysis instructions", default=default_instructions)
        
        # Run analysis
        console.print("\nStarting analysis...\n", style="bold yellow")
        try:
            asyncio.run(run_agent(instructions, console=console))
        except KeyboardInterrupt:
            console.print("\nAnalysis interrupted.\n", style="bold red")
            continue
        
        # Ask to continue
        if not Prompt.ask("\nWould you like to analyze another file?", choices=["y", "n"], default="y") == "y":
            break
    
    console.print("\nAnalysis complete!", style="bold blue")

if __name__ == "__main__":
    main()
