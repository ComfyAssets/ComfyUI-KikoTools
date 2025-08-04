# ComfyUI XYZ Grid Comparison Nodes

## Project Objective
Create a modular suite of ComfyUI nodes for visual grid-based comparisons across parameters such as:

- Models
- LoRAs
- Schedulers
- Samplers
- CFG Scale
- Steps
- Clip Skip
- VAEs
- Flux Guidance (custom model settings)

The tool will support X, Y, and optional Z axis configuration using a polished, intuitive UI with no scripting or coding required.

---

## Design Goals

- **Modular Architecture:** Built as multiple nodes (not monolithic)
- **Standard Node Compatibility:** Work with *any* KSampler, Model Loader, etc.
- **User Friendly UI:** Dropdowns, toggles, and visual input—no syntax or scripting
- **Flexible Axis Mapping:** Any parameter can go on X, Y, or Z
- **Dynamic Grid Generation:** One-click execution queues all combinations
- **Labeling:** Automatic overlay and metadata support with clean presentation
- **High Performance:** Smart resource caching and sequential queuing

---

## Key Nodes

### 1. `XYZ Plot Controller`
- Main config node
- Allows axis selection (X, Y, optional Z)
- Outputs: axis values, labels, grid ID
- Automatically queues image generation

### 2. `Image Grid Combiner`
- Accepts image + axis metadata
- Assembles a labeled grid (or multiple grids)
- Outputs: grid image(s), optional metadata (label list, value list)

---

## Parameter Types
Supported as axis values:
- Model (checkpoint)
- LoRA (file)
- VAE
- Sampler (Euler, DPM++, etc.)
- Scheduler
- CFG Scale (float list)
- Steps (int list)
- Clip Skip
- Prompt (swap full prompt or use template)
- Seed
- Custom (e.g., Flux guidance strength)

---

## UI Design

### Axis Config (for X, Y, Z)
- Dropdown: Select parameter type
- Input: List of values (dynamic UI)
  - File pickers (models, LoRAs)
  - Number range or CSV (steps, CFG)
  - Text input (prompts)
- Label customization
  - Prefix: optional (e.g., CFG=, Sampler:)
  - Label format: full, short, value only

### Execution
- One-click generate
- Internally queues all combinations (X * Y * Z)
- Reuses sampler, model loader, etc.
- Supports caching to avoid repeated loads

---

## Output Behavior
- Combiner tracks image count
- Assembles grid when complete
- Draws axis labels using PIL
- Handles Z axis by outputting multiple grids
- Preview as images come in
- Metadata export (optional JSON/text)

---

## Example Use Cases

### Model vs CFG
- X: Models A/B
- Y: CFG [5,10,15]
- Output: 2x3 grid with axis labels

### Prompt vs Sampler
- X: Prompt variations
- Y: Samplers
- Output: labeled comparison grid

### LoRA vs Seed, Z=Strength
- X: LoRA name
- Y: Seeds
- Z: LoRA strength
- Output: Multiple 2D grids, one per Z value

---

## Development Phases

### Phase 1: MVP
- X/Y support
- Core image generation loop
- Grid image stitching

### Phase 2: Z Axis + More Parameters
- Prompt, LoRA, Flux guidance, etc.

### Phase 3: UI Polish
- Dynamic widgets
- Label controls, error handling

### Phase 4: Performance & Optimization
- Model caching
- Memory handling
- Abort/resume logic

### Phase 5: Docs & Examples
- Example workflows
- Visual documentation

---

## References & Inspirations
- [TinyTerra ComfyUI_tinyterraNodes](https://github.com/TinyTerra/ComfyUI_tinyterraNodes)
- [kenjiqq/qq-nodes-comfyui](https://github.com/kenjiqq/qq-nodes-comfyui)
- [jags111/efficiency-nodes-comfyui](https://github.com/jags111/efficiency-nodes-comfyui)
- [shockz-comfy/comfy-easy-grids](https://github.com/shockz-comfy/comfy-easy-grids)

---

## Final Outcome
A polished, no-code, modular XYZ plotting system in ComfyUI for exploring image generation across any combination of models, settings, or parameters with professional-grade visual output.

