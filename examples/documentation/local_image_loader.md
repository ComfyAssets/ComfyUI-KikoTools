# Local Image Loader

## Overview

The Local Image Loader node provides a visual gallery interface for browsing and selecting images, videos, and audio files from your local filesystem directly within ComfyUI. This streamlined version focuses on essential functionality without the complexity of tagging or metadata management.

## Features

- **Visual Gallery Browser**: Browse local directories with thumbnail previews
- **Multi-Media Support**: Load images, videos, and audio files
- **Directory Navigation**: Navigate through folders with ease
- **Sorting Options**: Sort by name, date, or file size
- **Saved Paths**: Save frequently used directory paths for quick access
- **Pagination**: Handle large directories with paginated display
- **Lightbox Preview**: Full-size preview with zoom and pan capabilities

## Node Inputs

### Required Inputs
None - The node uses a visual interface for file selection

### Hidden Inputs
- `unique_id`: Automatically assigned node identifier

## Node Outputs

| Output | Type | Description |
|--------|------|-------------|
| `image` | IMAGE | The selected image as a tensor |
| `video_path` | STRING | Path to the selected video file |
| `audio_path` | STRING | Path to the selected audio file |
| `info` | STRING | JSON metadata about the selected image |

## Usage

### Basic Workflow

1. **Add the Node**: Search for "Local Image Loader" in the node menu
2. **Browse Directory**: Enter a directory path or use saved paths
3. **Select Media**: Click on thumbnails to select files
4. **Connect Outputs**: Use the outputs in your workflow

### Interface Controls

#### Path Management
- **Directory Input**: Enter or paste a directory path
- **Saved Paths Dropdown**: Quick access to saved directories
- **Save Path Button** (💾): Save current directory to favorites
- **Browse Button** (📁): Load the entered directory

#### View Options
- **Videos Checkbox**: Show/hide video files
- **Audio Checkbox**: Show/hide audio files
- **Sort By**: Choose between Name, Date, or Size
- **Sort Order**: Ascending (↑) or Descending (↓)
- **Refresh Button** (🔄): Reload current directory

#### Gallery Display
- **Thumbnail Grid**: Visual preview of files
- **Blue Border**: Selected items are highlighted
- **Folder Icons**: Navigate into subdirectories
- **Video Overlay**: Visual indicator for video files
- **Pagination**: Navigate through pages of results

## File Support

### Supported Image Formats
- `.jpg`, `.jpeg`
- `.png`
- `.bmp`
- `.gif`
- `.webp`

### Supported Video Formats
- `.mp4`
- `.webm`
- `.mov`
- `.mkv`
- `.avi`

### Supported Audio Formats
- `.mp3`
- `.wav`
- `.ogg`
- `.flac`

## Image Metadata

When an image is selected, the node extracts and returns metadata including:
- **Basic Info**: Filename, width, height, format, mode
- **Embedded Parameters**: Generation parameters if present
- **Workflow Data**: Embedded ComfyUI workflow if present
- **Prompt Data**: Embedded prompt information if present

## Examples

### Loading an Image for Processing
```
Local Image Loader → Load Image → Image Processing Node
                 ↓
              [info] → Display Text (to show metadata)
```

### Setting Up a Multi-Media Workflow
```
Local Image Loader → [image] → Image Preview
                 ↓
           [video_path] → Video Player Node
                 ↓
           [audio_path] → Audio Player Node
```

## Tips and Best Practices

1. **Save Frequently Used Paths**: Use the save button to bookmark directories you use often
2. **Use Sorting**: Sort by date to find recent files quickly
3. **Keyboard Navigation**: Press Enter in the path field to load a directory
4. **Performance**: For directories with thousands of files, use pagination to navigate efficiently
5. **Thumbnail Generation**: Thumbnails are generated on-demand and cached for performance

## Differences from Original

This version simplifies the original ComfyUI_Local_Image_Gallery by removing:
- Tag filtering and management
- Rating system
- Global tag search
- Metadata editing capabilities

These features were removed to focus on the core functionality of browsing and selecting files, making the tool simpler and more straightforward to use.

## Troubleshooting

### Common Issues

**Directory Not Loading**
- Verify the path exists and you have read permissions
- Check for special characters in the path
- Try using absolute paths instead of relative ones

**Thumbnails Not Showing**
- Ensure the files are in supported formats
- Check if the images are corrupted
- Try refreshing the gallery

**Large Directories Slow to Load**
- Use sorting and pagination to manage large folders
- Consider organizing files into subdirectories
- Enable only the media types you need (images, videos, audio)

## Technical Details

The node creates a visual widget that runs in the ComfyUI interface and communicates with the backend through API endpoints to:
- List directory contents
- Generate thumbnails
- Save user preferences
- Handle file selection

All file operations are performed server-side for security, with proper path validation to prevent directory traversal attacks.
