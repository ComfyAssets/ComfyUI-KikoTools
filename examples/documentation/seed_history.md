# Seed History Tool

The Seed History tool provides advanced seed value tracking with an interactive UI for managing seed history, automatic deduplication, and convenient seed retrieval.

## Overview

The Seed History node functions as both a standard seed input and an intelligent tracking system that automatically monitors seed changes and maintains a searchable history.

## Features

### 🎲 Core Functionality
- **Seed Output**: Standard ComfyUI seed value output (0 to 18,446,744,073,709,551,615)
- **History Tracking**: Automatic tracking of all seed changes with timestamps
- **Deduplication**: Intelligent filtering to prevent duplicate entries within 500ms windows
- **Persistent Storage**: History persists across ComfyUI sessions using localStorage

### 🎯 Interactive UI
- **History Display**: Scrollable list showing recent seeds with timestamps
- **Click to Load**: Click any history entry to instantly load that seed
- **Generate Button**: Create new random seeds with one click
- **Clear History**: Remove all tracked seeds when needed
- **Auto-Hide**: History section automatically hides after 2.5 seconds of inactivity

### ⚡ Smart Features
- **Real-time Updates**: Tracks seed changes from increment/decrement buttons
- **Visual Feedback**: Selected seeds are highlighted in green
- **Time Formatting**: Human-readable "time ago" display (e.g., "5m ago", "2h ago")
- **Notifications**: Toast messages for actions like generate and clear
- **Responsive Design**: Adapts to node resizing

## Usage

### Basic Setup

1. **Add Node**: Search for "Seed History" in the ComfyUI node browser
2. **Connect Output**: Connect the seed output to any node requiring a seed input
3. **Automatic Tracking**: The node automatically begins tracking seed changes

### Seed Management

```
🎲 Seed History
┌─────────────────┐
│ 🎲 Generate │ 🗑️ Clear │
├─────────────────┤
│ 🎲 1,234,567    │ ← Click to load
│ ⏰ 2m ago       │
├─────────────────┤
│ 🎲 9,876,543    │
│ ⏰ 5m ago       │
├─────────────────┤
│ 🎲 5,555,555    │
│ ⏰ 10m ago      │
└─────────────────┘
```

### Workflow Integration

The Seed History node works seamlessly with any ComfyUI workflow:

```
[Seed History] → [KSampler] → [Image Output]
     ↓
[VAE Decode] → [Save Image]
```

## Advanced Features

### History Management
- **Maximum Entries**: Keeps the 10 most recent seeds
- **Smart Deduplication**: Prevents rapid duplicate additions
- **Timestamp Tracking**: Full date/time information for each seed
- **Persistent Storage**: History survives ComfyUI restarts

### UI Behavior
- **Auto-Hide Timer**: History hides after 2.5 seconds of inactivity
- **Mouse Interaction**: Hovering over history cancels auto-hide
- **Restore Button**: Click to restore hidden history section
- **Visual Feedback**: Hover effects and selection highlighting

### Seed Validation
- **Range Checking**: Ensures seeds are within valid ComfyUI range
- **Error Handling**: Graceful fallback to default seed (12345) on errors
- **Sanitization**: Automatic clamping of out-of-range values

## Technical Details

### Input Parameters
- **seed** (INT): Seed value for generation processes
  - Range: 0 to 18,446,744,073,709,551,615
  - Default: 12345
  - Tooltip: "Seed value for generation processes. History UI tracks all changes automatically."

### Output
- **seed** (INT): The processed seed value for use in other nodes

### Storage
- **Key**: `comfyui_kikotools_seed_history`
- **Format**: JSON array of history entries
- **Location**: Browser localStorage
- **Persistence**: Survives browser sessions and ComfyUI restarts

## Use Cases

### 🎨 Creative Workflows
- **Iteration Tracking**: Keep track of promising seeds during creative exploration
- **Version Control**: Easily return to previous seeds that produced good results
- **Experimentation**: Generate and track multiple seed variations

### 🔬 Technical Workflows
- **Reproducibility**: Maintain exact seed records for reproducing specific outputs
- **A/B Testing**: Compare results from different seeds with easy switching
- **Documentation**: Export seed history for technical documentation

### 📊 Batch Processing
- **Seed Management**: Track seeds across multiple batch runs
- **Quality Control**: Quickly identify and reuse successful seeds
- **Workflow Optimization**: Analyze seed performance patterns

## Tips and Best Practices

### Efficient Usage
1. **Let it Track**: The node automatically tracks all seed changes - no manual intervention needed
2. **Use Generate**: The generate button is optimized for creating good random seeds
3. **Regular Clearing**: Clear history periodically to maintain relevant seeds only

### Workflow Integration
1. **Single Source**: Use one Seed History node per workflow for centralized tracking
2. **Connect Early**: Place the node early in your workflow chain for complete tracking
3. **Branch Connections**: Connect to multiple nodes that need the same seed

### History Management
1. **Review Regularly**: Check history for seeds that produced good results
2. **Document Success**: Note down particularly successful seeds externally
3. **Clean Periodically**: Clear history when starting new creative projects

## Troubleshooting

### Common Issues

**History Not Updating**
- Ensure the node is properly connected to your workflow
- Check that seed widget is visible and functional
- Verify browser localStorage is enabled

**UI Not Appearing**
- Check browser console for JavaScript errors
- Ensure ComfyUI-KikoTools is properly installed
- Verify web directory permissions

**Seeds Not Loading**
- Confirm the seed is within valid range
- Check that target widgets support the seed value
- Verify node connections are intact

### Performance Notes
- History is limited to 10 entries for optimal performance
- Deduplication prevents excessive storage usage
- Auto-hide reduces visual clutter during long workflows

## Examples

See the `examples/workflows/` directory for complete workflow examples demonstrating:
- Basic seed tracking workflow
- Creative iteration with history
- Technical reproducibility setup
- Batch processing with seed management
