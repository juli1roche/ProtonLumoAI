#!/usr/bin/env python3
"""
Executive Summary Email Reporter
Generates and sends HTML formatted executive summaries
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from important_message_detector import ImportantMessage


class SummaryEmailReporter:
    """
    Generates and sends executive summary reports via email
    """

    def __init__(self, imap_connection=None):
        """
        Initialize reporter

        Args:
            imap_connection: Existing IMAP connection (optional)
        """
        self.imap = imap_connection
        self.summary_folder = os.getenv(
            "PROTON_LUMO_SUMMARY_FOLDER", "Folders/Exec-Summary"
        )
        self.recipient_email = os.getenv(
            "PROTON_LUMO_SUMMARY_EMAIL", "juli1.roche@gmail.com"
        )

    def generate_html_report(self, summary: Dict) -> str:
        """
        Generate HTML formatted executive summary

        Args:
            summary: Summary dictionary from ImportantMessageDetector

        Returns:
            HTML string
        """
        timestamp = summary["timestamp"]
        urgent_count = summary["urgent_count"]
        high_count = summary["high_count"]
        medium_count = summary["medium_count"]
        total_count = summary["total_count"]

        # Build urgency sections
        urgent_html = self._build_urgency_section(
            "🔴 URGENT", summary["urgent"], "urgent"
        )
        high_html = self._build_urgency_section(
            "🟠 HIGH PRIORITY", summary["high"], "high"
        )
        medium_html = self._build_urgency_section(
            "🟡 MEDIUM PRIORITY", summary["medium"], "medium"
        )

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executive Summary</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .timestamp {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .section {{
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .section.urgent {{
            border-left-color: #dc3545;
        }}
        .section.high {{
            border-left-color: #fd7e14;
        }}
        .section.medium {{
            border-left-color: #ffc107;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
        }}
        .message {{
            background-color: #f8f9fa;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 3px solid #667eea;
        }}
        .message-subject {{
            font-weight: bold;
            color: #333;
        }}
        .message-meta {{
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }}
        .action-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 5px;
        }}
        .action-respond {{
            background-color: #dc3545;
            color: white;
        }}
        .action-verify {{
            background-color: #fd7e14;
            color: white;
        }}
        .action-track {{
            background-color: #ffc107;
            color: black;
        }}
        .action-review {{
            background-color: #667eea;
            color: white;
        }}
        .stats {{
            display: flex;
            gap: 15px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        .stat {{
            flex: 1;
            text-align: center;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        .stat-number {{
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .empty {{
            text-align: center;
            color: #999;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Executive Summary</h1>
        <div class="timestamp">{timestamp}</div>
    </div>

    {urgent_html}
    {high_html}
    {medium_html}

    <div class="section">
        <h3>📊 Daily Statistics</h3>
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{urgent_count}</div>
                <div class="stat-label">Urgent</div>
            </div>
            <div class="stat">
                <div class="stat-number">{high_count}</div>
                <div class="stat-label">High Priority</div>
            </div>
            <div class="stat">
                <div class="stat-number">{medium_count}</div>
                <div class="stat-label">Medium Priority</div>
            </div>
            <div class="stat">
                <div class="stat-number">{total_count}</div>
                <div class="stat-label">Total Important</div>
            </div>
        </div>
    </div>
</body>
</html>
        """
        return html

    def _build_urgency_section(self, title: str, messages: List[Dict], style_class: str) -> str:
        """
        Build HTML for a single urgency section
        """
        if not messages:
            return ""

        messages_html = ""
        for i, msg in enumerate(messages, 1):
            action_class = f"action-{msg['action']}"
            action_badge = (
                f'<span class="action-badge {action_class}">{msg["action"].upper()}</span>'
                if msg["action"] != "none"
                else ""
            )

            messages_html += f"""
            <div class="message">
                <div class="message-subject">{i}. {msg['subject']}</div>
                <div class="message-meta">
                    From: {msg['from']} | Category: {msg['category']} | Score: {msg['score']}<br>
                    {action_badge}
                </div>
            </div>
            """

        return f"""
        <div class="section {style_class}">
            <h2>{title} ({len(messages)} messages)</h2>
            {messages_html}
        </div>
        """

    def send_summary_email(
        self, html_content: str, subject_suffix: str = ""
    ) -> bool:
        """
        Send executive summary via email (as unseen message in folder)

        Args:
            html_content: HTML content of the summary
            subject_suffix: Optional suffix for subject line

        Returns:
            True if successful
        """
        if not self.imap:
            logger.error("No IMAP connection available for sending email")
            return False

        try:
            # Ensure summary folder exists
            self._ensure_folder_exists()

            # Build email message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            subject = f"📧 Executive Summary - {timestamp} {subject_suffix}"

            # Create simple email format (ProtonMail will handle formatting)
            email_message = f"""
Subject: {subject}
From: {self.recipient_email}
Content-Type: text/html; charset=utf-8

{html_content}
            """.encode("utf-8")

            # Append to Exec-Summary folder
            folder_name = self.summary_folder.replace("Folders/", "")
            self.imap.append(folder_name, [], None, email_message)

            logger.success(
                f"Executive summary sent to {self.summary_folder} (unseen)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send summary email: {e}")
            return False

    def _ensure_folder_exists(self) -> bool:
        """
        Ensure the summary folder exists
        """
        try:
            folder_name = self.summary_folder.replace("Folders/", "")
            if self.imap.folder_exists(folder_name):
                return True

            # Create folder
            self.imap.create_folder(folder_name)
            logger.success(f"Created folder: {self.summary_folder}")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure folder exists: {e}")
            return False

    def save_summary_locally(self, summary: Dict, html_content: str) -> bool:
        """
        Save summary to local files for backup

        Args:
            summary: Summary dictionary
            html_content: HTML formatted content

        Returns:
            True if successful
        """
        try:
            data_dir = Path(
                os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")
            ).expanduser()
            data_dir.mkdir(parents=True, exist_ok=True)

            # Save JSON summary
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = data_dir / f"summary_{timestamp}.json"
            with open(json_file, "w") as f:
                json.dump(summary, f, indent=2)

            # Save HTML report
            html_file = data_dir / f"summary_{timestamp}.html"
            with open(html_file, "w") as f:
                f.write(html_content)

            logger.info(f"Summary saved to {json_file} and {html_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save summary locally: {e}")
            return False
