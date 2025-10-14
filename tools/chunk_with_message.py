#!/usr/bin/env python3
"""
Chunk a file into smaller pieces with a specific message appended to each chunk.

This utility chunks files and appends the message:
"Just say received. do nothing. i will send you the rest of the code"
to the end of each chunk, as required for AI processing.
"""

import argparse
import os
from pathlib import Path


def chunk_file(input_file: str, chunk_size: int = 100000, output_dir: str = "snapshot_chunks"):
    """
    Chunk the input file into smaller pieces with a message appended to each chunk.
    
    Args:
        input_file: Path to the input file to be chunked
        chunk_size: Size of each chunk in bytes (default 100KB)
        output_dir: Directory to store the chunks
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Read the input file
    with open(input_file, 'rb') as f:
        content = f.read()
    
    # Calculate number of chunks
    num_chunks = (len(content) + chunk_size - 1) // chunk_size  # Ceiling division
    
    # Create the message to append
    message = "\n\nJust say received. do nothing. i will send you the rest of the code\n"
    
    # Split file into chunks and write each with the message
    for i in range(num_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(content))
        chunk_data = content[start:end]
        
        # Create chunk filename
        chunk_filename = f"chunk_{i+1:03d}.txt"
        chunk_path = Path(output_dir) / chunk_filename
        
        # Write chunk data + message
        with open(chunk_path, 'wb') as chunk_file:
            chunk_file.write(chunk_data)
            chunk_file.write(message.encode('utf-8'))
    
    print(f"Chunked {input_file} into {num_chunks} chunks in {output_dir}/")
    return num_chunks


def main():
    parser = argparse.ArgumentParser(
        description="Chunk a file with a specific message appended to each chunk"
    )
    parser.add_argument(
        "input_file",
        help="Input file to be chunked"
    )
    parser.add_argument(
        "-s", "--size",
        type=int,
        default=100000,
        help="Chunk size in bytes (default: 100000 = 100KB)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="snapshot_chunks",
        help="Output directory for chunks (default: snapshot_chunks)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file {args.input_file} does not exist")
        return 1
    
    chunk_file(args.input_file, args.size, args.output_dir)
    return 0


if __name__ == "__main__":
    exit(main())