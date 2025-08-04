Project Plan: ComfyUI XYZ Grid Comparison Nodes
Objectives and Requirements
We aim to develop a suite of XYZ Plot custom nodes for ComfyUI that enable easy grid comparisons across multiple parameters with minimal user effort. The goal is to support varying any combination of Models (checkpoints), LoRAs, Samplers, Schedulers, CFG scales, Steps, Clip skip, VAEs, and even new model-specific parameters like Flux guidance, all in a structured X/Y (and optional Z) grid format. Key requirements include:
Simple User Experience: Users should not need to write complex syntax or scripts to set up a grid. All configuration should be via clear UI fields (dropdowns, lists, etc.), unlike TinyTerra’s advanced XYPlot which requires manual text syntax for axes
runcomfy.com
.
Polished UI: Nodes should have an intuitive interface with logical organization. The system will automatically handle labeling of rows/columns with parameter values, adjustable font size, prefixes, etc., to produce presentation-ready grids
github.com
. No manual image combining or external tools should be needed.
Flexibility: Support any sampler or model loader node in ComfyUI – users should not be forced to use a custom KSampler as in the Efficiency node pack (which, while powerful, requires using its custom loader & sampler nodes
reddit.com
). Our solution will integrate with ComfyUI’s standard nodes so any sampler algorithm or model can be used.
Comprehensive Parameter Support: Allow plotting virtually “anything vs anything.” This means an X-axis and Y-axis (and optionally Z for a series of grids) can represent a range of values for any parameter in the workflow – e.g. different sampler names, different checkpoint models, numeric values (like steps or CFG), different prompt texts or LoRAs, etc.
runcomfy.com
. The system should even allow advanced uses like varying ControlNet strength or performing prompt search-and-replace if possible
runcomfy.com
.
Single-Run Automation: The user should be able to hit “Generate” once and get a complete labeled grid (or set of grids). The nodes will handle queuing or looping internally. Unlike some current solutions that require manually queuing multiple runs and hitting reset (e.g. the QQ XY Grid requires clicking reset and adding prompt jobs equal to the grid size
github.com
), our design will automate the iteration over all combinations.
Analysis of Existing Solutions
To design the best XYZ plot nodes, we examined the strengths and weaknesses of existing community solutions:
TinyTerra’s Advanced XY(Z) Plot: This extension provides very powerful and flexible plotting (even Z-axis for multiple grids) and features like search/replace in prompts and appending values
runcomfy.com
. However, it relies on a text-based configuration syntax that users must type into a special node
runcomfy.com
. For example, one must write out axis blocks like <1:label>\n[node_ID:option='value'] etc., which is powerful but complex for users to author correctly. Its UI is not as straightforward for novices, despite offering auto-complete aids
runcomfy.com
. We aim to capture its flexibility (support for many parameter types and even Z-axis) but present it in a friendlier UI with form inputs instead of coding.
KenjiQQ’s QQ-Nodes (XY Grid Helper & Accumulator): This approach uses nodes to build the grid via lists and accumulation. The XY Grid Helper node takes lists of row and column values and will iterate through each combination, outputting the current row/col value for other nodes
github.com
. A separate Accumulator collects images and assembles the final grid, even showing a live preview as images come in
github.com
. It supports custom prefixes, font sizes, and grid gaps for annotation
github.com
. However, the user must perform some manual steps: for example, clicking reset and manually queuing the correct number of prompts to generate all combinations
github.com
. Additionally, because the output row/col values are untyped, one must use extra “Axis To X” converter nodes to plug them into e.g. a model loader or number input
github.com
. Pros: clear separation of concerns (list setup, conversion, accumulation) and customizable layout. Cons: Not entirely automated (requires manual queuing) and the multi-node setup (with converters) is a bit cumbersome UI-wise. We plan to improve upon this by automating the iteration loop and reducing the number of fiddly nodes needed.
Jags’ Efficiency Nodes (XY Plot Script): The Efficiency node pack includes a very convenient X/Y plot capability that is integrated into a modified KSampler. By connecting an XY Plot script node to the custom KSampler, the sampler will generate a grid of images internally
github.com
. This solution is seamless to use and fast – it caches models to avoid reload overhead and can vary many things (including checkpoint models, LoRAs, prompts, etc.) with one click
runcomfy.com
. It also supports special plot types like prompt substitution and ControlNet toggles
runcomfy.com
. Drawback: It forces the use of the “Efficient” Loader & KSampler nodes
reddit.com
, meaning a user must swap out their normal nodes and cannot easily use other samplers or future nodes. This tight coupling is “annoying” for some users
reddit.com
. Our plan draws inspiration from Efficiency’s one-click ease and feature depth, but will remain agnostic to specific sampler implementations. We won’t require a custom sampler – our nodes will coordinate with the standard ComfyUI nodes (ensuring broad compatibility).
ShockZ’s Comfy-Easy-Grids: This extension (a.k.a. ComfyRoll) focuses on simplifying grid generation with automation. The Create Image Grid node lets you specify grid dimensions (X and Y size) and then automatically queues the required number of prompts, outputting the current X and Y index for each iteration
runcomfy.com
. Paired with a Save Image Grid node (a modified saver), it will accumulate images until the grid is complete and then output a combined image, including optional row/column labels provided via inputs (e.g. String lists)
runcomfy.com
. This approach is very user-friendly – you don’t need to manually queue or reset; the node handles looping internally. It also provides utility nodes like FloatList, StringList, and LoRA List to easily supply sequences of values to iterate
runcomfy.com
runcomfy.com
. Pros: True one-click operation and straightforward list-based UI. Cons: Each axis’s values still need to be prepared as list nodes and wired in, and labeling requires manually creating label lists that correspond to the values. There’s no single consolidated UI to choose parameter types and values – it’s still somewhat low-level in that you construct the mechanism with multiple nodes. We intend to build on this by offering a single high-level interface for selecting parameters and values, while likely leveraging a similar under-the-hood approach of automated queuing and image accumulation.
In summary, existing solutions prove that it’s possible to plot “anything vs anything” in ComfyUI, but each has trade-offs. Our project will combine their best ideas: the flexibility of TinyTerra, the grid customization and labeling of QQ/Comfy-Easy-Grids, and the one-click convenience of Efficiency – all while removing the need for coding or rigid custom node dependencies.
Proposed Design and Features

