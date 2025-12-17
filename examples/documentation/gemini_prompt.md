# Gemini Prompt Engineer

The Gemini Prompt Engineer node uses Google's Gemini AI to analyze images and generate optimized prompts for various AI image generation models.

## Features

- **Multi-Model Support**: Generate prompts optimized for FLUX, SDXL, Danbooru, and Video generation
- **Custom Prompts**: Override templates with your own system prompts
- **Visual Feedback**: UI shows processing status and error states
- **Flexible API Key Management**: Multiple ways to provide API credentials
- **Dynamic Model Selection**: Fetch and use latest Gemini models with refresh button
- **Model Caching**: Persistent storage of available models for offline access
- **Help Integration**: Built-in setup guide accessible via help button

## Setup

### 1. Get API Key

Get your free Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Install Dependencies

```bash
pip install google-generativeai
```

### 3. Configure API Key

Choose one of these methods:

1. **Environment Variable** (Recommended):
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

2. **Config File**:
   Create `gemini_config.json` in your ComfyUI root directory:
   ```json
   {
     "api_key": "your-api-key-here"
   }
   ```

3. **Node Input**:
   Enter the API key directly in the node's `api_key` field

## Inputs

- **image** (IMAGE): The image to analyze
- **prompt_type** (DROPDOWN): Type of prompt to generate
  - `flux`: Detailed artistic prompts with quality markers
  - `sdxl`: Positive/negative prompt pairs with weight emphasis
  - `danbooru`: Anime-style booru tags with underscores
  - `video`: Motion and temporal descriptions for video generation
- **model** (DROPDOWN): Gemini model selection
  - Dynamically populated list of available models
  - Includes latest models like gemini-2.0-flash-exp
  - Click refresh button to update model list
- **api_key** (STRING, optional): Gemini API key if not set elsewhere
- **custom_prompt** (STRING, optional): Override template with custom system prompt

## Outputs

- **prompt** (STRING): Generated prompt text
- **negative_prompt** (STRING): Negative prompt (only populated for SDXL format)

## Prompt Type Details

### FLUX Format
Generates detailed prompts optimized for FLUX models:
- Starts with main subject and action
- Includes style and medium descriptors
- Adds lighting and atmosphere details
- Uses quality markers like "4K", "highly detailed", "award-winning"

Example output:
```
majestic mountain landscape at golden hour, oil painting style, dramatic lighting with sun rays piercing through clouds, wide angle composition, warm color palette with orange and purple hues, highly detailed, 4K resolution, trending on ArtStation, photorealistic rendering
```

### SDXL Format
Generates positive and negative prompt pairs with enhanced structure:
- Layered positive prompts: main subject → style → composition → technical
- Comprehensive negative prompts to avoid common issues
- Uses parentheses for emphasis: `(detailed eyes:1.2)`
- Includes quality boosters and technical specifications

Example output:
```
Positive prompt:
beautiful woman with flowing red hair, elegant pose, (detailed eyes:1.2), serene expression
oil painting style, renaissance art influence, classical portraiture
golden hour lighting, warm color palette, soft shadows, dramatic chiaroscuro
centered composition, rule of thirds, shallow depth of field, bokeh background
masterpiece, best quality, highly detailed, 8k uhd, professional artwork

Negative prompt:
low quality, worst quality, blurry, out of focus, pixelated, low resolution
bad anatomy, deformed features, extra limbs, missing limbs, disconnected limbs
poorly drawn face, poorly drawn hands, amateur drawing, bad proportions
oversaturated, overexposed, underexposed, bad lighting, harsh shadows
jpeg artifacts, watermark, signature, text, cropped, duplicate
```

### Danbooru Format
Generates booru-style tags for anime artwork:
- Uses underscores for multi-word concepts
- Includes character count descriptors (1girl, 2boys)
- Orders tags from most to least important

Example output:
```
1girl, solo, long_hair, blue_eyes, blonde_hair, school_uniform, serafuku, pleated_skirt, thighhighs, smile, looking_at_viewer, classroom, sitting, desk, window, sunlight, highres, masterpiece
```

### Video Format
Generates prompts for video generation models:
- Describes motion and camera movements
- Includes temporal markers and transitions
- Specifies technical details like fps and duration

Example output:
```
Aerial shot slowly descending toward a misty forest at dawn, camera smoothly transitions to tracking shot following a deer through the trees, photorealistic style, soft golden hour lighting with fog, 10 second duration, 4K resolution 24fps, ending with close-up of deer looking at camera
```

## Custom System Prompts

You can override any template by providing your own system prompt. This is useful for:
- Specialized use cases
- Different language outputs
- Custom formatting requirements
- Integration with specific workflows

Example custom prompt:
```
You are an expert at analyzing images and creating simple, concise descriptions.
Focus only on the main subject and primary colors.
Keep your response under 50 words.
```

## Error Handling

The node provides clear error messages for common issues:
- Missing API key
- API request failures
- Invalid image inputs
- Rate limiting

Errors are displayed in the prompt output for easy debugging.

## Model Selection

### Dynamic Model List
- Click the refresh button (🔄) next to the model dropdown to fetch latest models
- Models are fetched from Google's API and include all available versions
- Common models include:
  - `gemini-2.0-flash-exp`: Latest experimental flash model
  - `gemini-1.5-pro`: Advanced model with larger context
  - `gemini-1.5-flash`: Fast and efficient for most tasks

### Model Caching
- Available models are cached locally for offline access
- Cache persists across ComfyUI sessions
- Refresh button updates the cache with latest models

## UI Features

### Help Button
- Click the help button (?) for quick setup instructions
- Shows API key setup methods
- Links to Google AI Studio for key generation

### Status Indicators
- Processing spinner during API calls
- Error messages displayed in red
- Success feedback when prompt is generated

## Tips

1. **API Usage**: Gemini has generous free tier limits, but be mindful of rate limits
2. **Image Quality**: Higher resolution images provide better analysis results
3. **Prompt Refinement**: You can chain multiple Gemini nodes with different custom prompts
4. **Caching**: Results are not cached, so identical images will make new API calls
5. **Model Selection**: Use flash models for faster responses, pro models for complex analysis

## Example Workflow

1. Load an image using Load Image node
2. Connect to Gemini Prompt Engineer
3. Select appropriate prompt_type for your target model
4. Connect prompt output to your generation model
5. For SDXL, connect both prompt and negative_prompt outputs

## Troubleshooting

**"API key not found" error**:
- Check environment variable is set correctly
- Verify config file path and JSON format
- Try entering key directly in node

**"No response generated" error**:
- Check internet connection
- Verify API key is valid
- Image might be too large (resize if needed)

**Import error for google-generativeai**:
- Run `pip install google-generativeai` in your ComfyUI environment
- Restart ComfyUI after installation
