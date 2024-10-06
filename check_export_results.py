#!/usr/bin/env python3

import os
import sys
import argparse

def get_total_size(dir_path):
    """
    Calculate the total size of all files in the given directory and its subdirectories.

    Args:
        dir_path (str): The path to the directory.

    Returns:
        float: Total size in megabytes (MB).
    """
    total_size = 0
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                # Skip if it's a symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
            except OSError:
                # If the file is inaccessible, skip it
                pass
    return total_size / (1024 * 1024)  # Convert bytes to MB

def display_tree(dir_path, prefix="", is_last=True):
    """
    Recursively display the directory tree with file counts and total sizes.

    Args:
        dir_path (str): The path to the directory.
        prefix (str, optional): The indentation string for the current level. Defaults to "".
        is_last (bool, optional): Indicates if the current directory is the last in its level. Defaults to True.
    """
    basename = os.path.basename(os.path.abspath(dir_path))
    if not basename:
        basename = dir_path  # For root directories

    # Get total size
    total_size_mb = get_total_size(dir_path)

    # Count files and collect subdirectories
    try:
        with os.scandir(dir_path) as it:
            entries = sorted(it, key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        print(f"{prefix}{'└── ' if is_last else '├── '}[Access Denied] {basename}")
        return
    except FileNotFoundError:
        print(f"{prefix}{'└── ' if is_last else '├── '}[Not Found] {basename}")
        return

    file_count = sum(1 for entry in entries if entry.is_file())
    subdirs = [entry.path for entry in entries if entry.is_dir()]

    # Prepare the branch symbols
    branch = "└── " if is_last else "├── "

    # Display the current directory's information
    print(f"{prefix}{branch}{basename} ({total_size_mb:.2f} MB, {file_count} files)")

    # Update the prefix for child directories
    if is_last:
        new_prefix = prefix + "    "
    else:
        new_prefix = prefix + "│   "

    # Iterate over subdirectories
    for index, subdir in enumerate(subdirs):
        is_last_subdir = index == len(subdirs) - 1
        display_tree(subdir, new_prefix, is_last_subdir)

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Export and display the directory structure with file counts and total sizes.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  ab.export_directory_check.py /path/to/directory
  ab.export_directory_check.py --help
"""
    )
    parser.add_argument(
        "directory",
        metavar="DIRECTORY",
        type=str,
        nargs="?",
        help="Path to the directory to inspect."
    )
    return parser.parse_args()

def main():
    """
    Main function to handle command-line arguments and initiate the directory tree display.
    """
    args = parse_arguments()

    if args.directory is None:
        # No directory provided; display usage information
        print("Error: No directory provided.\n")
        print("Usage: ab.export_directory_check.py <directory>\n")
        print("Use 'ab.export_directory_check.py --help' for more information.")
        sys.exit(1)

    dir_path = args.directory

    if not os.path.isdir(dir_path):
        print(f"Error: '{dir_path}' is not a directory or cannot be accessed.")
        sys.exit(1)

    # Display the working message
    print("Working... please wait (depending on directory size and file count, it can take up to 30 minutes to finish)\n")

    # Print the root directory without any prefix
    root_basename = os.path.basename(os.path.abspath(dir_path))
    if not root_basename:
        root_basename = dir_path  # For root directories

    # Get total size for root
    root_total_size_mb = get_total_size(dir_path)

    # Count files in root
    try:
        with os.scandir(dir_path) as it:
            entries = list(it)
    except PermissionError:
        print(f"[Access Denied] {root_basename}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"[Not Found] {root_basename}")
        sys.exit(1)

    root_file_count = sum(1 for entry in entries if entry.is_file())
    root_subdirs = sorted([entry.path for entry in entries if entry.is_dir()])

    print(f"{root_basename} ({root_total_size_mb:.2f} MB, {root_file_count} files)")

    # Iterate over subdirectories
    for index, subdir in enumerate(root_subdirs):
        is_last_subdir = index == len(root_subdirs) - 1
        display_tree(subdir, "", is_last_subdir)

if __name__ == "__main__":
    main()
