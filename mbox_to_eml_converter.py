#!/usr/bin/env python3

# Script: mbox_to_eml_converter.py
# Usage:
#   To extract emails:        ./mbox_to_eml_converter.py path_to_mailbox.mbox [label_priority.txt]
#   To just list labels:      ./mbox_to_eml_converter.py --list-labels path_to_mailbox.mbox

import sys
import os
import mailbox
import email
import re
import argparse
import random
import string
from email.header import decode_header, make_header

def sanitize_folder_name(name):
    """
    Sanitize the folder name by replacing or removing invalid characters.
    """
    # Replace invalid characters with an underscore
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def decode_mime_words(s):
    """
    Decode MIME encoded words to a unicode string.
    """
    try:
        return str(make_header(decode_header(s)))
    except Exception as e:
        # If decoding fails, return the original string
        print(f"Warning: Failed to decode MIME words in '{s}': {e}")
        return s

def fix_broken_mime(s):
    """
    Attempt to fix broken MIME encodings in a string.
    """
    # Remove any line breaks and join lines
    s = ''.join(s.splitlines())
    # Find all MIME encoded words
    pattern = r'(=\?[^?]*\?[BQbq]\?[^?]*\?=)'
    matches = re.findall(pattern, s)
    fixed_parts = []
    last_end = 0
    for match in matches:
        start = s.find(match, last_end)
        end = start + len(match)
        fixed_parts.append(s[last_end:start])
        fixed_parts.append(match)
        last_end = end
    fixed_parts.append(s[last_end:])
    # Reconstruct the string
    fixed_s = ''.join(fixed_parts)
    return fixed_s

def parse_labels(headers):
    """
    Parse the X-Gmail-Labels header and return a list of labels.
    """
    labels = []

    # Extract all X-Gmail-Labels headers
    labels_headers = headers.get_all('X-Gmail-Labels', [])

    for header in labels_headers:
        # Decode header if it's MIME-encoded
        header = fix_broken_mime(header)
        header = decode_mime_words(header)
        # Handle folded headers (joined without spaces)
        header = header.replace('\r', '').replace('\n', '')
        # Split labels by comma unless the comma is within quotes
        labels.extend(re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', header))

    # Strip whitespace and quotes from labels
    labels = [label.strip().strip('"') for label in labels]
    return labels

def remove_surrogates(s):
    """
    Remove surrogate code points from a string.
    """
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

def sanitize_filename(filename):
    """
    Sanitize filename to remove invalid characters and surrogates.
    """
    # Remove surrogates
    filename = remove_surrogates(filename)
    # Replace invalid characters with an underscore
    safe_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c if c in safe_chars else '_' for c in filename)

def random_string(length=6):
    """
    Generate a random string of given length.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def main():
    parser = argparse.ArgumentParser(description="Extract emails from mbox file into folders based on labels.")
    parser.add_argument('mailbox_file', nargs='?', help='Path to the mbox file.')
    parser.add_argument('label_priority_file', nargs='?', help='Optional label priority file.')
    parser.add_argument('--list-labels', action='store_true', help='Only list labels without extracting emails.')

    args = parser.parse_args()

    if not args.mailbox_file:
        parser.print_help()
        sys.exit(1)

    mailbox_file = args.mailbox_file
    label_priority_file = args.label_priority_file
    list_only = args.list_labels

    # Labels to ignore
    ignore_labels = {"Opened", "Archived", "Unread", "Important", "Category Forums", "Category Personal", "Category Promotions", "Category Purchases", "Category Travel", "Category Updates", "Read Receipt Sent", "IMAP_NOTJUNK", "IMAP_NonJunk", "IMAP_receipt-handled"}

    # Read label priority from file if provided
    label_priority = []
    label_priority_map = {}
    if label_priority_file:
        try:
            with open(label_priority_file, 'r', encoding='utf-8') as lp_file:
                for idx, line in enumerate(lp_file):
                    label = line.strip()
                    if label:
                        label_priority.append(label)
                        label_priority_map[label] = idx
        except Exception as e:
            print(f"Error reading label priority file: {e}")
            sys.exit(1)
    else:
        # Default label priority with "Sent" as highest priority
        label_priority = ["Sent"]
        label_priority_map = {"Sent": 0}

    try:
        mbox = mailbox.mbox(mailbox_file)
    except Exception as e:
        print(f"Error opening mailbox file: {e}")
        sys.exit(1)

    # Collect labels to assign priorities later if needed
    labels_set = set()

    # Process each email
    for idx, message in enumerate(mbox):
        # Get the headers of the message
        headers = message

        # Parse labels
        labels = parse_labels(headers)
        # Ignore specified labels
        labels = [label for label in labels if label and label not in ignore_labels]
        # Add labels to the set
        labels_set.update(labels)

        if list_only:
            continue  # Skip email extraction if listing labels only

        # Determine the highest priority label
        highest_priority_label = None
        highest_priority_index = len(label_priority) + 1  # Default to lowest priority

        for label in labels:
            if label in label_priority_map:
                priority_index = label_priority_map[label]
            else:
                # Assign low priority to labels not in the priority list
                priority_index = len(label_priority) + 1

            if highest_priority_label is None or priority_index < highest_priority_index:
                highest_priority_index = priority_index
                highest_priority_label = label

        if highest_priority_label is None:
            # If no labels matched, assign to "Other"
            highest_priority_label = "Other"

        # Handle '/' in label names to create nested directories
        # Split the label by '/' and create the nested path
        folder_path_parts = [sanitize_folder_name(part) for part in highest_priority_label.split('/')]
        folder_path = os.path.join('emails', *folder_path_parts)

        # Create the nested directories if they don't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Generate a unique filename for the email
        message_id = message.get('Message-ID', '')
        if message_id:
            # Remove '<' and '>'
            message_id = message_id.strip('<>')
            # Sanitize message_id to create filename
            filename_safe_message_id = sanitize_filename(message_id)
            # Ensure filename is not too long
            max_filename_length = 255 - len('.eml')
            if len(filename_safe_message_id) > max_filename_length:
                filename_safe_message_id = filename_safe_message_id[:max_filename_length]
            # Add random string
            random_str = random_string()
            filename = f"{filename_safe_message_id}_{random_str}.eml"
        else:
            # If no Message-ID, generate a filename using index and random string
            random_str = random_string()
            filename = f"email_{idx}_{random_str}.eml"

        # Ensure filename is unique in the folder
        filepath = os.path.join(folder_path, filename)
        count = 1
        while os.path.exists(filepath):
            filename = f"{os.path.splitext(filename)[0]}_{count}.eml"
            filepath = os.path.join(folder_path, filename)
            count += 1

        # Write the email to the .eml file
        try:
            with open(filepath, 'wb') as eml_file:
                gen = email.generator.BytesGenerator(eml_file)
                gen.flatten(message)
        except Exception as e:
            print(f"Error writing email to file {filepath}: {e}")
            continue

    # Write the list of labels to a file
    with open('labels.txt', 'w', encoding='utf-8') as labels_file:
        for label in sorted(labels_set):
            labels_file.write(f"{label}\n")

    if list_only:
        print("Labels have been listed in 'labels.txt'.")
    else:
        print("Emails have been extracted to folders based on highest priority labels.")

if __name__ == "__main__":
    main()