1. Node Architecture
   We will implement the XYZ plotting functionality as two main nodes for clarity and modularity (similar to the Create/Save separation in easy-grids):
   XYZ Plot Controller Node – This is the primary configuration node where the user chooses what to vary on the X axis, Y axis, and optionally Z axis. It handles generating the sequence of parameter combinations and triggering the image generation for each. Internally, this node will automatically queue the required runs (or otherwise loop through combinations) so that the user only needs to execute once to get all images, much like Create Image Grid does
   runcomfy.com
   . This node will output:
   Index/Value Outputs: For each axis (X, Y, Z) it provides an output that represents the current value for that axis in a given iteration. These outputs can be fed into other nodes in the workflow (e.g., into a checkpoint loader’s model field, into a sampler’s steps or CFG input, into a text concatenation node for prompts, etc.). We will make these outputs type-aware to avoid extra conversion nodes – e.g., X output might be a string type if X is “model name”, or a float if X is a numeric parameter. (If needed, we can internally include conversion logic or expose outputs in multiple types.)
   Loop Control/Trigger: It may also output a control signal (like a boolean or trigger) indicating when a batch/grid is complete. This can feed into the second node to signal when to finalize the grid image.
   Grid Combiner (Image Grid Output) Node – This node will collect the images produced from each combination and assemble the final grid image (or images). It functions similarly to QQ’s accumulator or Easy-Grids’ save node, holding onto incoming images until the set is complete
   github.com
   . Once all images for one grid are ready, it will output:
   A composite grid image arranged according to X and Y dimensions, with annotated labels.
   It will support multiple pages if a Z-axis is used (for example, if Z has 3 values, it could produce 3 grid images – one per Z – or perhaps one big tiled 3D grid, but likely separate images makes more sense). We will likely implement Z as generating multiple grid outputs (perhaps as a list of images or sequential outputs the user can save individually).
   Additionally, it could provide a UI preview output for convenience, showing progress as images come in (like QQ’s accumulator does in preview mode
   github.com
   ).
   This two-node setup keeps things organized: the Controller focuses on parameter logic, and the Combiner on image assembly and labeling. For basic use, the user would place these two nodes and connect them: the Controller’s image output (from the sampler) goes into the Combiner’s image input, and the Combiner outputs the final grid. We will make sure they sync via the unique batch ID or trigger so that each grid resets properly and doesn’t mix images from different runs (similar to QQ’s unique_id usage to separate batches
   runcomfy.com
   runcomfy.com
   ).
