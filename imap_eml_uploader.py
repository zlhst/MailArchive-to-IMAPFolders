#!/usr/bin/env python3

# Script: imap_eml_uploader.py
# Usage:
#   For Gmail:
#     To upload emails:
#       ./imap_eml_uploader.py --imap-provider gmail --email your_email@gmail.com --password your_app_password --directory emails
#     To resume uploading:
#       ./imap_eml_uploader.py --imap-provider gmail --email your_email@gmail.com --password your_app_password --directory emails --resume
#
#   For Custom IMAP Server:
#     To upload emails:
#       ./imap_eml_uploader.py --imap-provider custom --server imap.example.com --port 993 --username your_username --password your_password --directory emails
#     To resume uploading:
#       ./imap_eml_uploader.py --imap-provider custom --server imap.example.com --port 993 --username your_username --password your_password --directory emails --resume

import os
import sys
import argparse
import imaplib
import email
import time
import traceback
import re
import string
import datetime

def connect_to_imap(args):
    try:
        if args.imap_provider == 'gmail':
            imap = imaplib.IMAP4_SSL('imap.gmail.com')
            imap.login(args.email, args.password)
            print("Logged in to Gmail IMAP server.")
        elif args.imap_provider == 'custom':
            imap = imaplib.IMAP4_SSL(args.server, args.port)
            imap.login(args.username, args.password)
            print(f"Logged in to IMAP server at {args.server}:{args.port}.")
        else:
            print("Invalid IMAP provider specified.")
            sys.exit(1)
        return imap
    except imaplib.IMAP4.error as e:
        print(f"IMAP login failed: {e}")
        sys.exit(1)

def get_hierarchy_delimiter(imap):
    typ, data = imap.list()
    if typ == 'OK':
        # Parse the response to get the hierarchy delimiter
        for line in data:
            match = re.search(rb'\(([^)]*)\) "(?P<delimiter>[^"]+)" .*', line)
            if match:
                delimiter = match.group('delimiter').decode('utf-8')
                return delimiter
    # Default to '/'
    return '/'

def sanitize_label(label, delimiter):
    # Replace any non-ASCII character with an underscore
    label = re.sub(r'[^\x00-\x7F]', '_', label)
    # Replace dots with underscores
    label = re.sub(r'[ .,]', '_', label)
    # Build a set of allowed characters
    allowed_chars_set = set(string.ascii_letters + string.digits + '_')
    allowed_chars_set.add(delimiter)
    # Build a character class, escaping any special characters
    allowed_chars_escaped = [re.escape(c) for c in allowed_chars_set]
    # Combine into a character class
    allowed_chars_class = ''.join(allowed_chars_escaped)
    # Replace any character not in the allowed set with an underscore
    label = re.sub(rf'[^{allowed_chars_class}]', '_', label)
    # Replace multiple underscores or spaces with a single underscore
    label = re.sub(r'[_]+', '_', label)
    # Remove leading and trailing underscores
    label = label.strip('_')
    return label

def format_internaldate(date_header):
    if not date_header:
        return None
    try:
        parsed_datetime = email.utils.parsedate_to_datetime(date_header)
        if not parsed_datetime:
            return None
        # Ensure timezone-aware datetime
        if parsed_datetime.tzinfo is None:
            parsed_datetime = parsed_datetime.replace(tzinfo=datetime.timezone.utc)
        return parsed_datetime
    except Exception as e:
        return None

def collect_eml_files(base_dir, uploaded_files, parent_label='ARCH-IMPORT', delimiter='/'):
    files_to_upload = []
    labels_set = set()
    for root, dirs, files in os.walk(base_dir):
        # Construct the IMAP folder path
        relative_path = os.path.relpath(root, base_dir)
        if relative_path == '.':
            label = parent_label
        else:
            # Replace OS-specific path separator with the hierarchy delimiter
            sub_label = relative_path.replace(os.sep, delimiter)
            label = f"{parent_label}{delimiter}{sub_label}"
        # Sanitize label
        label = sanitize_label(label, delimiter)
        labels_set.add(label)

        for filename in files:
            if filename.lower().endswith('.eml'):
                eml_file_path = os.path.abspath(os.path.join(root, filename))  # Ensure absolute path
                if eml_file_path not in uploaded_files:
                    files_to_upload.append((eml_file_path, label))
    return files_to_upload, labels_set

