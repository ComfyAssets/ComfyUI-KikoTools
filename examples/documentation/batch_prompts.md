# Batch Prompts Node

The **Batch Prompts** node loads and processes prompts from text files for batch generation workflows. It automatically cycles through prompts with each execution, making it perfect for testing multiple prompts in queue batches.

## Features

- **File-based prompt loading** - Load prompts from text files with `---` separators
- **Auto-increment mode** - Automatically advance to the next prompt with each execution
- **Positive/Negative splitting** - Automatically splits prompts at "Negative:" markers
- **Persistent state** - Maintains position across ComfyUI restarts
- **Wrap-around support** - Loop back to the first prompt after the last one
- **Progress tracking** - Shows current position and total prompts

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt_file` | STRING | "prompts.txt" | Path to text file containing prompts |
| `index` | INT | 0 | Manual prompt index (when auto_increment is off) |
| `auto_increment` | BOOLEAN | True | Automatically advance to next prompt |
| `wrap_around` | BOOLEAN | True | Loop back to start after last prompt |
| `split_negative` | BOOLEAN | True | Split prompts at "Negative:" marker |
| `reload_file` | BOOLEAN | False | Force reload file from disk |
| `show_preview` | BOOLEAN | True | Show prompt preview in console |

## Output Values

| Output | Type | Description |
|--------|------|-------------|
| `positive` | STRING | The positive prompt text |
| `negative` | STRING | The negative prompt text (if split) |
| `full_prompt` | STRING | Complete prompt including negative |
| `next_prompt` | STRING | Preview of the next prompt |
| `current_index` | INT | Current prompt index (0-based) |
| `total_prompts` | INT | Total number of prompts |
| `batch_info` | STRING | Progress information string |

## Prompt File Format

Create a text file with prompts separated by `---` on its own line:

```
A beautiful sunset over the ocean
Negative: blurry, dark, low quality
---
Mountain landscape with snow peaks
Negative: foggy, unclear
---
Futuristic city at night
Negative: old, vintage, sepia
```

## Usage Examples

### Basic Queue Batch Processing

1. Create a prompt file in your ComfyUI `input` folder
2. Add the Batch Prompts node to your workflow
3. Set `prompt_file` to your file name
4. Enable `auto_increment` and `wrap_around`
5. Connect `positive` to your text encoder
6. Connect `negative` to your negative text encoder
7. Set Queue Batch to desired number (e.g., 10)
8. Run the queue - prompts will cycle automatically

### Manual Index Control

For manual control over which prompt to use:

1. Set `auto_increment` to False
2. Control the `index` parameter manually
3. Use with other nodes that provide index values

### Monitoring Progress

The node provides several ways to track progress:

- `batch_info` output shows "Prompt X of Y (Z% complete)"
- Console logging shows current prompt preview (when `show_preview` is True)
- `current_index` and `total_prompts` for custom progress displays

## Tips

- Place prompt files in the ComfyUI `input` folder for easy access
- Use relative paths like "prompts.txt" for files in the input folder
- Use absolute paths for files elsewhere on your system
- The node maintains state across ComfyUI restarts
- Set `reload_file` to True to force re-reading after editing the file
- Empty sections (between `---` markers) are automatically skipped

## Troubleshooting

### Prompts not changing in queue batch
- Ensure `auto_increment` is set to True
- Check console for "[BatchPrompts] Auto-increment" messages
- Restart ComfyUI after installing/updating the node

### File not found errors
- Check that the file exists in the ComfyUI `input` folder
- Try using an absolute path to test
- Ensure file has read permissions

### State persistence
- State is stored in your system's temp directory
- Clear `/tmp/comfyui_batch_prompts/` to reset all counters
- Use `reload_file` to reset counter for a specific file
