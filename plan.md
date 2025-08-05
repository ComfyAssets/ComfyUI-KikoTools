# ComfyUI-KikoTools XYZ Grid Development Plan

## Current Session Context (2025-08-05)

### Working Branch: `feature/xyz-nodes`

### Completed Work

#### 1. XYZ Plot Controller
- ✅ Implemented dynamic widget management with RGThree-style interface
- ✅ Added right-click context menus (Toggle, Move Up/Down, Remove)
- ✅ Fixed text input removal that was leaving DOM elements behind
- ✅ Added placeholder hints for text inputs
- ✅ Auto-resize nodes when adding widgets
- ✅ Removed unwanted "input" connection from node
- ✅ Fixed image count calculation for step ranges (e.g., "10:50:5")
- ✅ Added callbacks to update node title with image count

#### 2. XYZ Prompt Node
- ✅ Created separate node for prompt management
- ✅ Implemented dynamic prompt set addition/removal
- ✅ Added include_negative toggle for showing/hiding negative prompts
- ✅ Added repeat_negative feature (use first negative for all variations)
- ✅ Fixed spacing issues with protected button containers
- ✅ Fixed widget values not passing to Python backend (added FlexibleOptionalInputType)
- ✅ Visual styling: green background for positive, red for negative prompts

#### 3. ImageGridCombiner
- ✅ Fixed grid_data structure mismatch with controller
- ✅ Added proper dimensions object (cols, rows, grids_count)
- ✅ Added axes object with human-readable labels
- ✅ Created _create_labels method for formatting axis values

### Current Issues

#### 1. XYZ Prompt Widget Restoration Bug
**Problem**: When refreshing the page, prompts aren't properly restored
- Negative prompt appears at top with saved value
- Positive prompts are lost
- Widget restoration from widgets_values array not working correctly

**Current Fix Attempt**:
- Modified onConfigure to properly clean up dynamic widgets
- Added debug logging to trace restoration
- Using promptData to track number of prompt sets
- Need to properly handle widgets_values array restoration

#### 2. Pending Tasks (from todo list)
- Complete queue implementation for actual ComfyUI API integration
- Remove debug logging from production JavaScript
- Add validation for invalid axis combinations

### File Structure

```
ComfyUI-KikoTools/
├── kikotools/
│   └── tools/
│       └── xyz_grid/
│           ├── controller/
│           │   ├── power_node.py (Main XYZ Plot Controller)
│           │   ├── queue_manager.py (Placeholder - needs implementation)
│           │   └── execution.py
│           ├── prompt/
│           │   └── node.py (XYZ Prompt node)
│           ├── combiner/
│           │   └── node.py (ImageGridCombiner)
│           └── __init__.py
├── web/
│   ├── xyz_plot_controller.js (Dynamic widget UI)
│   ├── xyz_prompt.js (Prompt management UI)
│   └── disabled/ (Old implementations)
└── examples/
    └── xyz_grid_test_workflow.json (Test workflow)
```

### Key Technical Patterns

#### Python Node Pattern
```python
class FlexibleOptionalInputType(dict):
    """Accepts dynamic widget values from JavaScript."""
    def __contains__(self, key):
        return True
    def __getitem__(self, key):
        return ("STRING", {"multiline": True, "forceInput": False})

# In INPUT_TYPES:
"optional": FlexibleOptionalInputType()
```

#### JavaScript Widget Creation
```javascript
const widget = ComfyWidgets.STRING(
    this, 
    widgetName, 
    ["STRING", config], 
    app
).widget;
```

#### RGThree-style Context Menu
```javascript
getSlotInPosition(x, y) {
    // Return fake slot with widget for context menu
    const widget = this.findWidgetAtPosition(x, y);
    if (widget) {
        return {
            slot_index: -1,
            widget: widget
        };
    }
}

getSlotMenuOptions(slot) {
    if (slot?.widget) {
        return this.getWidgetMenuOptions(slot.widget);
    }
}
```

### Git Commands for Session Recovery

```bash
# Switch to working branch
git checkout feature/xyz-nodes

# Check current status
git status

# Recent commits
git log --oneline -10

# Current changes
git diff
```

### Testing Instructions

1. Load ComfyUI
2. Refresh browser (F5)
3. Add XYZ Prompt node
4. Add multiple prompts
5. Save workflow
6. Refresh page
7. Check if prompts are restored correctly

### Debug Points

1. Check browser console for debug logs from:
   - `XYZ Prompt onConfigure`
   - `XYZ Prompt serialize`
   - Widget creation logs

2. Monitor Python console for:
   - `XYZPrompt.process_prompts` kwargs
   - Grid data structure output

### Next Steps

1. **Fix widget restoration**: 
   - Properly handle widgets_values array
   - Ensure widget values are restored in correct order
   - Test with multiple prompt sets

2. **Clean up debug code**:
   - Remove console.log statements
   - Remove print statements in Python

3. **Complete queue manager**:
   - Implement actual ComfyUI API integration
   - Handle batch execution properly

4. **Add validation**:
   - Prevent same parameter on multiple axes
   - Validate numeric ranges
   - Check model/VAE/LoRA availability

### Important Notes

- CLAUDE.md is in .gitignore (local only)
- Main branch is `main` for PRs
- Test with actual checkpoint files before merging
- Memory management for large grids needs optimization
- Performance concerns with many dynamic widgets

### Session Recovery Command

To continue work in new terminal:
```bash
cd /home/vito/code/personal/ComfyUI-KikoTools
git checkout feature/xyz-nodes
# Check this plan.md for context
```