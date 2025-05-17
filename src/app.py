from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from pathlib import Path
import asyncio
from agent import run_agent

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
        # Select audio file
        selected_file = select_audio_file()
        if not selected_file:
            break
            
        # Get instructions
        default_instructions = f"Analyze the audio file at {selected_file} and perform a spectral analysis"
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