class ImapUploader:
    def __init__(self, args):
        self.args = args
        self.connect()

    def connect(self):
        self.imap = connect_to_imap(self.args)

    def disconnect(self):
        self.imap.logout()

    def create_imap_label(self, label):
        try:
            result = self.imap.create(label)
            if result[0] == 'OK':
                print(f"Created label: {label}")
            else:
                # Check if the label already exists
                if 'already exists' in result[1][0].decode().lower():
                    pass  # Label already exists
                else:
                    print(f"Failed to create label '{label}': {result[1]}")
        except imaplib.IMAP4.abort as e:
            print("IMAP connection aborted during label creation, attempting to reconnect...")
            self.connect()
            # Retry label creation
            try:
                result = self.imap.create(label)
                if result[0] == 'OK':
                    print(f"Created label: {label}")
                else:
                    # Check if the label already exists
                    if 'already exists' in result[1][0].decode().lower():
                        pass  # Label already exists
                    else:
                        print(f"Failed to create label '{label}': {result[1]}")
            except Exception as e:
                print(f"Failed to create label '{label}' after reconnecting: {e}")

        except Exception as e:
            print(f"Failed to create label '{label}': {e}")

    def upload_email(self, eml_file_path, imap_folder, log_file, current_file, total_files, counter_width):
        try:
            with open(eml_file_path, 'rb') as f:
                msg = f.read()

            # Parse the email message
            email_message = email.message_from_bytes(msg)

            # Get the 'Date' header
            date_header = email_message.get('Date')

            # Format the date_time for IMAP APPEND
            date_time = format_internaldate(date_header)
            # If date_time is None, the current date/time will be used

            # Append the message to the mailbox
            flags = None
            try:
                result = self.imap.append(imap_folder, flags, date_time, msg)
            except imaplib.IMAP4.abort as e:
                print("IMAP connection aborted during upload, attempting to reconnect...")
                self.connect()
                # Retry the upload
                result = self.imap.append(imap_folder, flags, date_time, msg)

            counter_format = f"{{:{counter_width}d}}/{{:{counter_width}d}}"
            counter = counter_format.format(current_file, total_files)
            if result[0] == 'OK':
                print(f"{counter} Uploaded email '{eml_file_path}' to folder '{imap_folder}'.")
                # Write success to log file, using absolute path
                log_file.write(f"[success] {eml_file_path}\n")
                log_file.flush()
            else:
                print(f"{counter} Failed to upload email '{eml_file_path}': {result[1]}")
                # Write failure to log file
                log_file.write(f"[fail] {eml_file_path}\n")
                log_file.flush()

            # Sleep for 10 milliseconds / rate limit
            time.sleep(0.001)  # 0.01 seconds = 10 milliseconds

        except Exception as e:
            counter_format = f"{{:{counter_width}d}}/{{:{counter_width}d}}"
            counter = counter_format.format(current_file, total_files)
            print(f"{counter} Error uploading email '{eml_file_path}': {e}")
            traceback.print_exc()
            # Write failure to log file
            log_file.write(f"[fail] {eml_file_path}\n")
            log_file.flush()

def main():
    parser = argparse.ArgumentParser(description="Upload .eml files to an IMAP server, preserving directory structure under ARCH-IMPORT folder.")
    parser.add_argument('--imap-provider', choices=['gmail', 'custom'], required=True, help='Specify the IMAP provider (gmail or custom).')
    parser.add_argument('--email', help='Your email address (required for gmail).')
    parser.add_argument('--password', required=True, help='Your email account password or app password.')
    parser.add_argument('--directory', required=True, help='Path to the directory containing .eml files.')
    parser.add_argument('--resume', action='store_true', help='Resume upload from where it left off using upload.log')

    # Additional arguments for custom IMAP server
    parser.add_argument('--server', help='IMAP server hostname (required for custom provider).')
    parser.add_argument('--port', type=int, help='IMAP server port (required for custom provider).')
    parser.add_argument('--username', help='Your username for the custom IMAP server (required for custom provider).')

    args = parser.parse_args()

    # Validate arguments based on the imap_provider
    if args.imap_provider == 'gmail':
        if not args.email:
            parser.error("--email is required for Gmail provider.")
    elif args.imap_provider == 'custom':
        missing_args = []
        if not args.server:
            missing_args.append('--server')
        if not args.port:
            missing_args.append('--port')
        if not args.username:
            missing_args.append('--username')
        if missing_args:
            parser.error(f"The following arguments are required for custom provider: {', '.join(missing_args)}")
    else:
        parser.error("Invalid --imap-provider specified.")

    base_directory = os.path.abspath(args.directory)  # Ensure base_directory is absolute

    if not os.path.isdir(base_directory):
        print(f"The directory '{base_directory}' does not exist.")
        sys.exit(1)

    uploaded_files = set()

    if not args.resume:
        # Delete upload.log file if it exists
        if os.path.exists('upload.log'):
            os.remove('upload.log')
    else:
        # Build set of successfully uploaded files from upload.log
        if os.path.exists('upload.log'):
            with open('upload.log', 'r') as log_file_read:
                for line in log_file_read:
                    line = line.strip()
                    if line.startswith('[success] '):
                        # Extract the full path and convert to absolute path
                        full_path = line[len('[success] '):]
                        full_path = os.path.abspath(full_path)
                        uploaded_files.add(full_path)

    uploader = ImapUploader(args)

    try:
        # Get the hierarchy delimiter
        delimiter = get_hierarchy_delimiter(uploader.imap)
        print(f"Using hierarchy delimiter: '{delimiter}'")

        # Collect files to upload and labels to create
        files_to_upload, labels_to_create = collect_eml_files(
            base_directory,
            uploaded_files,
            parent_label='ARCH-IMPORT',
            delimiter=delimiter
        )
        total_files = len(files_to_upload)

        if total_files == 0:
            print("No new emails to upload.")
            return

        # Determine the width for the counter based on the total number of files
        counter_width = len(str(total_files))

        # Sort labels to ensure parent labels are created before child labels
        sorted_labels = sorted(labels_to_create, key=lambda x: x.count(delimiter))

        # Create labels in hierarchical order
        for label in sorted_labels:
            uploader.create_imap_label(label)

        current_file = 1
        with open('upload.log', 'a') as log_file:
            for eml_file_path, label in files_to_upload:
                uploader.upload_email(eml_file_path, label, log_file, current_file, total_files, counter_width)
                current_file += 1
    finally:
        uploader.disconnect()
        print("Logged out from IMAP server.")

if __name__ == '__main__':
    main()
