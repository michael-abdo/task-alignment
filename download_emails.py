#!/usr/bin/env python3
"""
Outlook Email Tool - Download and send emails via Microsoft Graph API.
Reuses authentication from clockify-automation.
"""
import os
import sys
import json
import msal
import requests
import webbrowser
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import re

# Configuration
SCRIPT_DIR = Path(__file__).parent.absolute()
CLOCKIFY_AUTOMATION_DIR = Path("/Users/Mike/Documents/programming/3_current_projects/vvg/clockify-automation")
DOWNLOADS_DIR = SCRIPT_DIR / "downloads"
TOKEN_CACHE_FILE = CLOCKIFY_AUTOMATION_DIR / ".token_cache.json"

# Load env from clockify-automation
from dotenv import load_dotenv
load_dotenv(CLOCKIFY_AUTOMATION_DIR / ".env")

MICROSOFT_CONFIG = {
    "client_id": os.environ.get("MS_CLIENT_ID"),
    "client_secret": os.environ.get("MS_CLIENT_SECRET"),
    "tenant_id": os.environ.get("MS_TENANT_ID"),
    "redirect_uri": os.environ.get("MS_REDIRECT_URI", "http://localhost:8000/callback"),
    "scopes": [
        "Mail.Read", "Mail.ReadWrite", "Mail.Send", "User.Read",
        "Sites.Read.All", "Sites.ReadWrite.All", "Files.Read.All", "Files.ReadWrite.All"
    ],
    "authority": f"https://login.microsoftonline.com/{os.environ.get('MS_TENANT_ID', 'common')}",
    "graph_endpoint": "https://graph.microsoft.com/v1.0",
    "user_email": os.environ.get("MS_USER_EMAIL", "")
}


def _load_token_cache() -> msal.SerializableTokenCache:
    """Load token cache from file."""
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_FILE.exists():
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_token_cache(cache: msal.SerializableTokenCache):
    """Save token cache to file."""
    if cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


@dataclass
class EmailAttachment:
    """Represents an email attachment with content."""
    name: str
    size: int
    content_type: str
    content: bytes = None  # Actual file content

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "size": self.size,
            "content_type": self.content_type,
            "downloaded": self.content is not None
        }


@dataclass
class Email:
    """Represents a fetched email."""
    id: str
    subject: str
    body: str
    date: str
    sender: str
    recipients: List[str]
    attachments: List[EmailAttachment]
    conversation_id: str

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['attachments'] = [a.to_dict() for a in self.attachments]
        return result


@dataclass
class SharePointFile:
    """Represents a SharePoint/OneDrive file."""
    id: str
    name: str
    size: int
    web_url: str
    created: str
    modified: str
    created_by: str
    modified_by: str
    mime_type: str
    parent_path: str

    def to_dict(self) -> Dict:
        return asdict(self)