2. Parameter Selection UI
   The XYZ Plot Controller node’s UI will be the heart of user interaction. We will design it with dynamic, easy-to-use widgets:
   Axis Parameter Dropdowns: The node will have sections for X Axis, Y Axis, and Z Axis. For each axis, the user can choose the parameter type from a dropdown menu. For example:
   None (if they don’t want to use the Z axis at all, they can disable it),
   Model (Stable Diffusion checkpoint model),
   Sampler (diffusion sampler algorithm),
   Scheduler (if applicable, e.g. scheduler type or noise schedule – we will clarify if this is needed or if “sampler” covers it),
   CFG Scale (classifier guidance scale),
   Steps (number of diffusion steps),
   Clip Skip (text encoder skip levels),
   VAE (decoder to use),
   LoRA (Low-Rank Adaptation model to apply),
   Prompt Text (to vary text or prompt components),
   Flux Guidance (if using a Flux model, vary its guidance strength or related parameter),
   Seed (to test different random seeds),
   etc. – Essentially any parameter that a ComfyUI workflow might want to sweep. We can start with the most common ones and allow extending in future.
   Value Input Fields: Depending on the parameter chosen, the UI will present an appropriate input mechanism for the list of values:
   For categorical choices (Model, Sampler, VAE, LoRA), we will provide either a multi-select checklist or a list builder. Ideally, we can query the available options dynamically:
   Model: Provide a dropdown or list of available checkpoint files in the models folder, so the user can select multiple models to compare. (We will use ComfyUI’s existing model loader API or search the directory for model filenames).
   Sampler: A list of sampler names (Euler, Euler a, LMS, DPM++ etc.) – we can fetch these from ComfyUI’s KSampler options or maintain a predefined list if needed.
   LoRA: List of available LoRA files (perhaps via the LoRA loader’s listing or a folder scan).
   VAE: Similarly, list VAE filenames to choose from.
   If multiple selections are allowed, we will allow adding items to the list easily (maybe checkboxes or a plus-button to add another slot).
   For numeric ranges (CFG scale, Steps, Clip skip, etc.), provide an input that can accept comma-separated values or a range generator:
   We might allow a syntax like start:stop:step to quickly specify a range (and parse it into list of values), or simply ask for a list of numbers (with a helper to fill ranges).
   Alternatively, include spin boxes to add values one by one. We can also integrate with the concept of Easy-Grids’ Float List/Int List: for example, let the user enter something like “0, 0.5, 1.0” for flux guidance, or “10,20,30” for steps.
   For text prompts variation, we have a couple options:
   Simplest: treat the entire prompt as a string and allow the user to input multiple prompt variants (perhaps separated by a special delimiter or via a multiline field where each line is a different prompt). The axis will then swap the entire prompt for each value.
   More advanced: allow specifying a search-and-replace or a placeholder in the prompt. E.g., user writes the base prompt in their Text node like “A portrait of [styles] woman” and in the axis values they supply different strings for [styles] (like “a cyberpunk”, “a victorian”, etc.). TinyTerra’s %search;replace% functionality
   runcomfy.com
   and Efficiency’s Prompt S/R hint at this idea. This might be a stretch goal; initially, we can require full prompt variants or manual setup.
   We will ensure that if prompt text is varied, it can feed into the Positive (or Negative) prompt input of the model pipeline easily (likely through a Text concatenation or by directly connecting a Text node input).
   For boolean or toggle parameters (if any, like using a feature on/off), we can allow values like True/False in the list.
   Axis Labels: By default, the system will generate labels for each value to display on the grid. The user can control this:
   There will be a text field for “X Axis Label Prefix” and “Y Axis Label Prefix” (and Z if needed) – if the user wants to prefix the labels (e.g. “CFG=” so the labels read “CFG=7, CFG=10, …”). By default, we might use the parameter name as prefix (e.g. “Model: ” or “Sampler: ”) unless turned off.
   We will automatically use either the value itself or a short description as the label. For instance, for model filenames we might strip the extension. For prompts, possibly use a truncated first few words if too long.
   We will also include options for label formatting similar to TinyTerra’s tv_label/itv_label concept
   github.com
   (though we’ll hide complexity from user): essentially provide a toggle between showing just the value vs. showing “parameter: value”. Users who want very compact labels can choose value-only, while others might prefer seeing the parameter name included. By default, we’ll include the name or prefix so grids are self-explanatory.
   Font size and max label length can be set in the Combiner node (like QQ’s label_length and font_size
   github.com
   ). We’ll expose those settings in the Combiner UI or let it inherit sensible defaults.
   Axis Combination Limits: The node will display the computed total number of images = (#X values × #Y values × #Z values). This gives the user feedback on how many images will be generated (important for performance awareness). If this number is extremely large, we might warn the user or require confirmation to avoid accidental huge runs.
   Dynamic Field Enable/Disable: If the user selects “None” for Z axis, the UI for Z values will hide or disable. Similarly, if they only want an X or a 1D plot, we could allow Y to be “None” and then it just generates a 1-row grid. We will make sure the UI updates logically based on selections, using ComfyUI’s capabilities for dynamic widgets (TinyTerra does something similar with dynamic widget showing/hiding
   runcomfy.com
   ).
3. Execution Flow (One-Click Generation)
   The behind-the-scenes execution will work as follows:
   When the user hits Generate, the Controller node will take the lists of X, Y, Z values and iterate over all combinations. For each combination, it will set the axis outputs to the current values and emit a forward execution. This will propagate through the rest of the graph (where those outputs are connected) and ultimately produce an image from the KSampler (or decoder).
   We plan to implement this by leveraging ComfyUI’s queue system or looping mechanism. There are a few possibilities:
   Use a technique similar to comfy-easy-grids: internally queue multiple jobs. The Create Image Grid node likely uses api.queuePrompt() calls or similar to push multiple executions. We can replicate that: the first execution of the Controller will schedule the next N-1 executions automatically with the different param values. All images will then be generated in sequence.
   Alternatively, implement an internal loop in the node’s execute method (since custom nodes can produce multiple outputs perhaps) – but ComfyUI typically expects one output per execution, so queuing separate executions is safer.
   We will assign each grid run a unique ID (much like QQ’s unique_id control
   runcomfy.com
   ) that gets passed to the Combiner, so it knows which images belong together. This prevents mixing images from separate plots if two are run concurrently.
   Concurrency & Caching: We will likely generate images sequentially (one combination at a time) to reuse the same pipeline and avoid memory spikes. However, to improve efficiency when switching heavy models (checkpoints, VAEs, etc.), we plan to cache models and other resources. For example, if X axis is models A, B, C, we could load each model once at the start (or keep loaded when switching) to avoid repeatedly loading from disk. Efficiency nodes explicitly had a cache_models option for this
   runcomfy.com
   ; we can implement a lightweight caching strategy: perhaps load each required model in memory, or use ComfyUI’s existing model caching (if any). At minimum, ensure that when we switch model, we do it in a way that ComfyUI’s model loader doesn’t fully unload/reload if not necessary.
   The Combiner node will receive each image as it’s produced. It will hold images in a buffer until the expected count is reached, then assemble the grid:
   We’ll arrange images in row-major order (X axis varying horizontally, Y axis vertically). The number of columns = number of X values (by default, unless we implement a wrap via a “max columns” option similar to QQ’s max_columns
   runcomfy.com
   – we might allow the grid to wrap if too wide).
   It will draw the labels on the top of each column and/or side of each row. We can use a simple Python imaging library (PIL/Pillow) to overlay text, or possibly leverage the images-grid-comfy-plugin that QQ-nodes uses behind the scenes
   github.com
   . We may consider using that plugin to avoid reinventing the wheel for combining images and drawing text. (The QQ readme notes that their node injects the LEv145 images-grid plugin for grid assembly
   github.com
   – perhaps we can directly call that code or include it.)
   Font style can be basic (white text with black outline for visibility, for example).
   Z-axis output: If Z is used (say Z has 2 values meaning two separate grids for e.g. two different prompts), we have options:
   The Combiner could output a list of images (all grids) once done. Or,
   It could output one image at a time and require the user to connect a Save node that handles it. But that’s less convenient.
   Another approach: output a single large image where grids are concatenated vertically or horizontally with a separator and a label for Z. But that might be unwieldy for many Z values.
   Probably simplest: output as a list or just sequentially output multiple images (ComfyUI might not handle multiple outputs from one execution easily, so list is better).
   We will likely output a List of images if Z axis is used, along with maybe a text list of Z labels. The user can then handle it (perhaps with a custom save that can save all in a folder). We’ll detail this behavior in documentation so it’s clear.
   Using Standard Nodes: Our design ensures the actual image generation still uses standard ComfyUI nodes:
   The user’s workflow will include a Checkpoint Loader, Sampler, etc., which produce the image. We simply feed different values into them each iteration. For example, if varying Model, the CheckpointLoader’s ckpt_name field will be driven by our Controller’s X output (string). The user would expose ckpt_name as an input on the loader node and connect the X output to it. Our node will set it to each model filename in turn for each run. Similarly, for numeric parameters like Steps or CFG, we connect to the sampler’s inputs (these are already exposable in ComfyUI). This way, we use “any sampler” – our node doesn’t re-implement sampling, it just feeds values to the existing KSampler. This satisfies the requirement of not being locked into a custom sampler node.
   For LoRAs, one approach is to have the LoRA Loader’s “model path” input connected to our output, cycling through LoRA filenames. Alternatively, we could vary prompt text by injecting <lora:name:weight> tokens (some users do LoRA via prompt text). But a cleaner method is connecting to a LoRA apply node. We will investigate how ComfyUI applies LoRAs by node and support that.
   For prompts, the user can use a Text node for their prompt and we can connect our output to it (maybe via a Text Concatenator if inserting words). If doing entire prompt variations, it might be easiest to have multiple prompts in a String List node and connect our axis output to the Text node’s text input.
   Guidance for Flux: If the parameter is something specific like “Flux guidance strength” (assuming Flux is a model that has a unique guidance parameter separate from CFG), we will allow that to be varied by, say, connecting to a node or API that controls flux guidance. This might require the user to expose that parameter on a Flux-specific node. Since Flux is new, we’ll ensure our design is generic enough to plug into any float or int parameter exposed in the workflow.
4. Labeling and Grid Customization
   Producing a nicely annotated grid is a major part of the user experience. Features for this include:
   Automatic Label Generation: As mentioned, we’ll derive labels from the values. For each axis value, we generate a label string. The Combiner node will have inputs for row_labels and col_labels (and possibly an overall title or Z labels). By default, our Controller can feed these in automatically:
   The Controller can output a list of X labels and list of Y labels once the values are set (similar to how Easy-Grids expects String List inputs for labels
   runcomfy.com
   , but in our case we can supply them directly).
   If needed, we can also allow the user to override these label lists via optional inputs – e.g. if they want abbreviated or custom names not exactly matching the values. If an override is not provided, we use the auto labels.
   Styling Options: In the Combiner UI, provide settings for:
   Font size (with a reasonable default, e.g. 20px).
   Grid cell gap (pixel spacing between images, default perhaps 5-10px)
   github.com
   .
   Maybe font color or style, though likely white text with black outline is universally readable so we might fix that.
   Max columns before wrap (if user wants to break a very large grid into multiple rows – but since Y axis already provides rows, “max columns” would effectively limit X length and overflow to additional grid images; this is an advanced feature, we can defer unless needed).
   Background color for the label area if we want a band behind the labels (or we can just overlay on images if they have space at edges).
   Page Size / Z usage: If Z-axis is large, we might allow showing one “page” (grid) at a time. We can implement a page slider in the UI for preview (this is more advanced and might not be necessary if we output all images at once).
   Interactivity vs Static Output: Initially, the output will be static images. A possible enhancement (future) is an interactive HTML output where you can toggle through Z values or view a high-resolution grid in the UI. However, that’s beyond core requirements – we will focus on static image grids that can be saved.
5. Example Use Cases
   To illustrate how the new nodes will work (and to guide development):
   Example 1: Model vs CFG plot. User wants to compare two models (A and B) at different CFG scales (5, 10, 15) using the same prompt.
   They place the Controller node and set X Axis = Model, select A and B; Y Axis = CFG Scale, enter [5, 10, 15]; Z Axis = None.
   They connect the Controller’s X output to the Checkpoint Loader’s model name, and the Y output to the KSampler’s CFG input.
   They connect KSampler’s image output to the Combiner node.
   The Combiner automatically gets X labels (“Model A”, “Model B”) and Y labels (“CFG5”, “CFG10”, “CFG15” or with prefix “CFG=”).
   Upon running, it generates 2×3 = 6 images, then Combiner outputs a single 2-column by 3-row grid image with labels on top of each column (Model names) and at the left of each row (CFG values). The user can then preview or save this grid.
   What happens behind the scenes: The node will queue 6 runs. It may load model A for first run, then model B for second run, etc., switching back and forth – we might optimize to do AAA… then BBB… to avoid thrashing, but since we need a grid with A and B as columns, we might generate in row-major order (all X for Y1, then Y2). We will consider caching both models in memory to reduce load time.
   Example 2: Sampler vs Prompt Variation. User wants to see how different samplers render two different descriptions.
   X = Sampler, choose Euler vs DPM++ 2M Karras; Y = Prompt, enter “a sunny landscape” and “a rainy landscape” as two variants (or use prompt placeholder approach).
   The user connects X output to the Sampler node’s sampler-name input, and Y output to the positive Prompt text (maybe via a Text node that takes this string).
   Grid will be 2×2: columns = {Euler, DPM2M}, rows = {sunny, rainy}. Labels reflect sampler names and an abbreviated prompt label (or user manually sets row labels to “Sunny” / “Rainy” for brevity).
   All 4 images are generated and combined.
   Example 3: Three-axis plot. User tests two LoRAs at different strengths across three seeds.
   X = LoRA, values = {No LoRA, Style1, Style2} (with possibly weight 1.0 for style LoRAs embedded in selection or separate weight axis if needed); Y = Seed, values = {100, 200, 300}; Z = LoRA Strength, values = {0.5, 1.0} (this means two grids, one at each strength level).
   This will produce 2 (Z) _ 3 (X) _ 3 (Y) = 18 images, output as 2 separate 3x3 grids. The Combiner could output a list [Grid_strength0.5, Grid_strength1.0].
   Each grid’s column labels are LoRA names (with “None” or “No LoRA” for the baseline), row labels are seeds, and each grid has a title or annotation indicating the strength (0.5 or 1.0).
   The user can then examine the effect of LoRA and strength on different seeds.
   These use cases ensure our design covers multiple parameter types simultaneously, a key advantage. The system should be robust to any mix (within reason – some combinations might not make sense, but we won’t restrict it programmatically).
6. Performance Considerations
   Generating large grids (dozens of images) can be slow or memory-heavy. We will incorporate some features to mitigate issues:
   Progress Feedback: The Combiner will update a preview as images arrive (like QQ’s accumulator preview output
   github.com
   ). The node UI can also show a counter of how many images have been generated out of total. This way the user knows it’s working and can estimate time remaining.
   Cancellation: If the user stops the queue, our nodes should handle it gracefully (partially filled grid will reset on next run as needed). The unique ID mechanism will help ensure a canceled run doesn’t erroneously carry over images to the next.
   Memory: For grids with many images, memory might become an issue. We might implement an option akin to QQ’s page_size
   github.com
   to split a very large grid into smaller chunks (e.g., if generating 100 images, do 25 at a time and output 4 grids). However, by default we assume moderate grid sizes. This is an advanced option for users who truly need it.
   Threading: ComfyUI typically runs GPU tasks sequentially unless using batches. We will ensure our queuing doesn’t try to run multiple combos in parallel unintentionally (unless the user specifically wanted to use batch size to generate multiple images simultaneously – that’s a different scenario, possibly outside scope of X/Y plot which usually changes parameters per image, not suitable for same-batch generation).
   Model Switching Overhead: As noted, caching models/VAEs will be important if those are varied. We can load all needed models at the start of execution (perhaps by pre-loading them via the Loader node or an API call) to avoid repetitive disk I/O. After the grid, unload any that aren’t needed to free VRAM. This approach will draw from Efficiency’s model caching idea
   runcomfy.com
   .
   Implementation Plan
   We will implement the project in stages: Phase 1: Basic X/Y Plot Node (happy path with one grid).
   Develop the Controller node with support for two axes (X,Y) initially. Focus on a few core parameter types (models, samplers, CFG, steps) to get the mechanism working.
   Implement the queuing of jobs for combinations. Test that we can programmatically queue multiple executions via the ComfyUI API. Ensure the outputs (like different model names) properly feed into the model loader on each run.
   Develop a simple Combiner that accumulates images and once all are received, outputs a grid image (we can use PIL to stitch images in a grid layout for now). Add basic label drawing.
   Test with simple scenarios (vary model vs CFG, etc.) and verify the grid image output and labels.
   Phase 2: Expand to Z axis and more parameters.
   Extend the Controller to handle an optional Z axis loop (probably by nesting another loop or running multiple XY cycles). Ensure multiple grid outputs can be handled (perhaps output a list of images, or sequential outputs; we’ll decide based on ComfyUI capabilities).
   Add UI support for LoRA, VAE, prompts, seed, etc. – this may involve writing helper code to list files (for models, VAEs, LoRAs) and to parse user input lists for numbers or text.
   Incorporate prompt variation logic (maybe a simple whole-prompt swap at first).
   Add Clip skip support (this could be done by connecting to the Checkpoint loader’s clip skip input, if exposed).
   Ensure that multiple parameter types can be varied at once (like one axis numeric, another axis categorical).
   Phase 3: UI Refinement and Polishing.
   Improve the node descriptions, tooltips, and default values for a polished feel. For instance, when the user selects a parameter in the dropdown, we can populate a placeholder or example in the values field to guide them (e.g. “enter comma-separated values”).
   Implement dynamic showing/hiding of fields (using ComfyUI’s dynamic widget support) so the UI is not cluttered with irrelevant inputs
   runcomfy.com
   .
   Add error handling and validation: e.g., if a user leaves a value list empty for a selected axis, show a warning; if the parameter type requires additional setup (like no Checkpoint Loader connected for a model axis), we can detect that and warn.
   Integrate advanced label options: allow the user to specify a custom label list if they really want to override, or perhaps toggle between “Value” vs “Name: Value” label style.
   Aesthetic polish: choose a pleasant default color for the nodes, maybe group them in a custom category in ComfyUI (“XYZ Nodes” category) for easy discovery.
   Phase 4: Optimization and Edge Cases.
   Test edge cases like: only 1 value in an axis (should essentially degenerate to a 1-row or 1-col grid), using the node in an already batched context (probably uncommon), extremely long prompt texts (ensure label doesn’t overflow – wrap text if over a certain length
   github.com
   ).
   If performance of assembling images with PIL is slow for high-res images, consider using the optimized library from images-grid plugin (since QQ-nodes mention injecting that for efficient tiling
   github.com
   ).
   Verify compatibility with SDXL workflows (SDXL has two model passes – base and refiner. Our design should allow varying things in an SDXL pipeline too. Likely it works similarly, but we may test an SDXL prompt vs. something grid).
   Memory test with varying models: ensure model A and B switching does not cause CUDA OOM (maybe unload one before loading next if both can’t reside in VRAM simultaneously – caching on CPU if necessary).
   User abort testing: if user stops midway, next run should be able to reset properly (we’ll implement a reset mechanism possibly triggered by a new execution ID).
   Phase 5: Documentation and Examples.
   Write a user guide with examples (similar to those described above) so users can quickly understand how to use the nodes. Emphasize that no scripting is needed – just connect and go.
   Provide example workflows JSON (perhaps include a few typical ones, like “Model_vs_CFG_XY.json”) as part of the repo.
   Throughout development, we’ll incorporate feedback from testers to ensure the UI is truly intuitive and that we didn’t miss any important use-case. The result will be a robust “XYZ Plot” feature for ComfyUI that dramatically simplifies experimentation.
   Conclusion
   By blending the best aspects of existing solutions and focusing on user-centric design, this project will deliver an XYZ grid comparison tool for ComfyUI that is both powerful and easy to use. Creators will be able to set up complex multi-parameter comparisons in just a few clicks – no coding, no manual stitching. The grids produced will be neatly labeled and customizable, suitable for analyzing results or sharing with others. This fills an important gap in ComfyUI’s toolkit, empowering users to explore models, prompts, and settings efficiently and with confidence in the interface. Ultimately, our custom nodes will make advanced AI art workflows more accessible, turning what was once a manual, error-prone process into a streamlined experience. By supporting everything from model and sampler swaps to subtle parameter tweaks, all in a polished UI, we help users focus on creativity and insight rather than technical hassle. This project plan lays out the path to achieve that goal, and with careful implementation, the “best XYZ plot nodes” for ComfyUI will soon become a reality.
