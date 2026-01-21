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
    "scopes": ["Mail.Read", "Mail.ReadWrite", "Mail.Send", "User.Read"],
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

    def send_email(self, to: List[str], subject: str, body: str, body_type: str = "Text") -> bool:
        """
        Send an email.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body content
            body_type: "Text" or "HTML"

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

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

        print(f"\nSending email...")
        print(f"  To: {', '.join(to)}")
        print(f"  Subject: {subject}")

        response = requests.post(url, headers=self._get_headers(), json=message)

        if response.status_code == 202:
            print("Email sent successfully!")
            return True
        else:
            print(f"Error sending email: {response.status_code} - {response.text}")
            return False

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
