#!/usr/bin/env python3
"""Utility script to check for GraphML files in the output directory."""

import os
from pathlib import Path
import argparse
import glob
import datetime

def find_graphml_files(root_dir):
    """Find all GraphML files in the output directory."""
    output_dir = Path(root_dir) / "output"
    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        return []
    
    print(f"Checking output directory: {output_dir}")
    
    # List all timestamp directories
    timestamp_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    if not timestamp_dirs:
        print("No timestamp directories found.")
        return []
    
    graphml_files = []
    
    for ts_dir in timestamp_dirs:
        artifacts_dir = ts_dir / "artifacts"
        if artifacts_dir.exists():
            files = list(artifacts_dir.glob("*.graphml"))
            if files:
                for file in files:
                    modified_time = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                    graphml_files.append({
                        "path": str(file),
                        "timestamp_dir": str(ts_dir.name),
                        "modified": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "size_kb": file.stat().st_size / 1024
                    })
                    
    return sorted(graphml_files, key=lambda x: x["modified"], reverse=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for GraphML files in the output directory.")
    parser.add_argument("--root", default="./ragtest", help="Root directory for the GraphRAG data")
    args = parser.parse_args()
    
    files = find_graphml_files(args.root)
    
    if files:
        print(f"\nFound {len(files)} GraphML files:")
        print("-" * 80)
        print(f"{'Path':<60} {'Modified':<20} {'Size (KB)':<10}")
        print("-" * 80)
        for file in files:
            print(f"{file['path']:<60} {file['modified']:<20} {file['size_kb']:<10.2f}")
    else:
        print("\nNo GraphML files found. Make sure:")
        print("1. You've run the indexing process (python -m graphrag.index --root ./ragtest)")
        print("2. snapshots.graphml: yes is set in your settings.yaml file")
