# Kiko Save Image

Enhanced image saving node with multiple format support, quality controls, and an interactive floating popup viewer for ComfyUI.

## Features

- **Multiple Format Support**: Save as PNG, JPEG, or WebP with format-specific optimizations
- **Advanced Quality Controls**: Fine-tune compression settings per format
- **Floating Popup Viewer**: Interactive window showing saved images immediately
- **Batch Operations**: Multi-select images for bulk actions
- **File Size Display**: Real-time feedback on compression effectiveness
- **Smart UI**: Auto-hide, draggable, resizable popup window

## Inputs

- **images** (IMAGE): Batch of images to save
- **filename_prefix** (STRING): Prefix for saved filenames
  - Default: "KikoSave"
  - Supports subfolder paths (e.g., "outputs/renders/final")
- **format** (DROPDOWN): Output format selection
  - `PNG`: Lossless compression, best quality
  - `JPEG`: Lossy compression, smaller files
  - `WEBP`: Modern format, best compression ratio
- **quality** (INT): JPEG/WebP quality level
  - Range: 1-100 (default: 90)
  - Higher values = better quality, larger files
- **png_compress_level** (INT): PNG compression level
  - Range: 0-9 (default: 4)
  - Higher values = smaller files, slower saving
- **webp_lossless** (BOOLEAN): Use lossless WebP compression
  - Default: False (lossy)
  - True: Lossless compression like PNG
- **popup** (BOOLEAN): Enable popup viewer window
  - Default: True
  - Toggle per save operation

## Outputs

- **UI**: Enhanced preview data with interactive popup viewer

## Popup Viewer Features

### Window Controls
- **Drag Handle**: Click and drag the header to move window
- **Minimize Button**: Collapse to title bar only
- **Maximize Button**: Expand to larger viewing size
- **Roll-up Button**: Show/hide content area
- **Close Button**: Hide the popup (can reopen with toggle)

### Image Grid
- **Thumbnails**: Click any image to open full-size in new tab
- **File Info**: Shows filename and size for each image
- **Quality Indicators**:
  - PNG: Compression level (0-9)
  - JPEG/WebP: Quality percentage
- **Batch Selection**: Checkboxes for multi-select operations

### Bulk Actions
- **Open All Selected**: Opens selected images in new tabs
- **Download All Selected**: Downloads selected images as a batch
- **Individual Downloads**: Download button per image

### Smart Behavior
- **Auto-positioning**: Appears in convenient screen location
- **Persistence**: Stays open across multiple saves
- **Auto-hide**: Can be minimized when not needed
- **Responsive**: Adapts to different image counts

## Format Details

### PNG Format
- **Pros**: Lossless quality, transparency support, wide compatibility
- **Cons**: Larger file sizes
- **Best for**: Final outputs, images with transparency, archival
- **Compression**: 0 (none) to 9 (maximum)
  - Level 4 (default) balances size and speed
  - Level 9 for maximum compression (slow)

### JPEG Format
- **Pros**: Smaller files, fast loading, universal support
- **Cons**: Lossy compression, no transparency
- **Best for**: Web images, previews, photos
- **Quality**: 1-100%
  - 90% (default) excellent quality with good compression
  - 95%+ for near-lossless quality
  - 70-85% for web optimization

### WebP Format
- **Pros**: Best compression ratios, supports transparency, modern
- **Cons**: Limited software support
- **Best for**: Web deployment, storage optimization
- **Modes**:
  - Lossy (default): Excellent compression with quality control
  - Lossless: PNG-like quality with better compression

## Usage Examples

### High-Quality Archive
```
Format: PNG
Compression: 0-2
Use Case: Final renders for portfolio or client delivery
```

### Web Optimization
```
Format: JPEG or WebP
Quality: 80-85
Use Case: Website images, social media posts
```

### Balanced Storage
```
Format: WebP
Quality: 90
Lossless: False
Use Case: Large batches with storage constraints
```

### Transparency Preservation
```
Format: PNG or WebP (lossless)
Use Case: Logos, UI elements, cutout images
```

## Workflow Integration

### Basic Save
```
Generate → Kiko Save Image
           format: PNG
           popup: enabled
```

### Format Comparison
```
Generate → Kiko Save Image (PNG)    → Compare file sizes
        ↘ Kiko Save Image (JPEG)   ↗
        ↘ Kiko Save Image (WebP)   ↗
```

### Batch Processing
```
Batch Generate → Kiko Save Image → Popup Viewer
                 ↓                  ↓
                4 images        Select best results
```

## Tips and Best Practices

1. **Format Selection**:
   - Use PNG for maximum quality and transparency
   - Use JPEG for photographs without transparency
   - Use WebP for modern web deployment

2. **Quality Settings**:
   - Start with defaults (90 for JPEG/WebP, 4 for PNG)
   - Adjust based on file size requirements
   - Preview results in popup before finalizing

3. **Popup Management**:
   - Drag to second monitor for larger workspace
   - Use roll-up to save screen space
   - Disable popup for automated workflows

4. **Batch Operations**:
   - Use checkboxes to select multiple images
   - Open all in tabs for side-by-side comparison
   - Download all for quick collection

5. **File Organization**:
   - Use subfolders in filename_prefix
   - Include descriptive prefixes
   - Let ComfyUI handle timestamp suffixes

## Advantages Over Standard Save Image

- **Immediate Preview**: No need to navigate file system
- **Format Flexibility**: Choose optimal format per use case
- **Quality Control**: Fine-tune compression settings
- **Batch Management**: Handle multiple images efficiently
- **Modern UI**: Floating interface doesn't interrupt workflow
- **File Size Awareness**: See compression effectiveness immediately
- **Quick Access**: One-click opening and downloading

## Technical Details

- **Image Processing**: Uses Pillow for format conversion
- **Metadata**: Preserves ComfyUI metadata in saved files
- **File Naming**: Automatic timestamp and counter suffixes
- **Memory Efficiency**: Processes images individually
- **Thread Safety**: Proper handling of concurrent saves

## Troubleshooting

**Popup not appearing**:
- Check that popup input is enabled
- Look for minimized window
- Try toggling the popup button in node

**WebP not working**:
- Ensure Pillow has WebP support
- Update Pillow: `pip install --upgrade pillow`

**Large file sizes**:
- Increase compression (PNG) or reduce quality (JPEG/WebP)
- Consider switching formats
- Check image dimensions

**Can't see all images**:
- Scroll within the popup grid
- Maximize the popup window
- Images are shown newest first
