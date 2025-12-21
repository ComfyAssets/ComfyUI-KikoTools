# Plot Parameters

## Overview
The **Plot Parameters** node creates visual graphs and plots from sampler parameters, enabling data-driven analysis of generation settings. Adapted from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) (now in maintenance mode), this tool helps visualize the relationship between parameters and output quality.

## Attribution
This node is based on work from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) by cubiq. The original project is in maintenance-only mode, and we've adopted and enhanced these tools to ensure continued support and compatibility with modern ComfyUI workflows.

## Features
- **Multi-Parameter Plotting**: Visualize multiple parameters simultaneously
- **Comparison Graphs**: Compare settings across batch runs
- **Statistical Analysis**: Calculate means, deviations, and trends
- **Export Capabilities**: Save plots as images or data files
- **Real-time Updates**: Dynamic graph generation during workflow execution

## Node Properties
- **Category**: `ComfyAssets/🧰 xyz-helpers`
- **Node Name**: `PlotParameters`
- **Function**: `plot`

## Inputs

### Required
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sampler_params` | SAMPLER_PARAMS | - | Parameters to plot |
| `plot_type` | DROPDOWN | line | [line, bar, scatter, heatmap] |
| `x_axis` | DROPDOWN | steps | Parameter for X axis |
| `y_axis` | DROPDOWN | quality | Metric for Y axis |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | STRING | "Parameter Analysis" | Graph title |
| `show_grid` | BOOLEAN | True | Display grid lines |
| `show_legend` | BOOLEAN | True | Display legend |
| `color_scheme` | DROPDOWN | default | Color palette selection |

## Outputs
| Name | Type | Description |
|------|------|-------------|
| `plot_image` | IMAGE | Generated plot as image |
| `data_csv` | STRING | Plot data in CSV format |
| `statistics` | STRING | Statistical summary |

## Usage Examples

### Basic Parameter Visualization
```
FluxSamplerParams → PlotParameters → Display Image
    plot_type: line
    x_axis: steps
    y_axis: guidance
```

### Batch Comparison Plot
```
LoRAFolderBatch → PlotParameters → Save Image
    plot_type: scatter
    x_axis: lora_strength
    y_axis: quality_score
```

### Heatmap Analysis
```
Parameter Grid → PlotParameters → Analysis Display
    plot_type: heatmap
    x_axis: cfg
    y_axis: steps
```

## Plot Types Explained

### Line Plot
- Best for continuous parameter changes
- Shows trends and relationships
- Ideal for time series or progression

### Bar Chart
- Compares discrete values
- Good for categorical comparisons
- Shows distribution clearly

### Scatter Plot
- Reveals correlations
- Identifies outliers
- Best for large datasets

### Heatmap
- Two-dimensional parameter analysis
- Color-coded intensity values
- Perfect for grid searches

## Best Practices

### Parameter Selection
- Choose related parameters for meaningful plots
- Use consistent scales for comparison
- Consider parameter ranges when plotting

### Visual Clarity
- Limit number of series to 5-7 for readability
- Use contrasting colors for multiple lines
- Enable grid for precise value reading

### Data Analysis
```python
# Effective parameter combinations
x_axis: "guidance"
y_axis: "perceived_quality"

# Step efficiency analysis
x_axis: "steps"
y_axis: "generation_time"

# LoRA impact assessment
x_axis: "lora_strength"
y_axis: "style_adherence"
```

## Integration Examples

### Complete Analysis Pipeline
```
1. Generate with parameters
2. Plot results
3. Export data
4. Statistical analysis
```

### Multi-Plot Workflow
```
Params → Plot1 (steps vs quality)
      ↘ Plot2 (guidance vs coherence)
      ↘ Plot3 (strength vs style)
      → Combined Analysis
```

## Advanced Features

### Custom Metrics
- Define custom Y-axis metrics
- Import external quality scores
- Calculate derived values

### Export Options
- PNG/SVG image formats
- CSV data export
- JSON statistics export

### Styling Options
```python
# Professional presentation
color_scheme: "scientific"
show_grid: True
show_legend: True

# Minimal style
color_scheme: "minimal"
show_grid: False
show_legend: False
```

## Statistical Analysis

### Available Metrics
- Mean, Median, Mode
- Standard Deviation
- Correlation Coefficients
- Trend Lines
- R-squared Values

### Interpretation Guide
- **Positive Correlation**: Parameters increase together
- **Negative Correlation**: Inverse relationship
- **No Correlation**: Independent parameters

## Tips and Tricks

### Optimal Visualization
1. Start with scatter plots for exploration
2. Use line plots for trends
3. Apply heatmaps for 2D parameter spaces
4. Bar charts for final comparisons

### Data Preparation
- Normalize scales when comparing different metrics
- Remove outliers for cleaner plots
- Group similar parameters

### Performance Tips
- Cache plot images for repeated viewing
- Export data for external analysis
- Use lower resolution for preview plots

## Troubleshooting

### Empty Plots
- Verify sampler_params contains data
- Check axis parameter selection
- Ensure valid parameter ranges

### Scaling Issues
- Use logarithmic scale for wide ranges
- Normalize data if needed
- Adjust plot dimensions

### Export Problems
- Check file permissions
- Verify export path exists
- Ensure sufficient disk space

## Use Cases

### Hyperparameter Optimization
Track and visualize the effect of different sampling parameters on output quality.

### LoRA Strength Analysis
Plot the relationship between LoRA strength and style transfer effectiveness.

### Efficiency Studies
Analyze generation time vs quality trade-offs across different settings.

### Batch Comparison
Compare multiple generation runs to identify optimal parameters.

## Version History
- **1.0.0**: Initial adaptation from comfyui-essentials-nodes
- **1.0.1**: Added heatmap visualization
- **1.0.2**: Enhanced statistical analysis
- **1.0.3**: Improved export capabilities

## Credits
Original implementation by cubiq in [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials). Adapted and maintained by the ComfyAssets team.
