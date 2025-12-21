# Display Any

The Display Any node is a debugging and inspection tool that can display any type of input value in ComfyUI. It's particularly useful for understanding data structures and tensor shapes during workflow development.

## Features

- **Universal Input**: Accepts any type of input data (tensors, strings, numbers, lists, dictionaries, etc.)
- **Two Display Modes**:
  - **Raw Value**: Shows the string representation of the input
  - **Tensor Shape**: Extracts and displays the shapes of any tensors found in the input
- **Nested Structure Support**: Can find tensors within nested dictionaries and lists
- **UI Output**: Displays results directly in the ComfyUI interface

## Inputs

- **input** (*): Any value you want to display or inspect
- **mode** (DROPDOWN): Display mode selection
  - `raw value`: Shows the complete string representation of the input
  - `tensor shape`: Extracts and shows shapes of any tensors in the input

## Outputs

- **display_text** (STRING): The formatted display text

## Usage Examples

### 1. Display Simple Values

Connect any output to see its raw value:
```
String Input: "Hello, ComfyUI!"
Mode: raw value
Output: "Hello, ComfyUI!"
```

### 2. Inspect Tensor Shapes

Great for debugging image processing pipelines:
```
Image Tensor: [1, 3, 512, 512]
Mode: tensor shape
Output: "[[1, 3, 512, 512]]"
```

### 3. Debug Complex Data Structures

View nested data structures with multiple tensors:
```python
Input: {
    "images": tensor([1, 3, 256, 256]),
    "masks": [tensor([256, 256]), tensor([256, 256, 1])],
    "config": {"steps": 20}
}
Mode: tensor shape
Output: "[[1, 3, 256, 256], [256, 256], [256, 256, 1]]"
```

### 4. Workflow Debugging

Use Display Any nodes at various points in your workflow to understand data flow:
- After loading images to verify dimensions
- Before/after processing nodes to track shape changes
- To inspect conditioning or latent data structures
- To view metadata or configuration dictionaries

## Use Cases

### Image Pipeline Debugging
Place Display Any nodes after image loading and processing nodes to track dimension changes:
```
Load Image → Display Any (tensor shape) → Resize → Display Any (tensor shape)
```

### Latent Space Inspection
Understand latent dimensions in your workflows:
```
VAE Encode → Display Any (tensor shape) → KSampler → Display Any (raw value)
```

### Configuration Verification
Display complex configuration objects to ensure correct settings:
```
Config Node → Display Any (raw value) → Processing Node
```

## Tips

1. **Multiple Display Nodes**: You can use multiple Display Any nodes in a single workflow to track data at different stages

2. **Tensor Shape Mode**: Particularly useful when working with:
   - Image batches to verify batch size
   - Latent tensors to understand dimensions
   - Mask arrays to check compatibility

3. **Raw Value Mode**: Best for:
   - String prompts and text
   - Configuration dictionaries
   - Debugging node outputs
   - Understanding data structure

4. **No Tensors Found**: If you see "No tensors found in input" in tensor shape mode, the input doesn't contain any tensor-like objects (numpy arrays, torch tensors, etc.)

## Technical Notes

- The node uses `str()` for raw value display, providing Python's string representation
- Tensor shape detection works with any object that has a `shape` attribute
- Nested structure traversal supports dictionaries, lists, and tuples
- The output is both displayed in the UI and available as a string output for further processing

## Example Workflow Integration

```
[Load Image] → [Image Processing] → [Display Any (tensor shape)]
                                           ↓
                                    "[[1, 3, 512, 512]]"
                                           ↓
[Text Multiline] ← [Concatenate] ← "Image dimensions: "
```

This creates a text output showing the current image dimensions that can be used elsewhere in your workflow.