class OutlookEmailDownloader:
    """Downloads emails and attachments from Outlook."""

    def __init__(self):
        self.config = MICROSOFT_CONFIG
        self.token = None
        self.graph_endpoint = self.config["graph_endpoint"]

    def authenticate(self) -> bool:
        """Authenticate using cached token or device code flow."""
        # Load persistent token cache
        cache = _load_token_cache()

        app = msal.PublicClientApplication(
            self.config["client_id"],
            authority=self.config["authority"],
            token_cache=cache
        )

        # Try to get token from cache first
        accounts = app.get_accounts()
        if accounts:
            print(f"Found cached account: {accounts[0].get('username', 'unknown')}")
            result = app.acquire_token_silent(
                self.config["scopes"],
                account=accounts[0]
            )
            if result and "access_token" in result:
                self.token = result["access_token"]
                _save_token_cache(cache)
                print("Using cached token - no login required!")
                return True

        # Device code flow for interactive login
        flow = app.initiate_device_flow(scopes=self.config["scopes"])
        if "user_code" not in flow:
            print(f"Failed to create device flow: {flow.get('error_description')}")
            return False

        print(f"\nTo authenticate, visit: {flow['verification_uri']}")
        print(f"Enter code: {flow['user_code']}\n")

        # Auto-open browser with code pre-filled
        auth_url = f"https://microsoft.com/devicelogin?otc={flow['user_code']}"
        webbrowser.open(auth_url)
        print("(Browser opened with code pre-filled)")

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            self.token = result["access_token"]
            _save_token_cache(cache)
            print("Authentication successful! Token cached for future runs.")
            return True
        else:
            print(f"Authentication failed: {result.get('error_description')}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _download_attachment_content(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Download actual attachment content."""
        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/messages/{message_id}/attachments/{attachment_id}"

        response = requests.get(url, headers=self._get_headers())
        if response.ok:
            data = response.json()
            # contentBytes is base64 encoded
            if "contentBytes" in data:
                return base64.b64decode(data["contentBytes"])
        return None

    def _parse_email(self, email_data: Dict, download_attachments: bool = True) -> Email:
        """Parse raw email data into Email object."""
        attachments = []
        if email_data.get("hasAttachments"):
            user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
            att_url = f"{self.graph_endpoint}/{user_path}/messages/{email_data['id']}/attachments"
            att_response = requests.get(att_url, headers=self._get_headers())
            if att_response.ok:
                for att in att_response.json().get("value", []):
                    attachment = EmailAttachment(
                        name=att.get("name", ""),
                        size=att.get("size", 0),
                        content_type=att.get("contentType", "")
                    )

                    # Download actual content if requested
                    if download_attachments and att.get("@odata.type") == "#microsoft.graph.fileAttachment":
                        print(f"    Downloading: {attachment.name}")
                        content = self._download_attachment_content(email_data['id'], att['id'])
                        if content:
                            attachment.content = content

                    attachments.append(attachment)

        # Extract recipients
        recipients = []
        for recipient in email_data.get("toRecipients", []):
            email_addr = recipient.get("emailAddress", {})
            recipients.append(email_addr.get("address", ""))

        # Extract sender
        sender_data = email_data.get("from", {}).get("emailAddress", {})
        sender = sender_data.get("address", "")

        # Extract body
        body = email_data.get("body", {})
        body_content = body.get("content", "")
        if body.get("contentType") == "html":
            body_content = re.sub(r'<[^>]+>', '', body_content)
            body_content = body_content.strip()

        return Email(
            id=email_data.get("id", ""),
            subject=email_data.get("subject", ""),
            body=body_content,
            date=email_data.get("receivedDateTime", ""),
            sender=sender,
            recipients=recipients,
            attachments=attachments,
            conversation_id=email_data.get("conversationId", "")
        )

    def fetch_received_emails_today(self, download_attachments: bool = True) -> List[Email]:
        """Fetch received emails from today."""
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        today = datetime.now()
        start_str = today.strftime("%Y-%m-%dT00:00:00Z")
        end_str = today.strftime("%Y-%m-%dT23:59:59Z")

        filter_str = f"receivedDateTime ge {start_str} and receivedDateTime le {end_str}"

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/mailFolders/Inbox/messages"
        params = {
            "$filter": filter_str,
            "$select": "id,subject,body,receivedDateTime,from,toRecipients,hasAttachments,conversationId",
            "$orderby": "receivedDateTime desc",
            "$top": 100
        }

        print(f"\nFetching emails received today ({today.strftime('%Y-%m-%d')})...")

        response = requests.get(url, headers=self._get_headers(), params=params)

        if not response.ok:
            print(f"Error fetching emails: {response.status_code} - {response.text}")
            return []

        data = response.json()
        print(f"Found {len(data.get('value', []))} emails")

        emails = []
        for email_data in data.get("value", []):
            print(f"  Processing: {email_data.get('subject', '(no subject)')[:60]}")
            emails.append(self._parse_email(email_data, download_attachments))

        return emails

    def save_emails(self, emails: List[Email], output_dir: Path) -> None:
        """Save emails and attachments to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = output_dir / timestamp
        session_dir.mkdir(exist_ok=True)

        # Save email metadata
        metadata = {
            "downloaded_at": datetime.now().isoformat(),
            "email_count": len(emails),
            "emails": [e.to_dict() for e in emails]
        }

        with open(session_dir / "emails.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"\nSaved email metadata to {session_dir / 'emails.json'}")

        # Save attachments
        attachments_dir = session_dir / "attachments"
        attachment_count = 0

        for email in emails:
            for att in email.attachments:
                if att.content:
                    attachments_dir.mkdir(exist_ok=True)
                    # Sanitize filename
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', att.name)
                    filepath = attachments_dir / safe_name

                    # Handle duplicate names
                    counter = 1
                    original_filepath = filepath
                    while filepath.exists():
                        stem = original_filepath.stem
                        suffix = original_filepath.suffix
                        filepath = attachments_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                    with open(filepath, "wb") as f:
                        f.write(att.content)
                    attachment_count += 1
                    print(f"  Saved: {filepath.name}")

        print(f"\nDownloaded {attachment_count} attachments to {attachments_dir}")
        print(f"\nAll files saved to: {session_dir}")

    def send_email(self, to: List[str], subject: str, body: str, body_type: str = "Text", attachments: List[str] = None) -> dict:
        """
        Send an email with optional attachments.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body content
            body_type: "Text" or "HTML"
            attachments: List of file paths to attach

        Returns:
            dict with success status and details
        """
        import base64
        import hashlib
        import json
        import time
        from pathlib import Path

        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Idempotency: Check if this email was recently sent (within 5 minutes)
        sent_log_path = Path(__file__).parent / "downloads" / ".sent_emails_log.json"
        email_hash = hashlib.md5(f"{sorted(to)}:{subject}".encode()).hexdigest()
        current_time = time.time()

        sent_log = {}
        if sent_log_path.exists():
            try:
                sent_log = json.loads(sent_log_path.read_text())
                # Clean up old entries (older than 5 minutes)
                sent_log = {k: v for k, v in sent_log.items() if current_time - v < 300}
            except:
                sent_log = {}

        if email_hash in sent_log:
            elapsed = int(current_time - sent_log[email_hash])
            print(f"\n⚠️  DUPLICATE PREVENTED: This email was sent {elapsed}s ago")
            print(f"  To: {', '.join(to)}")
            print(f"  Subject: {subject}")
            return {"success": False, "reason": "duplicate", "message": f"Email already sent {elapsed}s ago"}

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/sendMail"

        # Build recipient list
        to_recipients = [
            {"emailAddress": {"address": addr}} for addr in to
        ]

        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": body_type,
                    "content": body
                },
                "toRecipients": to_recipients
            },
            "saveToSentItems": True
        }

        # Add attachments if provided
        total_size = 0
        if attachments:
            attachment_list = []
            for file_path in attachments:
                path = Path(file_path)
                if path.exists():
                    with open(path, 'rb') as f:
                        file_bytes = f.read()
                        total_size += len(file_bytes)
                        content = base64.b64encode(file_bytes).decode('utf-8')
                    attachment_list.append({
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": path.name,
                        "contentBytes": content
                    })
                    print(f"  Attaching: {path.name} ({len(file_bytes):,} bytes)")
                else:
                    print(f"  Warning: File not found: {file_path}")
            if attachment_list:
                message["message"]["attachments"] = attachment_list

        # Use longer timeout for large attachments (30s base + 10s per MB)
        timeout_seconds = 30 + (total_size // 1_000_000) * 10
        print(f"\nSending email (timeout: {timeout_seconds}s)...")
        print(f"  To: {', '.join(to)}")
        print(f"  Subject: {subject}")

        try:
            response = requests.post(url, headers=self._get_headers(), json=message, timeout=timeout_seconds)

            if response.status_code == 202:
                print("Email sent successfully!")
                # Log this send for idempotency
                sent_log[email_hash] = current_time
                sent_log_path.parent.mkdir(parents=True, exist_ok=True)
                sent_log_path.write_text(json.dumps(sent_log))
                return {"success": True, "message": "Email sent successfully"}
            else:
                print(f"Error sending email: {response.status_code} - {response.text}")
                return {"success": False, "status_code": response.status_code, "error": response.text}
        except requests.exceptions.Timeout:
            print(f"⚠️  Request timed out after {timeout_seconds}s - email MAY have been sent")
            print("   Do NOT retry immediately - check sent folder first")
            return {"success": False, "reason": "timeout", "message": "Request timed out - check sent folder before retrying"}

    def fetch_emails_range(
        self,
        start_date: datetime,
        end_date: datetime,
        download_attachments: bool = False
    ) -> List[Email]:
        """
        Fetch received emails within a date range.

        Args:
            start_date: Start date
            end_date: End date
            download_attachments: Whether to download attachment content

        Returns:
            List of Email objects
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")

        filter_str = f"receivedDateTime ge {start_str} and receivedDateTime le {end_str}"

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/mailFolders/Inbox/messages"
        params = {
            "$filter": filter_str,
            "$select": "id,subject,body,receivedDateTime,from,toRecipients,hasAttachments,conversationId,isRead",
            "$orderby": "receivedDateTime desc",
            "$top": 100
        }

        response = requests.get(url, headers=self._get_headers(), params=params)

        if not response.ok:
            raise RuntimeError(f"Error fetching emails: {response.status_code} - {response.text}")

        data = response.json()
        emails = []
        for email_data in data.get("value", []):
            emails.append(self._parse_email(email_data, download_attachments))

        return emails

    def fetch_email_by_id(self, email_id: str, download_attachments: bool = False) -> Optional[Email]:
        """
        Fetch a specific email by ID.

        Args:
            email_id: The email message ID
            download_attachments: Whether to download attachment content

        Returns:
            Email object or None if not found
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/messages/{email_id}"
        params = {
            "$select": "id,subject,body,receivedDateTime,from,toRecipients,hasAttachments,conversationId,isRead"
        }

        response = requests.get(url, headers=self._get_headers(), params=params)

        if response.status_code == 404:
            return None
        if not response.ok:
            raise RuntimeError(f"Error fetching email: {response.status_code} - {response.text}")

        return self._parse_email(response.json(), download_attachments)

    def mark_email_read(self, email_id: str, is_read: bool = True) -> bool:
        """
        Mark an email as read or unread.

        Args:
            email_id: The email message ID
            is_read: True to mark as read, False to mark as unread

        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/messages/{email_id}"

        response = requests.patch(
            url,
            headers=self._get_headers(),
            json={"isRead": is_read}
        )

        return response.ok

    def delete_email(self, email_id: str) -> bool:
        """
        Move an email to trash (soft delete).

        Args:
            email_id: The email message ID

        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        # Move to deletedItems folder instead of hard delete
        url = f"{self.graph_endpoint}/{user_path}/messages/{email_id}/move"

        response = requests.post(
            url,
            headers=self._get_headers(),
            json={"destinationId": "deleteditems"}
        )

        return response.ok

    # =========================================================================
    # MAIL FOLDER METHODS
    # =========================================================================

    def list_mail_folders(self) -> List[Dict]:
        """
        List all mail folders in the mailbox.

        Returns:
            List of folder info dicts with id, displayName, totalItemCount, unreadItemCount
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/mailFolders"
        params = {
            "$select": "id,displayName,totalItemCount,unreadItemCount,parentFolderId",
            "$top": 100
        }

        response = requests.get(url, headers=self._get_headers(), params=params)

        if not response.ok:
            raise RuntimeError(f"Error listing folders: {response.status_code} - {response.text}")

        return response.json().get("value", [])

    def get_folder_by_name(self, folder_name: str) -> Optional[Dict]:
        """
        Get a mail folder by its display name.

        Args:
            folder_name: The folder display name (e.g., "Archive", "Inbox", "Sent Items")

        Returns:
            Folder info dict or None if not found
        """
        folders = self.list_mail_folders()
        for folder in folders:
            if folder.get("displayName", "").lower() == folder_name.lower():
                return folder
        return None

    def fetch_emails_from_folder(
        self,
        folder: str = "Inbox",
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
        download_attachments: bool = False
    ) -> List[Email]:
        """
        Fetch emails from a specific folder or all folders.

        Args:
            folder: Folder name ("Inbox", "Archive", "SentItems", "Drafts", "DeletedItems")
                   or "All" to search all folders
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of emails to return
            download_attachments: Whether to download attachment content

        Returns:
            List of Email objects
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"

        # Build URL based on folder
        if folder.lower() == "all":
            # Search all folders
            url = f"{self.graph_endpoint}/{user_path}/messages"
        else:
            # Map common folder names
            folder_map = {
                "inbox": "Inbox",
                "archive": "Archive",
                "sent": "SentItems",
                "sentitems": "SentItems",
                "sent items": "SentItems",
                "drafts": "Drafts",
                "deleted": "DeletedItems",
                "deleteditems": "DeletedItems",
                "deleted items": "DeletedItems",
                "junk": "JunkEmail",
                "junkemail": "JunkEmail",
                "junk email": "JunkEmail",
            }
            folder_id = folder_map.get(folder.lower(), folder)
            url = f"{self.graph_endpoint}/{user_path}/mailFolders/{folder_id}/messages"

        # Build filter
        filters = []
        if start_date:
            start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
            filters.append(f"receivedDateTime ge {start_str}")
        if end_date:
            end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")
            filters.append(f"receivedDateTime le {end_str}")

        params = {
            "$select": "id,subject,body,receivedDateTime,sentDateTime,from,toRecipients,hasAttachments,conversationId,isRead,parentFolderId",
            "$orderby": "receivedDateTime desc",
            "$top": limit
        }

        if filters:
            params["$filter"] = " and ".join(filters)

        response = requests.get(url, headers=self._get_headers(), params=params)

        if not response.ok:
            raise RuntimeError(f"Error fetching emails: {response.status_code} - {response.text}")

        data = response.json()
        emails = []
        for email_data in data.get("value", []):
            emails.append(self._parse_email(email_data, download_attachments))

        return emails

    def search_emails(
        self,
        query: str,
        folder: str = "All",
        limit: int = 50
    ) -> List[Email]:
        """
        Search emails using Microsoft Search.

        Args:
            query: Search query (searches subject, body, sender, etc.)
            folder: Folder to search ("All" for all folders)
            limit: Maximum number of results

        Returns:
            List of matching Email objects
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"

        # Build URL
        if folder.lower() == "all":
            url = f"{self.graph_endpoint}/{user_path}/messages"
        else:
            folder_map = {
                "inbox": "Inbox",
                "archive": "Archive",
                "sent": "SentItems",
                "sentitems": "SentItems",
            }
            folder_id = folder_map.get(folder.lower(), folder)
            url = f"{self.graph_endpoint}/{user_path}/mailFolders/{folder_id}/messages"

        params = {
            "$search": f'"{query}"',
            "$select": "id,subject,body,receivedDateTime,from,toRecipients,hasAttachments,conversationId,parentFolderId",
            "$top": limit
        }

        response = requests.get(url, headers=self._get_headers(), params=params)

        if not response.ok:
            raise RuntimeError(f"Error searching emails: {response.status_code} - {response.text}")

        data = response.json()
        emails = []
        for email_data in data.get("value", []):
            emails.append(self._parse_email(email_data, download_attachments=False))

        return emails

    # =========================================================================
    # ATTACHMENT METHODS
    # =========================================================================

    def list_attachments(self, email_id: str) -> List[Dict]:
        """
        List all attachments for an email.

        Args:
            email_id: The email message ID

        Returns:
            List of attachment info dicts with id, name, size, contentType
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/messages/{email_id}/attachments"

        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            raise RuntimeError(f"Error listing attachments: {response.status_code} - {response.text}")

        attachments = []
        for att in response.json().get("value", []):
            attachments.append({
                "id": att.get("id", ""),
                "name": att.get("name", ""),
                "size": att.get("size", 0),
                "content_type": att.get("contentType", ""),
                "is_inline": att.get("isInline", False),
                "attachment_type": att.get("@odata.type", "").replace("#microsoft.graph.", "")
            })

        return attachments

    def download_attachment(self, email_id: str, attachment_id: str) -> Optional[Dict]:
        """
        Download an attachment's content.

        Args:
            email_id: The email message ID
            attachment_id: The attachment ID

        Returns:
            Dict with name, content_type, size, and content (base64 encoded)
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        user_path = f"users/{self.config.get('user_email')}" if self.config.get('user_email') else "me"
        url = f"{self.graph_endpoint}/{user_path}/messages/{email_id}/attachments/{attachment_id}"

        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            return None

        data = response.json()

        # contentBytes is base64 encoded
        return {
            "id": data.get("id", ""),
            "name": data.get("name", ""),
            "size": data.get("size", 0),
            "content_type": data.get("contentType", ""),
            "content_base64": data.get("contentBytes", "")
        }

    def save_attachment(
        self,
        email_id: str,
        attachment_id: str,
        output_dir: Path = None
    ) -> Optional[Path]:
        """
        Download and save an attachment to disk.

        Args:
            email_id: The email message ID
            attachment_id: The attachment ID
            output_dir: Directory to save to (default: downloads folder)

        Returns:
            Path to saved file or None if failed
        """
        if output_dir is None:
            output_dir = DOWNLOADS_DIR / "attachments"

        output_dir.mkdir(parents=True, exist_ok=True)

        attachment = self.download_attachment(email_id, attachment_id)
        if not attachment or not attachment.get("content_base64"):
            return None

        # Decode and save
        content = base64.b64decode(attachment["content_base64"])

        # Sanitize filename
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', attachment["name"])
        filepath = output_dir / safe_name

        # Handle duplicate names
        counter = 1
        original_filepath = filepath
        while filepath.exists():
            stem = original_filepath.stem
            suffix = original_filepath.suffix
            filepath = output_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        with open(filepath, "wb") as f:
            f.write(content)

        return filepath

    # =========================================================================
    # SHAREPOINT METHODS
    # =========================================================================

    def get_sharepoint_site(self, site_path: str) -> Optional[Dict]:
        """
        Get SharePoint site info.

        Args:
            site_path: Site path like "xcellerateeq.sharepoint.com:/sites/DevTeam"

        Returns:
            Site info dict or None if not found
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        url = f"{self.graph_endpoint}/sites/{site_path}"
        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            return None
        return response.json()

    def list_sharepoint_drives(self, site_id: str) -> List[Dict]:
        """
        List document libraries (drives) in a SharePoint site.

        Args:
            site_id: The SharePoint site ID

        Returns:
            List of drive info dicts
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        url = f"{self.graph_endpoint}/sites/{site_id}/drives"
        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            raise RuntimeError(f"Error listing drives: {response.status_code} - {response.text}")

        return response.json().get("value", [])

    def list_sharepoint_files(
        self,
        site_id: str,
        drive_id: str = None,
        folder_path: str = "",
        recursive: bool = False
    ) -> List[SharePointFile]:
        """
        List files in a SharePoint document library.

        Args:
            site_id: The SharePoint site ID
            drive_id: The drive/document library ID (uses default if None)
            folder_path: Path within the drive (empty for root)
            recursive: If True, list all files recursively

        Returns:
            List of SharePointFile objects
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Get default drive if not specified
        if not drive_id:
            drives = self.list_sharepoint_drives(site_id)
            if not drives:
                raise RuntimeError("No document libraries found in site")
            drive_id = drives[0]["id"]

        # Build URL based on folder path
        if folder_path:
            url = f"{self.graph_endpoint}/sites/{site_id}/drives/{drive_id}/root:/{folder_path}:/children"
        else:
            url = f"{self.graph_endpoint}/sites/{site_id}/drives/{drive_id}/root/children"

        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            raise RuntimeError(f"Error listing files: {response.status_code} - {response.text}")

        files = []
        for item in response.json().get("value", []):
            # Skip folders unless recursive
            if "folder" in item and not recursive:
                continue

            files.append(SharePointFile(
                id=item.get("id", ""),
                name=item.get("name", ""),
                size=item.get("size", 0),
                web_url=item.get("webUrl", ""),
                created=item.get("createdDateTime", ""),
                modified=item.get("lastModifiedDateTime", ""),
                created_by=item.get("createdBy", {}).get("user", {}).get("displayName", ""),
                modified_by=item.get("lastModifiedBy", {}).get("user", {}).get("displayName", ""),
                mime_type=item.get("file", {}).get("mimeType", "") if "file" in item else "folder",
                parent_path=item.get("parentReference", {}).get("path", "")
            ))

        return files

    def get_sharepoint_file_content(self, site_id: str, drive_id: str, item_id: str) -> Optional[bytes]:
        """
        Download SharePoint file content.

        Args:
            site_id: The SharePoint site ID
            drive_id: The drive/document library ID
            item_id: The file item ID

        Returns:
            File content as bytes or None if failed
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        url = f"{self.graph_endpoint}/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            return None
        return response.content

    def search_sharepoint_files(self, site_id: str, query: str) -> List[SharePointFile]:
        """
        Search for files in a SharePoint site.

        Args:
            site_id: The SharePoint site ID
            query: Search query string

        Returns:
            List of matching SharePointFile objects
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        url = f"{self.graph_endpoint}/sites/{site_id}/drive/root/search(q='{query}')"
        response = requests.get(url, headers=self._get_headers())

        if not response.ok:
            raise RuntimeError(f"Error searching files: {response.status_code} - {response.text}")

        files = []
        for item in response.json().get("value", []):
            if "file" not in item:
                continue  # Skip folders

            files.append(SharePointFile(
                id=item.get("id", ""),
                name=item.get("name", ""),
                size=item.get("size", 0),
                web_url=item.get("webUrl", ""),
                created=item.get("createdDateTime", ""),
                modified=item.get("lastModifiedDateTime", ""),
                created_by=item.get("createdBy", {}).get("user", {}).get("displayName", ""),
                modified_by=item.get("lastModifiedBy", {}).get("user", {}).get("displayName", ""),
                mime_type=item.get("file", {}).get("mimeType", ""),
                parent_path=item.get("parentReference", {}).get("path", "")
            ))

        return files

    def save_sharepoint_file(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        filename: str,
        output_dir: str = None
    ) -> Optional[str]:
        """
        Download and save a SharePoint file to disk.

        Args:
            site_id: The SharePoint site ID
            drive_id: The drive/document library ID
            item_id: The file item ID
            filename: Name to save the file as
            output_dir: Directory to save to (default: downloads/sharepoint)

        Returns:
            Path to saved file or None if failed
        """
        content = self.get_sharepoint_file_content(site_id, drive_id, item_id)
        if content is None:
            return None

        if output_dir is None:
            output_dir = Path(__file__).parent / "downloads" / "sharepoint"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / filename

        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path)


def cmd_download(args):
    """Download emails command."""
    downloader = OutlookEmailDownloader()

    print("=" * 60)
    print("Outlook Email Downloader")
    print("=" * 60)

    if not MICROSOFT_CONFIG.get("client_id"):
        print("ERROR: MS_CLIENT_ID not set. Check .env file in clockify-automation.")
        sys.exit(1)

    if not downloader.authenticate():
        print("ERROR: Authentication failed!")
        sys.exit(1)

    emails = downloader.fetch_received_emails_today(
        download_attachments=not args.no_attachments
    )

    if not emails:
        print("\nNo emails received today.")
        return

    downloader.save_emails(emails, Path(args.output))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Emails downloaded: {len(emails)}")
    total_attachments = sum(len(e.attachments) for e in emails)
    print(f"Total attachments: {total_attachments}")

    for email in emails:
        att_count = len(email.attachments)
        att_str = f" [{att_count} attachments]" if att_count else ""
        print(f"  - {email.date[:16]} | {email.sender[:30]} | {email.subject[:40]}{att_str}")


def cmd_send(args):
    """Send email command."""
    downloader = OutlookEmailDownloader()

    print("=" * 60)
    print("Outlook Email Sender")
    print("=" * 60)

    if not MICROSOFT_CONFIG.get("client_id"):
        print("ERROR: MS_CLIENT_ID not set. Check .env file in clockify-automation.")
        sys.exit(1)

    if not downloader.authenticate():
        print("ERROR: Authentication failed!")
        sys.exit(1)

    recipients = [addr.strip() for addr in args.to.split(",")]
    success = downloader.send_email(
        to=recipients,
        subject=args.subject,
        body=args.body,
        body_type="HTML" if args.html else "Text"
    )

    sys.exit(0 if success else 1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Outlook Email Tool - Download and send emails")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download today's emails")
    download_parser.add_argument("--no-attachments", action="store_true", help="Skip downloading attachments")
    download_parser.add_argument("--output", "-o", default=str(DOWNLOADS_DIR), help="Output directory")

    # Send command
    send_parser = subparsers.add_parser("send", help="Send an email")
    send_parser.add_argument("--to", "-t", required=True, help="Recipient email(s), comma-separated")
    send_parser.add_argument("--subject", "-s", required=True, help="Email subject")
    send_parser.add_argument("--body", "-b", required=True, help="Email body")
    send_parser.add_argument("--html", action="store_true", help="Send body as HTML")

    args = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "send":
        cmd_send(args)
    else:
        # Default to download for backwards compatibility
        args.no_attachments = False
        args.output = str(DOWNLOADS_DIR)
        cmd_download(args)


if __name__ == "__main__":
    main()
