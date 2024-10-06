# MailArchive-to-IMAPFolders

## Overview

**MailArchive-to-IMAPFolders** provides a collection of tools aimed at simplifying email archive migrations. Designed for switching between Gmail accounts or migrating to other IMAP-compatible services, especially for large email archives. It converts Mbox exports to EML files, maintains your original labels and folder structures to preserve email organization, and ensures efficient uploads. Notable features include label filtering and migration resumption capabilities.

## Features

- **Mbox to EML Conversion**: Efficiently converts large Mbox files into individual EML files.
- **Email Uploading**: Uploads converted EML files to Gmail or any IMAP-compatible email service.
- **Preserve Labels and Folders**: Maintains the original labels and folder hierarchy from Gmail.
- **Label Filtering**: Skip unwanted labels during the upload process.
- **Resumable Uploads**: Continue the upload process from where it left off in case of interruptions.
- **Compatibility**: Supports large email archives (e.g., 50GB or more).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Gmail Preparation](#gmail-preparation)
- [Usage](#usage)
- [Customization](#customization)
  - [1. Ignoring Specific Labels](#1-ignoring-specific-labels)
  - [2. Setting Label Priorities](#2-setting-label-priorities)
- [Troubleshooting](#troubleshooting)
- [Notes](#notes)
- [License](#license)

## Prerequisites

- **Python 3.6+**: Ensure you have Python installed. [Download Python](https://www.python.org/downloads/). No additional Python libraries or requirements needed.
- **Internet Connection**: A stable internet connection is required for uploading emails.
- **Access to Gmail Account**: Administrative access to both the source and destination Gmail accounts.

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/MailArchive-to-IMAPFolders.git
   cd MailArchive-to-IMAPFolders
   ```

   > **Note**: Replace `yourusername` with your actual GitHub username.

## Gmail Preparation

Before migrating your emails, ensure your Gmail account is properly prepared:

1. **Export Mbox File**

   - Use [Google Takeout](https://takeout.google.com/) to export your Mbox file (up to 50GB or as per your requirement).

2. **Enable IMAP**

   - Log in to your Gmail account.
   - Go to **Settings** > **See all settings** > **Forwarding and POP/IMAP**.
   - Enable **IMAP Access**.

3. **Enable Multi-Factor Authentication (MFA/2FA)**

   - Secure your Google account by enabling **MFA (2FA)**.
   - This is necessary to create app-specific passwords.

4. **Create App Password**

   - After enabling MFA, navigate to the **Security** section of your Google account.
   - Create an **App Password** for the email uploader.
   - **Important**: Remove spaces from the app password. For example, convert `xv12 xx34 xy56 xz78` to `xv12xx34xy56xz78`.

## Usage

Follow these steps to convert and upload your emails:

* 1\. **Run the Converter**

   ```bash
   python converter.py --input /path/to/your/mboxfile.mbox --output /path/to/eml/output --labels
   ```

   - The `--labels` flag will display which labels will be created during the upload.

* 2\. **Upload emails**

* 2.1\. **GMAIL IMAP**

To upload emails:

```bash
./imap_eml_uploader.py --imap-provider gmail --email your_email@gmail.com --password your_app_password --directory emails
```

To resume uploading:

```bash
./imap_eml_uploader.py --imap-provider gmail --email your_email@gmail.com --password your_app_password --directory emails --resume
```

* 2.2\. **Custom IMAP server**

To upload emails:

```bash
./imap_eml_uploader.py --imap-provider custom --server imap.example.com --port 993 --username your_username --password your_password --directory emails
```

To resume uploading:

```bash
./imap_eml_uploader.py --imap-provider custom --server imap.example.com --port 993 --username your_username --password your_password --directory emails --resume
```

**Note**: Ensure that your custom IMAP server supports SSL/TLS on the specified port (default is usually port 993 for IMAPS).

## Additional Notes

- **TLS/SSL**: The script uses `IMAP4_SSL` to ensure that the connection to the IMAP server is secure.
- **Email and Username**:
  - For Gmail, the `--email` argument is used for both the email address and the username when logging in.
  - For custom IMAP servers, the `--username` argument is used to log in, which may differ from the email address.
- **Logging**: The script logs successful and failed uploads to `upload.log`, which is used to resume uploads if needed.
- **Error Handling**: The script includes error handling for common issues such as login failures and connection errors.

## Customization

You can customize the script's behavior by modifying certain configurations directly in the Python source file.

### 1. Ignoring Specific Labels

By default, the script ignores a set of predefined labels that are considered unnecessary for organizing your emails.

#### Default Ignored Labels

```python
ignore_labels = {
    "Opened", "Archived", "Unread", "Important", "Category Forums",
    "Category Personal", "Category Promotions", "Category Purchases",
    "Category Travel", "Category Updates", "Read Receipt Sent",
    "IMAP_NOTJUNK", "IMAP_NonJunk", "IMAP_receipt-handled"
}
```

#### How to Customize

- **To ignore additional labels**: Add the label names to the `ignore_labels` set.

  ```python
  ignore_labels = {
      "Opened", "Archived", "Unread", "YourLabel1", "YourLabel2",
      # ... existing labels
  }
  ```

- **To stop ignoring certain labels**: Remove the label names from the `ignore_labels` set.

  ```python
  ignore_labels = {
      "Opened", "Archived", "Unread",
      # Removed "Important" from ignored labels
      # ... other labels
  }
  ```

### 2. Setting Label Priorities

The script assigns emails to folders based on the highest priority label assigned to them. By default, only the "Sent" label has a priority.

#### Default Label Priority

```python
# Default label priority with "Sent" as highest priority
label_priority = ["Sent"]
label_priority_map = {"Sent": 0}
```

#### How to Customize

- **Using a Label Priority File**:

  Create a text file (e.g., `label_priority.txt`) with labels listed from highest to lowest priority, one label per line.

  Example `label_priority.txt`:

  ```
  Important
  Work
  Personal
  Updates
  Promotions
  ```

  Run the script with your custom label priority file:

  ```bash
  python converter.py /path/to/your/mboxfile.mbox label_priority.txt
  ```

- **Modifying Directly in the Script**:

  Edit the `label_priority` list and `label_priority_map` dictionary:

  ```python
  label_priority = ["Important", "Work", "Personal", "Updates", "Promotions"]
  label_priority_map = {label: idx for idx, label in enumerate(label_priority)}
  ```

  This sets "Important" as the highest priority label, followed by "Work", and so on.

## Troubleshooting

- **Permission Issues**: Ensure you have the necessary permissions to read the Mbox file and write to the output directory.
- **Network Interruptions**: Use the `--resume` flag to continue uploading without restarting.
- **Label Issues**: Verify that label names do not contain prohibited characters. Special characters will be replaced with underscores.
- **Authentication Errors**: Double-check your app password and ensure MFA is correctly set up on your Google account. Make sure the app password is set on the Gmail account you are uploading to (not downloading from).

## Notes

- **Starting Over**: If you need to start the migration process from scratch, ensure you remove all previously uploaded emails and delete them entirely from Gmail's recycle bin. Otherwise, they might be removed instead of uploaded again.
- **Upload Duration**: Uploading 200k emails totaling 45GB can take approximately **36-48 hours** on a regular internet connection (20-30 Mbit/s).
- **Label Name Compatibility**: Labels with non-ASCII or special characters will be converted to underscores `_` for compatibility reasons.
- **Reviewing Emails Before Upload**:
  - Use **[Thunderbird Extended Support Release (ESR)](https://www.thunderbird.net/en-US/)** to review your emails.
  - Install **[ImportExportTools NG](https://addons.thunderbird.net/en-US/thunderbird/addon/importexporttools-ng/)**:
    - [ImportExportTools NG GitHub](https://github.com/thundernest/import-export-tools-ng)
  - **Handy Tips**:
    - [Change the Default Sorting Order in Thunderbird](https://superuser.com/questions/13518/change-the-default-sorting-order-in-thunderbird)
  - **Enable Downloading External Content**:
    - In Thunderbird, go to **Settings** > **Privacy & Security** and enable **Allow remote content in messages** if needed.

## License

This project is licensed under the [MIT License](LICENSE).
