#!/usr/bin/env python3
"""Test script to check how ComfyUI returns embedding paths."""

import sys
import os

# Add ComfyUI to path if available
comfyui_path = os.path.expanduser("~/ComfyUI")
if os.path.exists(comfyui_path):
    sys.path.insert(0, comfyui_path)

try:
    import folder_paths

    print("Testing embedding paths...")
    print("=" * 50)

    # Get embeddings
    embeddings = folder_paths.get_filename_list("embeddings")
    print(f"Total embeddings found: {len(embeddings)}")
    print("\nFirst 20 embeddings:")
    for i, emb in enumerate(embeddings[:20]):
        print(f"  {i+1}. '{emb}'")

    print("\n" + "=" * 50)
    print("Checking for path separators...")
    has_paths = any("/" in emb or "\\" in emb for emb in embeddings)
    print(f"Contains path separators: {has_paths}")

    if has_paths:
        print("\nEmbeddings with paths:")
        for emb in embeddings[:10]:
            if "/" in emb or "\\" in emb:
                print(f"  - {emb}")

except ImportError as e:
    print(f"Could not import folder_paths: {e}")
    print("\nThis script should be run from within ComfyUI environment")
