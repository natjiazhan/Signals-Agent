import io
import csv
import matplotlib.cm
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

def _get_color_for_value(value: float, v_min: float, v_max: float) -> str:
    """Maps a value to a jet colormap hex color string."""
    if v_min == v_max:
        normalized = 0.5  # Default to a mid-range color if all values are the same
    else:
        normalized = (value - v_min) / (v_max - v_min)
    
    # Clamp normalized value to [0, 1] just in case
    normalized = max(0.0, min(1.0, normalized))
            
    r, g, b, _ = matplotlib.cm.jet(normalized)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def format_fft_output_as_rich_table(
    csv_string: str, 
    console: Console, 
    tool_name: str, 
    tool_kwargs: dict
):
    """Parses FFT CSV output and prints it as a colorized Rich Table."""
    try:
        csv_file = io.StringIO(csv_string)
        reader = csv.reader(csv_file)
        header = next(reader)
        data_rows = list(reader)

        if not data_rows:
            console.print(Panel(
                f"Used tool `{tool_name}` with {tool_kwargs}\nReturned (empty CSV):\n{csv_string}",
                title=f"Tool Result ({tool_name} - Empty)",
                style="dim",
                border_style="dim",
                expand=False,
            ))
            return

        numerical_values = []
        for row in data_rows:
            for i, cell_value in enumerate(row):
                if i > 0:  # Skip 'Time' column
                    try:
                        numerical_values.append(float(cell_value))
                    except ValueError:
                        pass

        min_val = min(numerical_values) if numerical_values else 0
        max_val = max(numerical_values) if numerical_values else 1

        table = Table(title=f"Tool Result: {tool_name} ({tool_kwargs})")
        for col_name in header:
            table.add_column(col_name)

        for row_values in data_rows:
            styled_row = []
            for i, cell_str in enumerate(row_values):
                if i == 0:  # Time column
                    styled_row.append(Text(cell_str))
                else:
                    try:
                        val = float(cell_str)
                        color = _get_color_for_value(val, min_val, max_val)
                        styled_row.append(Text(f"{val:.3f}", style=color))
                    except ValueError:
                        styled_row.append(Text(cell_str))
            table.add_row(*styled_row)
        
        console.print(table)

    except Exception as e:
        console.print(Panel(
            f"Error processing FFT output for {tool_name}: {e}\n\nUsed tool with {tool_kwargs}\nReturned:\n{csv_string}",
            title=f"Tool Result ({tool_name} - Error)",
            style="red",
            border_style="dim",
            expand=False,
        )) 