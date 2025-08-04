"""Tests for cache manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import torch
from kikotools.tools.xyz_grid.utils.cache_manager import ModelCacheManager


class TestModelCacheManager:
    """Test ModelCacheManager class."""
    
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.mem_get_info')
    def test_get_available_memory_gpu(self, mock_mem_info, mock_cuda_available):
        """Test GPU memory detection."""
        mock_cuda_available.return_value = True
        mock_mem_info.return_value = (4 * 1024**3, 8 * 1024**3)  # 4GB free, 8GB total
        
        manager = ModelCacheManager()
        free, total = manager.get_available_memory()
        
        assert free == 4 * 1024**3
        assert total == 8 * 1024**3
    
    @patch('torch.cuda.is_available')
    @patch('psutil.virtual_memory')
    def test_get_available_memory_cpu(self, mock_vm, mock_cuda_available):
        """Test CPU memory fallback."""
        mock_cuda_available.return_value = False
        mock_vm.return_value = MagicMock(available=16 * 1024**3, total=32 * 1024**3)
        
        manager = ModelCacheManager()
        free, total = manager.get_available_memory()
        
        assert free == 16 * 1024**3
        assert total == 32 * 1024**3
    
    @patch.object(ModelCacheManager, 'get_available_memory')
    def test_should_cache(self, mock_memory):
        """Test cache decision logic."""
        manager = ModelCacheManager()
        
        # Plenty of memory available
        mock_memory.return_value = (6 * 1024**3, 8 * 1024**3)  # 6GB free, 8GB total
        assert manager.should_cache(2 * 1024**3)  # 2GB model
        
        # Not enough memory
        mock_memory.return_value = (1 * 1024**3, 8 * 1024**3)  # 1GB free, 8GB total
        assert not manager.should_cache(2 * 1024**3)  # 2GB model would exceed threshold
        
        # No memory info
        mock_memory.return_value = (0, 0)
        assert not manager.should_cache()
    
    @patch.object(ModelCacheManager, 'should_cache')
    def test_cache_model(self, mock_should_cache):
        """Test model caching."""
        manager = ModelCacheManager(max_cache_size=2)
        mock_should_cache.return_value = True
        
        # Cache first model
        model1 = Mock()
        assert manager.cache_model("model1", model1)
        assert manager.get_cached_model("model1") == model1
        
        # Cache second model
        model2 = Mock()
        assert manager.cache_model("model2", model2)
        assert len(manager.model_cache) == 2
        
        # Cache third model - should evict oldest
        model3 = Mock()
        assert manager.cache_model("model3", model3)
        assert len(manager.model_cache) == 2
        assert "model1" not in manager.model_cache
        assert "model3" in manager.model_cache
    
    def test_get_cached_model_updates_lru(self):
        """Test that getting a model updates LRU order."""
        manager = ModelCacheManager(max_cache_size=2)
        
        # Add two models
        with patch.object(manager, 'should_cache', return_value=True):
            manager.cache_model("model1", "m1")
            manager.cache_model("model2", "m2")
        
        # Access model1 to make it most recent
        manager.get_cached_model("model1")
        
        # Add third model - should evict model2, not model1
        with patch.object(manager, 'should_cache', return_value=True):
            manager.cache_model("model3", "m3")
        
        assert "model1" in manager.model_cache
        assert "model2" not in manager.model_cache
        assert "model3" in manager.model_cache
    
    @patch('gc.collect')
    @patch('torch.cuda.empty_cache')
    @patch('torch.cuda.is_available')
    def test_uncache_model(self, mock_cuda, mock_empty_cache, mock_gc):
        """Test model uncaching and cleanup."""
        mock_cuda.return_value = True
        manager = ModelCacheManager()
        
        # Create mock model with 'to' method
        model = Mock()
        model.to = Mock()
        
        with patch.object(manager, 'should_cache', return_value=True):
            manager.cache_model("model1", model)
        
        # Uncache
        manager.uncache_model("model1")
        
        # Verify cleanup
        assert "model1" not in manager.model_cache
        model.to.assert_called_with('cpu')
        mock_gc.assert_called_once()
        mock_empty_cache.assert_called_once()
    
    def test_optimize_for_grid(self):
        """Test grid optimization suggestions."""
        manager = ModelCacheManager()
        
        with patch.object(manager, 'get_available_memory') as mock_memory:
            # Enough memory for everything
            mock_memory.return_value = (10 * 1024**3, 16 * 1024**3)
            suggestions = manager.optimize_for_grid(
                ["model1", "model2", "model1"],
                ["vae1", "vae1", "vae1"]
            )
            
            assert suggestions["cache_all_models"]
            assert suggestions["cache_all_vaes"]
            assert suggestions["memory_sufficient"]
            
            # Not enough memory
            mock_memory.return_value = (1 * 1024**3, 8 * 1024**3)
            suggestions = manager.optimize_for_grid(
                ["model1", "model2", "model3"],
                ["vae1", "vae2"]
            )
            
            assert not suggestions["cache_all_models"]
            assert not suggestions["memory_sufficient"]
            assert len(suggestions["recommended_order"]) > 0
    
    def test_optimize_load_order(self):
        """Test load order optimization."""
        manager = ModelCacheManager()
        
        # Test grouping
        items = ["a", "b", "a", "c", "b", "a"]
        optimized = manager._optimize_load_order(items)
        
        # Should group all a's, then b's, then c
        assert optimized == ["a", "a", "a", "b", "b", "c"]
        
        # Test with single item type
        items = ["x", "x", "x"]
        optimized = manager._optimize_load_order(items)
        assert optimized == ["x", "x", "x"]
    
    @patch('gc.collect')
    @patch('torch.cuda.empty_cache')
    @patch('torch.cuda.is_available')
    def test_clear_cache(self, mock_cuda, mock_empty_cache, mock_gc):
        """Test clearing all caches."""
        mock_cuda.return_value = True
        manager = ModelCacheManager()
        
        # Add some items to caches
        with patch.object(manager, 'should_cache', return_value=True):
            manager.cache_model("model1", Mock())
            manager.cache_vae("vae1", Mock())
        
        manager.lora_cache["lora1"] = Mock()
        
        # Clear all
        manager.clear_cache()
        
        assert len(manager.model_cache) == 0
        assert len(manager.vae_cache) == 0
        assert len(manager.lora_cache) == 0
        assert mock_gc.called
        assert mock_empty_cache.called
    
    def test_get_cache_stats(self):
        """Test cache statistics."""
        manager = ModelCacheManager()
        
        with patch.object(manager, 'get_available_memory') as mock_memory:
            mock_memory.return_value = (4 * 1024**3, 8 * 1024**3)
            
            # Add some cached items
            with patch.object(manager, 'should_cache', return_value=True):
                manager.cache_model("model1", Mock())
                manager.cache_vae("vae1", Mock())
            
            stats = manager.get_cache_stats()
            
            assert stats["models_cached"] == 1
            assert stats["vaes_cached"] == 1
            assert stats["memory_free"] == 4 * 1024**3
            assert stats["memory_total"] == 8 * 1024**3
            assert stats["memory_usage"] == 0.5
            assert "model1" in stats["cache_names"]["models"]
            assert "vae1" in stats["cache_names"]["vaes"]