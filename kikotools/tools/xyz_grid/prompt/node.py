"""XYZ Prompt node for managing multiple prompt variations."""

from typing import Dict, List, Any, Tuple


class FlexibleOptionalInputType(dict):
    """Special input type that accepts any dynamic widget values from JavaScript."""
    def __contains__(self, key):
        return True
    
    def __getitem__(self, key):
        # Accept string inputs for dynamic prompts
        return ("STRING", {"multiline": True, "forceInput": False})


class XYZPrompt:
    """XYZ Prompt node for creating prompt variations for grid generation."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "include_negative": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Include negative prompt inputs"
                }),
                "repeat_negative": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Use the first negative prompt for all variations"
                }),
            },
            "optional": FlexibleOptionalInputType()
        }
    
    RETURN_TYPES = ("XYZ_PROMPTS", "STRING", "STRING", "INT")
    RETURN_NAMES = ("prompts", "positive", "negative", "count")
    OUTPUT_NODE = True
    FUNCTION = "process_prompts"
    CATEGORY = "ComfyAssets/XYZ Grid"
    
    def process_prompts(self, include_negative=True, repeat_negative=True, **kwargs):
        """Process all prompt inputs and return them formatted for XYZ grid.
        
        Args:
            include_negative: Whether to include negative prompts
            repeat_negative: Whether to use first negative for all prompts
            **kwargs: Dynamic prompt inputs from JavaScript
            
        Returns:
            Tuple of (prompts dict, first positive, first negative, count)
        """
        # Debug: Log all received kwargs
        print(f"XYZPrompt.process_prompts - Received kwargs: {kwargs}")
        print(f"XYZPrompt.process_prompts - include_negative: {include_negative}, repeat_negative: {repeat_negative}")
        
        prompts = []
        first_negative = ""
        
        # Collect all prompt pairs from kwargs
        prompt_index = 0
        while True:
            pos_key = f"positive_{prompt_index}"
            neg_key = f"negative_{prompt_index}"
            
            if pos_key not in kwargs:
                break
                
            positive = kwargs.get(pos_key, "")
            
            # Handle negative prompt based on settings
            if include_negative:
                if repeat_negative:
                    # Use first negative for all
                    if prompt_index == 0:
                        first_negative = kwargs.get(neg_key, "")
                    negative = first_negative
                else:
                    # Each prompt has its own negative
                    negative = kwargs.get(neg_key, "")
            else:
                negative = ""
            
            if positive:  # Only add if positive prompt exists
                prompts.append({
                    "positive": positive,
                    "negative": negative
                })
            
            prompt_index += 1
        
        # Prepare outputs
        first_positive = prompts[0]["positive"] if prompts else ""
        first_negative = prompts[0]["negative"] if prompts else ""
        
        result = {
            "prompts": prompts,
            "include_negative": include_negative,
            "count": len(prompts)
        }
        
        # Return for UI display
        return {
            "ui": {
                "prompts": result
            },
            "result": (result, first_positive, first_negative, len(prompts))
        }