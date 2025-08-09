#!/usr/bin/env python3
"""Test what folder_paths.get_filename_list actually returns."""

import sys
import os

# Add ComfyUI to path
comfyui_path = "/home/vito/ai-apps/ComfyUI-3.12"
if os.path.exists(comfyui_path):
    sys.path.insert(0, comfyui_path)
    # Set the working directory for folder_paths
    os.environ["COMFYUI_PATH"] = comfyui_path

    try:
        import folder_paths

        print("Testing folder_paths.get_filename_list('embeddings')...")
        print("=" * 60)

        embeddings = folder_paths.get_filename_list("embeddings")
        print(f"Total embeddings: {len(embeddings)}")

        print("\nFirst 10 embeddings:")
        for i, emb in enumerate(embeddings[:10]):
            print(f"  {i+1}. '{emb}'")

        # Check if any have paths
        with_paths = [e for e in embeddings if "/" in e or "\\" in e]
        print(f"\nEmbeddings with path separators: {len(with_paths)}")
        if with_paths:
            print("Examples:")
            for e in with_paths[:5]:
                print(f"  - '{e}'")

        # Check the actual folder structure
        print("\n" + "=" * 60)
        print("Checking actual folder structure...")
        emb_folders = folder_paths.get_folder_paths("embeddings")
        print(f"Embedding folders: {emb_folders}")

        if emb_folders:
            emb_dir = emb_folders[0]
            print(f"\nContents of {emb_dir}:")
            for root, dirs, files in os.walk(emb_dir):
                rel_root = os.path.relpath(root, emb_dir)
                if rel_root == ".":
                    rel_root = ""
                for f in files[:5]:  # Show first 5 files in each dir
                    if f.endswith((".pt", ".safetensors", ".ckpt")):
                        full_path = os.path.join(rel_root, f) if rel_root else f
                        print(f"  - '{full_path}'")
                if len(files) > 5:
                    print(f"  ... and {len(files)-5} more files")
                if dirs:
                    print(f"  Subdirectories: {dirs}")

    except ImportError as e:
        print(f"Could not import folder_paths: {e}")
else:
    print(f"ComfyUI not found at {comfyui_path}")
