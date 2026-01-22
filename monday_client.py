#!/usr/bin/env python3
"""
Monday.com API Client using GraphQL.
"""
import os
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Load env from clockify-automation
from dotenv import load_dotenv
CLOCKIFY_AUTOMATION_DIR = Path("/Users/Mike/Documents/programming/3_current_projects/vvg/clockify-automation")
load_dotenv(CLOCKIFY_AUTOMATION_DIR / ".env")

MONDAY_CONFIG = {
    "api_key": os.environ.get("MONDAY_API_KEY"),
    "api_url": "https://api.monday.com/v2",
    "api_version": "2025-10"
}


@dataclass
class MondayBoard:
    """Represents a Monday.com board."""
    id: str
    name: str
    description: str
    state: str
    board_kind: str
    workspace_id: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MondayItem:
    """Represents a Monday.com item (row)."""
    id: str
    name: str
    board_id: str
    group_id: str
    state: str
    created_at: str
    updated_at: str
    column_values: Dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MondayGroup:
    """Represents a Monday.com group."""
    id: str
    title: str
    color: str
    position: str

    def to_dict(self) -> Dict:
        return asdict(self)


class MondayClient:
    """Client for Monday.com GraphQL API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or MONDAY_CONFIG.get("api_key")
        self.api_url = MONDAY_CONFIG["api_url"]
        self.api_version = MONDAY_CONFIG["api_version"]

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "API-Version": self.api_version
        }

    def _execute_query(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload
        )

        if not response.ok:
            raise RuntimeError(f"Monday API error: {response.status_code} - {response.text}")

        data = response.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        return data.get("data", {})

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    def list_boards(self, limit: int = 50) -> List[MondayBoard]:
        """
        List all boards accessible to the user.

        Args:
            limit: Maximum number of boards to return

        Returns:
            List of MondayBoard objects
        """
        query = """
        query ($limit: Int!) {
            boards(limit: $limit) {
                id
                name
                description
                state
                board_kind
                workspace_id
            }
        }
        """

        data = self._execute_query(query, {"limit": limit})
        boards = []
        for b in data.get("boards", []):
            boards.append(MondayBoard(
                id=b.get("id", ""),
                name=b.get("name", ""),
                description=b.get("description", "") or "",
                state=b.get("state", ""),
                board_kind=b.get("board_kind", ""),
                workspace_id=str(b.get("workspace_id", "") or "")
            ))
        return boards

    def get_board(self, board_id: str) -> Optional[MondayBoard]:
        """
        Get a specific board by ID.

        Args:
            board_id: The board ID

        Returns:
            MondayBoard object or None
        """
        query = """
        query ($ids: [ID!]!) {
            boards(ids: $ids) {
                id
                name
                description
                state
                board_kind
                workspace_id
            }
        }
        """

        data = self._execute_query(query, {"ids": [board_id]})
        boards = data.get("boards", [])
        if not boards:
            return None

        b = boards[0]
        return MondayBoard(
            id=b.get("id", ""),
            name=b.get("name", ""),
            description=b.get("description", "") or "",
            state=b.get("state", ""),
            board_kind=b.get("board_kind", ""),
            workspace_id=str(b.get("workspace_id", "") or "")
        )

    def list_groups(self, board_id: str) -> List[MondayGroup]:
        """
        List groups in a board.

        Args:
            board_id: The board ID

        Returns:
            List of MondayGroup objects
        """
        query = """
        query ($ids: [ID!]!) {
            boards(ids: $ids) {
                groups {
                    id
                    title
                    color
                    position
                }
            }
        }
        """

        data = self._execute_query(query, {"ids": [board_id]})
        boards = data.get("boards", [])
        if not boards:
            return []

        groups = []
        for g in boards[0].get("groups", []):
            groups.append(MondayGroup(
                id=g.get("id", ""),
                title=g.get("title", ""),
                color=g.get("color", ""),
                position=g.get("position", "")
            ))
        return groups

    def list_items(self, board_id: str, limit: int = 100) -> List[MondayItem]:
        """
        List items in a board.

        Args:
            board_id: The board ID
            limit: Maximum number of items

        Returns:
            List of MondayItem objects
        """
        query = """
        query ($ids: [ID!]!, $limit: Int!) {
            boards(ids: $ids) {
                items_page(limit: $limit) {
                    items {
                        id
                        name
                        state
                        created_at
                        updated_at
                        group {
                            id
                        }
                        column_values {
                            id
                            text
                            value
                        }
                    }
                }
            }
        }
        """

        data = self._execute_query(query, {"ids": [board_id], "limit": limit})
        boards = data.get("boards", [])
        if not boards:
            return []

        items = []
        items_data = boards[0].get("items_page", {}).get("items", [])
        for item in items_data:
            # Parse column values into dict
            col_values = {}
            for cv in item.get("column_values", []):
                col_values[cv.get("id", "")] = {
                    "text": cv.get("text", ""),
                    "value": cv.get("value", "")
                }

            items.append(MondayItem(
                id=item.get("id", ""),
                name=item.get("name", ""),
                board_id=board_id,
                group_id=item.get("group", {}).get("id", ""),
                state=item.get("state", ""),
                created_at=item.get("created_at", ""),
                updated_at=item.get("updated_at", ""),
                column_values=col_values
            ))
        return items

    def get_item(self, item_id: str) -> Optional[MondayItem]:
        """
        Get a specific item by ID.

        Args:
            item_id: The item ID

        Returns:
            MondayItem object or None
        """
        query = """
        query ($ids: [ID!]!) {
            items(ids: $ids) {
                id
                name
                state
                created_at
                updated_at
                board {
                    id
                }
                group {
                    id
                }
                column_values {
                    id
                    text
                    value
                }
            }
        }
        """

        data = self._execute_query(query, {"ids": [item_id]})
        items = data.get("items", [])
        if not items:
            return None

        item = items[0]
        col_values = {}
        for cv in item.get("column_values", []):
            col_values[cv.get("id", "")] = {
                "text": cv.get("text", ""),
                "value": cv.get("value", "")
            }

        return MondayItem(
            id=item.get("id", ""),
            name=item.get("name", ""),
            board_id=item.get("board", {}).get("id", ""),
            group_id=item.get("group", {}).get("id", ""),
            state=item.get("state", ""),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
            column_values=col_values
        )

    def get_columns(self, board_id: str) -> List[Dict]:
        """
        Get column definitions for a board.

        Args:
            board_id: The board ID

        Returns:
            List of column definitions
        """
        query = """
        query ($ids: [ID!]!) {
            boards(ids: $ids) {
                columns {
                    id
                    title
                    type
                    settings_str
                }
            }
        }
        """

        data = self._execute_query(query, {"ids": [board_id]})
        boards = data.get("boards", [])
        if not boards:
            return []

        return boards[0].get("columns", [])

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    def create_item(
        self,
        board_id: str,
        item_name: str,
        group_id: str = None,
        column_values: Dict = None
    ) -> Optional[MondayItem]:
        """
        Create a new item in a board.

        Args:
            board_id: The board ID
            item_name: Name of the new item
            group_id: Optional group ID (uses first group if not specified)
            column_values: Optional dict of column_id -> value

        Returns:
            Created MondayItem or None
        """
        import json

        # Build mutation
        if column_values:
            col_values_json = json.dumps(column_values)
            mutation = """
            mutation ($board_id: ID!, $item_name: String!, $group_id: String, $column_values: JSON!) {
                create_item(
                    board_id: $board_id,
                    item_name: $item_name,
                    group_id: $group_id,
                    column_values: $column_values
                ) {
                    id
                    name
                    created_at
                }
            }
            """
            variables = {
                "board_id": board_id,
                "item_name": item_name,
                "group_id": group_id,
                "column_values": col_values_json
            }
        else:
            mutation = """
            mutation ($board_id: ID!, $item_name: String!, $group_id: String) {
                create_item(
                    board_id: $board_id,
                    item_name: $item_name,
                    group_id: $group_id
                ) {
                    id
                    name
                    created_at
                }
            }
            """
            variables = {
                "board_id": board_id,
                "item_name": item_name,
                "group_id": group_id
            }

        data = self._execute_query(mutation, variables)
        item_data = data.get("create_item", {})

        if not item_data:
            return None

        return MondayItem(
            id=item_data.get("id", ""),
            name=item_data.get("name", ""),
            board_id=board_id,
            group_id=group_id or "",
            state="active",
            created_at=item_data.get("created_at", ""),
            updated_at="",
            column_values=column_values or {}
        )

    def update_item(
        self,
        board_id: str,
        item_id: str,
        column_values: Dict
    ) -> bool:
        """
        Update column values of an item.

        Args:
            board_id: The board ID
            item_id: The item ID
            column_values: Dict of column_id -> value

        Returns:
            True if successful
        """
        import json

        mutation = """
        mutation ($board_id: ID!, $item_id: ID!, $column_values: JSON!) {
            change_multiple_column_values(
                board_id: $board_id,
                item_id: $item_id,
                column_values: $column_values
            ) {
                id
            }
        }
        """

        data = self._execute_query(mutation, {
            "board_id": board_id,
            "item_id": item_id,
            "column_values": json.dumps(column_values)
        })

        return "change_multiple_column_values" in data

    def update_item_name(self, board_id: str, item_id: str, new_name: str) -> bool:
        """
        Update the name of an item.

        Args:
            board_id: The board ID
            item_id: The item ID
            new_name: New name for the item

        Returns:
            True if successful
        """
        mutation = """
        mutation ($board_id: ID!, $item_id: ID!, $column_values: JSON!) {
            change_multiple_column_values(
                board_id: $board_id,
                item_id: $item_id,
                column_values: $column_values
            ) {
                id
                name
            }
        }
        """

        import json
        data = self._execute_query(mutation, {
            "board_id": board_id,
            "item_id": item_id,
            "column_values": json.dumps({"name": new_name})
        })

        return "change_multiple_column_values" in data

    def delete_item(self, item_id: str) -> bool:
        """
        Delete an item.

        Args:
            item_id: The item ID

        Returns:
            True if successful
        """
        mutation = """
        mutation ($item_id: ID!) {
            delete_item(item_id: $item_id) {
                id
            }
        }
        """

        data = self._execute_query(mutation, {"item_id": item_id})
        return "delete_item" in data

    def move_item_to_group(self, item_id: str, group_id: str) -> bool:
        """
        Move an item to a different group.

        Args:
            item_id: The item ID
            group_id: Target group ID

        Returns:
            True if successful
        """
        mutation = """
        mutation ($item_id: ID!, $group_id: String!) {
            move_item_to_group(item_id: $item_id, group_id: $group_id) {
                id
            }
        }
        """

        data = self._execute_query(mutation, {
            "item_id": item_id,
            "group_id": group_id
        })

        return "move_item_to_group" in data


# CLI for testing
if __name__ == "__main__":
    client = MondayClient()

    if not client.api_key:
        print("ERROR: MONDAY_API_KEY not set in .env")
        exit(1)

    print("Testing Monday.com API...")

    boards = client.list_boards(limit=10)
    print(f"\nFound {len(boards)} boards:")
    for b in boards:
        print(f"  - {b.name} (ID: {b.id})")
