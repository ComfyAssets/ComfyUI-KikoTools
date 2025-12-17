# Display Text

The Display Text node provides advanced text display capabilities with smart formatting, interactive features, and responsive design for ComfyUI workflows.

## Features

- **Smart Prompt Detection**: Automatically detects and formats SDXL-style positive/negative prompt pairs
- **Text Wrapping**: Proper word wrapping that reflows when node is resized
- **Scrollable Content**: Mouse wheel scrolling for long texts with visual indicators
- **Copy Functionality**: Always-visible copy button with visual feedback
- **Split View Mode**: Side-by-side display for prompt pairs
- **Responsive Design**: Content adapts to node resizing

## Inputs

- **text** (STRING): The text to display
  - Can be a single text block
  - Can contain "Positive prompt:" and "Negative prompt:" sections for automatic split view

## Outputs

- **text** (STRING): Pass-through of the input text

## Display Modes

### Single Text Mode

When the input is regular text without prompt markers, it displays as a single scrollable text area with:
- Word wrapping at word boundaries
- Vertical scrolling for long content
- Single copy button for the entire text

### Split View Mode

Automatically activated when text contains both "Positive prompt:" and "Negative prompt:" sections:
- Side-by-side display with 50/50 split
- Independent scrolling for each section
- Separate copy buttons for each prompt
- Labels are stripped when copying (clean prompts)

## Usage Examples

### 1. Display Generated Prompts

```
Gemini Prompt → Display Text → Copy to workflow
```
The node automatically detects SDXL format and shows positive/negative prompts side-by-side.

### 2. Debug Text Processing

```
Text Processing → Display Text → Further Processing
```
View intermediate text processing results with proper formatting.

### 3. Show Long Descriptions

```
Load Text → Display Text → Review
```
Display long text content with scrolling and word wrapping.

## Interactive Features

### Copy Button
- Always visible in the top-right corner
- Shows "✓ Copied!" feedback on click
- In split view: separate buttons for each section
- Strips prompt labels for clean copying

### Scrolling
- Mouse wheel scrolling when hovering over text
- Visual indicators appear when content is scrollable
- Smooth scrolling with proper boundaries
- Independent scrolling in split view mode

### Resizing
- Text reflows when node width changes
- Maintains readability at different sizes
- Split view maintains 50/50 proportions
- Minimum height ensures usability

## Smart Prompt Detection

The node intelligently detects prompt formats:

1. **SDXL Format**:
   - Looks for "Positive prompt:" and "Negative prompt:" markers
   - Case-insensitive detection
   - Handles various formatting styles

2. **Label Stripping**:
   - When copying from split view, labels are removed
   - "Positive prompt: beautiful sunset" → "beautiful sunset"
   - Clean prompts ready for direct use

## Styling

- **Font**: Monospace for consistent alignment
- **Colors**:
  - Text: Light gray (#ddd) on dark background
  - Background: Semi-transparent dark (#1a1a1a)
  - Borders: Subtle gray (#333)
- **Spacing**: Comfortable padding and line height
- **Visual Feedback**: Hover effects on interactive elements

## Use Cases

### Prompt Engineering Workflows
- Display AI-generated prompts with proper formatting
- Compare positive and negative prompts side-by-side
- Copy refined prompts without manual cleanup

### Text Processing Pipelines
- Debug text transformations at each step
- View formatted outputs from text nodes
- Monitor prompt construction workflows

### Documentation and Notes
- Display workflow instructions
- Show generation parameters
- Present formatted metadata

## Technical Details

- **Text Processing**: Preserves original text while adding display formatting
- **Responsive Design**: CSS-based layout adapts to node dimensions
- **Event Handling**: Proper event propagation for ComfyUI compatibility
- **Memory Efficient**: Only renders visible text portions

## Tips

1. **For Long Prompts**: The scrolling feature handles texts of any length efficiently
2. **Quick Copy**: Use the copy buttons to quickly grab prompts for other nodes
3. **Resizing**: Drag node edges to find optimal display width for your content
4. **Split View**: Works best with SDXL-format prompts but handles any dual-section text

## Integration Example

```
[Gemini Prompt Engineer] → [Display Text] → [Copy Button Click]
         ↓                        ↓                    ↓
   SDXL Format            Split View Display    Clean Prompts
```

This creates a seamless workflow from prompt generation to usage, with the Display Text node providing the visual interface for review and interaction.
