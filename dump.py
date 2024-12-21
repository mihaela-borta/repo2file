import os
import sys
from typing import List, Set, Optional
import fnmatch
import argparse
from pathlib import Path

def parse_exclusion_file(file_path: str) -> tuple[set[str], set[str]]:
    exclusion_patterns = set()
    inclusion_patterns = set()
    
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('!'):
                        inclusion_patterns.add(line[1:])  # Remove the ! character
                    else:
                        exclusion_patterns.add(line)
    return exclusion_patterns, inclusion_patterns

def is_excluded(path: str, exclusion_patterns: set[str], inclusion_patterns: set[str]) -> bool:
    # First check if path matches any inclusion pattern
    for pattern in inclusion_patterns:
        if pattern.startswith('/') and pattern.endswith('/'):
            if path.startswith(pattern[1:]) or path == pattern[1:-1]:
                return False
        elif pattern.endswith('/'):
            if path.startswith(pattern) or path == pattern[:-1]:
                return False
        elif pattern.startswith('/'):
            if path == pattern[1:] or path.startswith(pattern[1:] + os.sep):
                return False
        else:
            if fnmatch.fnmatch(path, pattern) or any(fnmatch.fnmatch(part, pattern) for part in path.split(os.sep)):
                return False

    # Then check exclusion patterns
    for pattern in exclusion_patterns:
        if pattern.startswith('/') and pattern.endswith('/'):
            if path.startswith(pattern[1:]) or path == pattern[1:-1]:
                return True
        elif pattern.endswith('/'):
            if path.startswith(pattern) or path == pattern[:-1]:
                return True
        elif pattern.startswith('/'):
            if path == pattern[1:] or path.startswith(pattern[1:] + os.sep):
                return True
        else:
            if fnmatch.fnmatch(path, pattern) or any(fnmatch.fnmatch(part, pattern) for part in path.split(os.sep)):
                return True
    
    return False  # If no patterns match, include the file

def print_directory_structure(start_path: str, exclusion_patterns: set[str], inclusion_patterns: set[str]) -> str:
    def _generate_tree(dir_path: str, prefix: str = '') -> List[str]:
        entries = os.listdir(dir_path)
        entries = sorted(entries, key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))
        tree = []
        for i, entry in enumerate(entries):
            rel_path = os.path.relpath(os.path.join(dir_path, entry), start_path)
            if is_excluded(rel_path, exclusion_patterns, inclusion_patterns):
                continue
            
            if i == len(entries) - 1:
                connector = '└── '
                new_prefix = prefix + '    '
            else:
                connector = '├── '
                new_prefix = prefix + '│   '
            
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                tree.append(f"{prefix}{connector}{entry}/")
                tree.extend(_generate_tree(full_path, new_prefix))
            else:
                tree.append(f"{prefix}{connector}{entry}")
        return tree

    tree = ['/ '] + _generate_tree(start_path)
    return '\n'.join(tree)

def scan_folder(start_path: str, file_types: Optional[List[str]], output_file: str, 
                exclusion_patterns: set[str], inclusion_patterns: set[str]) -> None:
    with open(output_file, 'w', encoding='utf-8') as out_file:
        # Write the directory structure
        out_file.write("Directory Structure:\n")
        out_file.write("-------------------\n")
        out_file.write(print_directory_structure(start_path, exclusion_patterns, inclusion_patterns))
        out_file.write("\n\n")
        out_file.write("File Contents:\n")
        out_file.write("--------------\n")

        for root, dirs, files in os.walk(start_path):
            rel_path = os.path.relpath(root, start_path)
            
            if is_excluded(rel_path, exclusion_patterns, inclusion_patterns):
                continue
            
            for file in files:
                file_rel_path = os.path.join(rel_path, file)
                if is_excluded(file_rel_path, exclusion_patterns, inclusion_patterns):
                    continue
                if file_types is None or any(file.endswith(ext) for ext in file_types):
                    file_path = os.path.join(root, file)
                    
                    print(f"Processing: {file_rel_path}")
                    out_file.write(f"File: {file_rel_path}\n")
                    out_file.write("-" * 50 + "\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as in_file:
                            content = in_file.read()
                            out_file.write(f"Content of {file_rel_path}:\n")
                            out_file.write(content)
                    except Exception as e:
                        print(f"Error reading file {file_rel_path}: {str(e)}. Skipping.")
                        out_file.write(f"Error reading file: {str(e)}. Content skipped.\n")
                    
                    out_file.write("\n\n")

def parse_arguments() -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scan and dump directory structure and file contents",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "start_path",
        type=Path,
        help="Directory path to start scanning from"
    )
    
    parser.add_argument(
        "output_file",
        type=Path,
        help="Path to the output file where results will be written"
    )
    
    parser.add_argument(
        "--exclusion-file",
        "-e",
        type=Path,
        help="Path to file containing exclusion patterns (use ! prefix for inclusions)"
    )
    
    parser.add_argument(
        "--file-types",
        "-t",
        nargs="+",
        help="List of file extensions to include (e.g., .py .txt .md)"
    )

    return parser.parse_args()

def main() -> None:
    """Main function to handle the directory scanning and file dumping process."""
    args = parse_arguments()
    
    # Convert Path objects to strings for compatibility with existing functions
    start_path = str(args.start_path)
    output_file = str(args.output_file)
    exclusion_file = str(args.exclusion_file) if args.exclusion_file else None
    
    # Parse exclusion and inclusion patterns from the same file
    exclusion_patterns, inclusion_patterns = parse_exclusion_file(exclusion_file) if exclusion_file else (set(), set())
    
    if exclusion_file:
        print(f"Using exclusion patterns: {exclusion_patterns}")
        if inclusion_patterns:
            print(f"Using inclusion patterns: {inclusion_patterns}")
    else:
        print("No exclusion file specified. Scanning all files.")

    if args.file_types:
        print(f"Scanning for file types: {args.file_types}")
    else:
        print("No file types specified. Scanning all files.")

    scan_folder(start_path, args.file_types, output_file, exclusion_patterns, inclusion_patterns)
    print(f"Scan complete. Results written to {output_file}")

if __name__ == "__main__":
    main()