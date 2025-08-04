"""Model and resource caching for performance optimization."""

import gc
import torch
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
import psutil

try:
    import folder_paths
    import comfy.model_management
except ImportError:
    # Not in ComfyUI environment
    folder_paths = None
    comfy = None


class ModelCacheManager:
    """Manages model caching for XYZ grid generation."""
    
    def __init__(self, max_cache_size: int = 3):
        """Initialize cache manager.
        
        Args:
            max_cache_size: Maximum number of models to keep in cache
        """
        self.max_cache_size = max_cache_size
        self.model_cache: OrderedDict[str, Any] = OrderedDict()
        self.vae_cache: OrderedDict[str, Any] = OrderedDict()
        self.lora_cache: OrderedDict[str, Any] = OrderedDict()
        self.memory_threshold = 0.85  # Use up to 85% of VRAM
    
    def get_available_memory(self) -> Tuple[int, int]:
        """Get available GPU memory in bytes.
        
        Returns:
            Tuple of (free_memory, total_memory)
        """
        try:
            if torch.cuda.is_available():
                free, total = torch.cuda.mem_get_info()
                return free, total
            else:
                # Fallback to system RAM
                mem = psutil.virtual_memory()
                return mem.available, mem.total
        except:
            return 0, 0
    
    def should_cache(self, model_size_estimate: int = 2 * 1024**3) -> bool:
        """Check if we should cache based on available memory.
        
        Args:
            model_size_estimate: Estimated model size in bytes (default 2GB)
            
        Returns:
            True if caching is safe
        """
        free, total = self.get_available_memory()
        if total == 0:
            return False
        
        # Check if we have enough free memory
        usage_after_cache = (total - free + model_size_estimate) / total
        return usage_after_cache < self.memory_threshold
    
    def cache_model(self, model_name: str, model: Any) -> bool:
        """Cache a model if memory allows.
        
        Args:
            model_name: Name/path of the model
            model: The loaded model object
            
        Returns:
            True if cached successfully
        """
        if not self.should_cache():
            return False
        
        # Remove oldest if cache is full
        if len(self.model_cache) >= self.max_cache_size:
            oldest = next(iter(self.model_cache))
            self.uncache_model(oldest)
        
        self.model_cache[model_name] = model
        self.model_cache.move_to_end(model_name)  # Mark as recently used
        return True
    
    def get_cached_model(self, model_name: str) -> Optional[Any]:
        """Get a model from cache if available.
        
        Args:
            model_name: Name/path of the model
            
        Returns:
            Cached model or None
        """
        if model_name in self.model_cache:
            self.model_cache.move_to_end(model_name)  # Mark as recently used
            return self.model_cache[model_name]
        return None
    
    def uncache_model(self, model_name: str) -> None:
        """Remove a model from cache and free memory.
        
        Args:
            model_name: Name/path of the model to remove
        """
        if model_name in self.model_cache:
            model = self.model_cache.pop(model_name)
            # Attempt to free GPU memory
            if hasattr(model, 'to'):
                try:
                    model.to('cpu')
                except:
                    pass
            del model
            
            # Force garbage collection
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def cache_vae(self, vae_name: str, vae: Any) -> bool:
        """Cache a VAE model."""
        if not self.should_cache(model_size_estimate=500 * 1024**2):  # VAEs are smaller
            return False
        
        if len(self.vae_cache) >= self.max_cache_size:
            oldest = next(iter(self.vae_cache))
            self.uncache_vae(oldest)
        
        self.vae_cache[vae_name] = vae
        self.vae_cache.move_to_end(vae_name)
        return True
    
    def get_cached_vae(self, vae_name: str) -> Optional[Any]:
        """Get a VAE from cache."""
        if vae_name in self.vae_cache:
            self.vae_cache.move_to_end(vae_name)
            return self.vae_cache[vae_name]
        return None
    
    def uncache_vae(self, vae_name: str) -> None:
        """Remove a VAE from cache."""
        if vae_name in self.vae_cache:
            vae = self.vae_cache.pop(vae_name)
            del vae
            gc.collect()
    
    def optimize_for_grid(self, model_names: List[str], vae_names: List[str]) -> Dict[str, Any]:
        """Pre-optimize caching for a grid generation.
        
        Args:
            model_names: List of models that will be used
            vae_names: List of VAEs that will be used
            
        Returns:
            Dict with optimization suggestions
        """
        suggestions = {
            "cache_all_models": False,
            "cache_all_vaes": False,
            "recommended_order": [],
            "memory_sufficient": True
        }
        
        # Estimate total memory needed
        model_count = len(set(model_names))
        vae_count = len(set(vae_names))
        
        estimated_model_size = model_count * 2 * 1024**3  # 2GB per model
        estimated_vae_size = vae_count * 500 * 1024**2  # 500MB per VAE
        total_needed = estimated_model_size + estimated_vae_size
        
        free, total = self.get_available_memory()
        
        if free > total_needed * 1.2:  # 20% safety margin
            suggestions["cache_all_models"] = True
            suggestions["cache_all_vaes"] = True
        elif free > estimated_model_size * 1.2:
            suggestions["cache_all_models"] = True
        else:
            suggestions["memory_sufficient"] = False
            
            # Suggest loading order to minimize switches
            model_order = self._optimize_load_order(model_names)
            suggestions["recommended_order"] = model_order
        
        return suggestions
    
    def _optimize_load_order(self, items: List[str]) -> List[str]:
        """Optimize loading order to minimize model switches.
        
        Args:
            items: List of items (may have duplicates)
            
        Returns:
            Optimized order
        """
        # Group consecutive items together
        optimized = []
        seen = set()
        
        for item in items:
            if item not in seen:
                # Add all instances of this item consecutively
                count = items.count(item)
                optimized.extend([item] * count)
                seen.add(item)
        
        return optimized
    
    def clear_cache(self) -> None:
        """Clear all caches and free memory."""
        # Clear model cache
        for model_name in list(self.model_cache.keys()):
            self.uncache_model(model_name)
        
        # Clear VAE cache
        for vae_name in list(self.vae_cache.keys()):
            self.uncache_vae(vae_name)
        
        # Clear LoRA cache
        self.lora_cache.clear()
        
        # Force cleanup
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get current cache statistics."""
        free, total = self.get_available_memory()
        
        return {
            "models_cached": len(self.model_cache),
            "vaes_cached": len(self.vae_cache),
            "loras_cached": len(self.lora_cache),
            "memory_free": free,
            "memory_total": total,
            "memory_usage": (total - free) / total if total > 0 else 0,
            "cache_names": {
                "models": list(self.model_cache.keys()),
                "vaes": list(self.vae_cache.keys()),
                "loras": list(self.lora_cache.keys())
            }
        }


# Global cache manager instance
cache_manager = ModelCacheManager()