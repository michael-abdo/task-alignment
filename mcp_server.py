#!/usr/bin/env python3
"""
MCP Server for Outlook Email and SharePoint operations.
Provides CRUD operations for emails and files via Model Context Protocol.
"""
import sys
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Import the email downloader
from download_emails import OutlookEmailDownloader, MICROSOFT_CONFIG

# Create MCP server
mcp = FastMCP("outlook-email")

# Global client instance (authenticated lazily)
_client: Optional[OutlookEmailDownloader] = None


def get_client() -> OutlookEmailDownloader:
    """Get authenticated email client (singleton)."""
    global _client
    if _client is None:
        _client = OutlookEmailDownloader()
        if not MICROSOFT_CONFIG.get("client_id"):
            raise RuntimeError("MS_CLIENT_ID not set. Check .env file.")
        if not _client.authenticate():
            raise RuntimeError("Authentication failed")
    return _client


# =============================================================================
# CREATE
# =============================================================================

@mcp.tool()
def send_email(to: str, subject: str, body: str, html: bool = False) -> dict:
    """
    Send an email.

    Args:
        to: Recipient email address(es), comma-separated for multiple
        subject: Email subject line
        body: Email body content
        html: If True, send body as HTML. Default is plain text.

    Returns:
        dict with success status
    """
    try:
        client = get_client()
        recipients = [addr.strip() for addr in to.split(",")]
        body_type = "HTML" if html else "Text"
        success = client.send_email(recipients, subject, body, body_type)
        return {
            "success": success,
            "message": f"Email sent to {to}" if success else "Failed to send email"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# READ
# =============================================================================

@mcp.tool()
def list_emails_today(limit: int = 50) -> dict:
    """
    List emails received today.

    Args:
        limit: Maximum number of emails to return (default 50)

    Returns:
        dict with list of emails
    """
    try:
        client = get_client()
        emails = client.fetch_received_emails_today(download_attachments=False)
        emails = emails[:limit]
        return {
            "success": True,
            "count": len(emails),
            "emails": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "sender": e.sender,
                    "date": e.date,
                    "has_attachments": len(e.attachments) > 0,
                    "body_preview": e.body[:200] + "..." if len(e.body) > 200 else e.body
                }
                for e in emails
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def list_emails(start_date: str, end_date: str, limit: int = 50) -> dict:
    """
    List emails received within a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of emails to return (default 50)

    Returns:
        dict with list of emails
    """
    try:
        client = get_client()
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        emails = client.fetch_emails_range(start, end, download_attachments=False)
        emails = emails[:limit]
        return {
            "success": True,
            "count": len(emails),
            "date_range": {"start": start_date, "end": end_date},
            "emails": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "sender": e.sender,
                    "date": e.date,
                    "has_attachments": len(e.attachments) > 0,
                    "body_preview": e.body[:200] + "..." if len(e.body) > 200 else e.body
                }
                for e in emails
            ]
        }
    except ValueError as e:
        return {"success": False, "error": f"Invalid date format. Use YYYY-MM-DD. {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_email(email_id: str) -> dict:
    """
    Get a specific email by ID.

    Args:
        email_id: The email message ID

    Returns:
        dict with email details including full body
    """
    try:
        client = get_client()
        email = client.fetch_email_by_id(email_id, download_attachments=False)
        if email is None:
            return {"success": False, "error": "Email not found"}
        return {
            "success": True,
            "email": {
                "id": email.id,
                "subject": email.subject,
                "sender": email.sender,
                "recipients": email.recipients,
                "date": email.date,
                "body": email.body,
                "attachments": [
                    {"name": a.name, "size": a.size, "content_type": a.content_type}
                    for a in email.attachments
                ],
                "conversation_id": email.conversation_id
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# UPDATE
# =============================================================================

@mcp.tool()
def mark_as_read(email_id: str, is_read: bool = True) -> dict:
    """
    Mark an email as read or unread.

    Args:
        email_id: The email message ID
        is_read: True to mark as read, False to mark as unread (default True)

    Returns:
        dict with success status
    """
    try:
        client = get_client()
        success = client.mark_email_read(email_id, is_read)
        status = "read" if is_read else "unread"
        return {
            "success": success,
            "message": f"Email marked as {status}" if success else f"Failed to mark email as {status}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# DELETE
# =============================================================================

@mcp.tool()
def delete_email(email_id: str) -> dict:
    """
    Move an email to trash (soft delete).

    Args:
        email_id: The email message ID

    Returns:
        dict with success status
    """
    try:
        client = get_client()
        success = client.delete_email(email_id)
        return {
            "success": success,
            "message": "Email moved to trash" if success else "Failed to delete email"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SHAREPOINT - READ
# =============================================================================

# Default site for convenience
DEFAULT_SITE = "xcellerateeq.sharepoint.com:/sites/DevTeam"


@mcp.tool()
def get_sharepoint_site(site_path: str = DEFAULT_SITE) -> dict:
    """
    Get SharePoint site information.

    Args:
        site_path: Site path like "xcellerateeq.sharepoint.com:/sites/DevTeam"

    Returns:
        dict with site info including site_id needed for other operations
    """
    try:
        client = get_client()
        site = client.get_sharepoint_site(site_path)
        if not site:
            return {"success": False, "error": "Site not found"}
        return {
            "success": True,
            "site": {
                "id": site.get("id", ""),
                "name": site.get("displayName", ""),
                "description": site.get("description", ""),
                "web_url": site.get("webUrl", ""),
                "created": site.get("createdDateTime", "")
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def list_sharepoint_drives(site_id: str) -> dict:
    """
    List document libraries (drives) in a SharePoint site.

    Args:
        site_id: The SharePoint site ID (get from get_sharepoint_site)

    Returns:
        dict with list of document libraries
    """
    try:
        client = get_client()
        drives = client.list_sharepoint_drives(site_id)
        return {
            "success": True,
            "count": len(drives),
            "drives": [
                {
                    "id": d.get("id", ""),
                    "name": d.get("name", ""),
                    "description": d.get("description", ""),
                    "web_url": d.get("webUrl", ""),
                    "drive_type": d.get("driveType", "")
                }
                for d in drives
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def list_sharepoint_files(site_id: str, drive_id: str = "", folder_path: str = "") -> dict:
    """
    List files in a SharePoint document library.

    Args:
        site_id: The SharePoint site ID
        drive_id: The drive/document library ID (optional, uses default if empty)
        folder_path: Path within the drive (optional, empty for root)

    Returns:
        dict with list of files
    """
    try:
        client = get_client()
        files = client.list_sharepoint_files(
            site_id,
            drive_id if drive_id else None,
            folder_path
        )
        return {
            "success": True,
            "count": len(files),
            "folder_path": folder_path or "/",
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "size": f.size,
                    "mime_type": f.mime_type,
                    "web_url": f.web_url,
                    "modified": f.modified,
                    "modified_by": f.modified_by
                }
                for f in files
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def search_sharepoint_files(site_id: str, query: str) -> dict:
    """
    Search for files in a SharePoint site.

    Args:
        site_id: The SharePoint site ID
        query: Search query string (searches file names and content)

    Returns:
        dict with list of matching files
    """
    try:
        client = get_client()
        files = client.search_sharepoint_files(site_id, query)
        return {
            "success": True,
            "count": len(files),
            "query": query,
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "size": f.size,
                    "mime_type": f.mime_type,
                    "web_url": f.web_url,
                    "modified": f.modified,
                    "parent_path": f.parent_path
                }
                for f in files
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_sharepoint_file_info(site_id: str, drive_id: str, item_id: str) -> dict:
    """
    Get detailed information about a SharePoint file.

    Args:
        site_id: The SharePoint site ID
        drive_id: The drive/document library ID
        item_id: The file item ID

    Returns:
        dict with file details
    """
    try:
        client = get_client()
        url = f"{client.graph_endpoint}/sites/{site_id}/drives/{drive_id}/items/{item_id}"
        response = __import__('requests').get(url, headers=client._get_headers())

        if not response.ok:
            return {"success": False, "error": f"File not found: {response.status_code}"}

        item = response.json()
        return {
            "success": True,
            "file": {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "size": item.get("size", 0),
                "mime_type": item.get("file", {}).get("mimeType", ""),
                "web_url": item.get("webUrl", ""),
                "created": item.get("createdDateTime", ""),
                "modified": item.get("lastModifiedDateTime", ""),
                "created_by": item.get("createdBy", {}).get("user", {}).get("displayName", ""),
                "modified_by": item.get("lastModifiedBy", {}).get("user", {}).get("displayName", ""),
                "download_url": item.get("@microsoft.graph.downloadUrl", "")
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("Starting Outlook Email MCP Server...", file=sys.stderr)
    mcp.run()
