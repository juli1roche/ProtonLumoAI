#!/usr/bin/env python3
"""
Important Message Detector
Detects and scores important messages based on multiple criteria
Generates executive summaries at specified times
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
import re


@dataclass
class ImportantMessage:
    """Represents an important message with scoring details"""
    message_id: str
    from_email: str
    subject: str
    score: int
    category: str
    criteria_breakdown: Dict[str, int]  # {criterion: points}
    action_type: str  # respond, verify, track, review, none
    status: str  # new, viewed, actioned, dismissed
    detected_at: str
    category_confidence: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class ImportantMessageDetector:
    """Detects and scores important messages"""

    # Scoring criteria
    SCORES = {
        "PRO": 30,  # Work/professional emails
        "BANQUE": 25,  # Financial/banking
        "VENTE": 5,  # Shopping (low importance)
        "SPAM": -100,  # Spam (exclude)
        "urgent_keywords": 15,  # urgent, important, action required
        "important_contact": 20,  # Key family/professional contacts
        "important_domain": 20,  # Key domains (cirrus.com, etc.)
        "frequent_sender": 10,  # >3 emails/month
        "new_domain": 10,  # First contact from domain
        "no_reply_7days": 5,  # Waiting >7 days for response
        "relocation_keyword": 10,  # Scotland relocation related
    }

    IMPORTANCE_THRESHOLD = 30
    URGENT_THRESHOLD = 85
    HIGH_THRESHOLD = 50

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize detector

        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = Path(
            config_dir or os.getenv(
                "PROTON_LUMO_CONFIG", "~/ProtonLumoAI/config"
            )
        ).expanduser()
        self.data_dir = Path(
            os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")
        ).expanduser()

        self.important_messages_file = self.data_dir / "important_messages.json"
        self.important_contacts = self._load_important_contacts()
        self.relocation_keywords = self._load_relocation_keywords()
        self.important_domains = self._load_important_domains()
        self.frequent_senders = self._load_frequent_senders()

        logger.info("ImportantMessageDetector initialized")

    def _load_important_contacts(self) -> List[str]:
        """Load important contacts from env"""
        contacts_str = os.getenv(
            "PROTON_LUMO_IMPORTANT_CONTACTS",
            "brigitte.clavel@gmail.com,frederic.roche@gmail.com",
        )
        return [c.strip().lower() for c in contacts_str.split(",")]

    def _load_relocation_keywords(self) -> List[str]:
        """Load relocation-related keywords from env"""
        keywords_str = os.getenv(
            "PROTON_LUMO_RELOCATION_KEYWORDS",
            "scotland,visa,relocation,edinburgh,currie,enrollment",
        )
        return [k.strip().lower() for k in keywords_str.split(",")]

    def _load_important_domains(self) -> Dict[str, int]:
        """Load important domains with scores from env"""
        domains_str = os.getenv(
            "PROTON_LUMO_IMPORTANT_DOMAINS",
            "cirrus.com:20,iqaimmigration.com:15",
        )
        domains_dict = {}
        for item in domains_str.split(","):
            if ":" in item:
                domain, score = item.strip().split(":")
                domains_dict[domain.lower()] = int(score)
        return domains_dict

    def _load_frequent_senders(self) -> Dict[str, int]:
        """Load frequent senders from tracking data"""
        tracking_file = self.data_dir / "sender_tracking.json"
        if tracking_file.exists():
            try:
                with open(tracking_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load sender tracking: {e}")
        return {}

    def score_message(
        self,
        message_id: str,
        from_email: str,
        subject: str,
        body: str,
        category: str,
        confidence: float,
    ) -> Tuple[int, Dict[str, int], str]:
        """
        Calculate importance score for a message

        Args:
            message_id: Email message ID
            from_email: Sender email address
            subject: Email subject
            body: Email body
            category: Classification category (PRO, BANQUE, VENTE, etc.)
            confidence: Classification confidence (0-1)

        Returns:
            Tuple of (score, criteria_breakdown, action_type)
        """
        score = 0
        breakdown = {}

        # Category score
        if category in self.SCORES:
            cat_score = self.SCORES[category]
            score += cat_score
            breakdown[f"category_{category}"] = cat_score

        # Exclude SPAM
        if category == "SPAM":
            return 0, {"SPAM_excluded": -100}, "none"

        # Important contact bonus
        from_lower = from_email.lower()
        if any(contact in from_lower for contact in self.important_contacts):
            score += self.SCORES["important_contact"]
            breakdown["important_contact"] = self.SCORES["important_contact"]

        # Important domain bonus
        domain = from_lower.split("@")[-1] if "@" in from_lower else ""
        if domain in self.important_domains:
            domain_score = self.important_domains[domain]
            score += domain_score
            breakdown[f"domain_{domain}"] = domain_score

        # Urgent keywords
        text_to_search = f"{subject} {body}".lower()
        urgent_keywords = [
            "urgent",
            "important",
            "action required",
            "asap",
            "deadline",
        ]
        if any(kw in text_to_search for kw in urgent_keywords):
            score += self.SCORES["urgent_keywords"]
            breakdown["urgent_keywords"] = self.SCORES["urgent_keywords"]

        # Relocation keywords
        if any(kw in text_to_search for kw in self.relocation_keywords):
            score += self.SCORES["relocation_keyword"]
            breakdown["relocation_keyword"] = self.SCORES["relocation_keyword"]

        # Frequent sender
        sender_count = self.frequent_senders.get(from_lower, 0)
        if sender_count >= 3:
            score += self.SCORES["frequent_sender"]
            breakdown["frequent_sender"] = self.SCORES["frequent_sender"]

        # Determine action type
        action_type = self._determine_action_type(
            category, urgent_keywords, text_to_search
        )

        logger.debug(
            f"Scored message {message_id}: {score} pts "
            f"(category={category}, from={from_email})"
        )

        return score, breakdown, action_type

    def _determine_action_type(self, category: str, urgent_kw: List[str], text: str) -> str:
        """
        Determine the action type for the message
        """
        if category == "PRO":
            if any(kw in text for kw in urgent_kw):
                return "respond"
            return "review"
        elif category == "BANQUE":
            return "verify"
        elif category == "VENTE":
            return "track"
        else:
            return "none"

    def save_important_message(self, msg: ImportantMessage) -> None:
        """
        Save important message to tracking file
        """
        messages = self._load_important_messages()
        messages.append(msg)
        with open(self.important_messages_file, "w") as f:
            json.dump([m.to_dict() for m in messages], f, indent=2)

    def _load_important_messages(self) -> List[ImportantMessage]:
        """
        Load important messages from file
        """
        if self.important_messages_file.exists():
            try:
                with open(self.important_messages_file) as f:
                    data = json.load(f)
                    return [
                        ImportantMessage(
                            message_id=m["message_id"],
                            from_email=m["from_email"],
                            subject=m["subject"],
                            score=m["score"],
                            category=m["category"],
                            criteria_breakdown=m["criteria_breakdown"],
                            action_type=m["action_type"],
                            status=m["status"],
                            detected_at=m["detected_at"],
                            category_confidence=m["category_confidence"],
                        )
                        for m in data
                    ]
            except Exception as e:
                logger.error(f"Could not load important messages: {e}")
        return []

    def generate_executive_summary(
        self, messages: List[ImportantMessage]
    ) -> Dict[str, any]:
        """
        Generate an executive summary from important messages

        Args:
            messages: List of important messages

        Returns:
            Dictionary with summary structure
        """
        # Categorize by urgency
        urgent = [m for m in messages if m.score >= self.URGENT_THRESHOLD]
        high = [m for m in messages if self.HIGH_THRESHOLD <= m.score < self.URGENT_THRESHOLD]
        medium = [m for m in messages if self.IMPORTANCE_THRESHOLD <= m.score < self.HIGH_THRESHOLD]

        summary = {
            "timestamp": datetime.now().isoformat(),
            "urgent_count": len(urgent),
            "high_count": len(high),
            "medium_count": len(medium),
            "total_count": len(messages),
            "urgent": [self._format_message_for_summary(m) for m in urgent],
            "high": [self._format_message_for_summary(m) for m in high],
            "medium": [self._format_message_for_summary(m) for m in medium],
        }

        logger.info(
            f"Executive summary generated: "
            f"{len(urgent)} urgent, {len(high)} high, {len(medium)} medium"
        )
        return summary

    def _format_message_for_summary(self, msg: ImportantMessage) -> Dict[str, str]:
        """
        Format a message for display in summary
        """
        return {
            "id": msg.message_id,
            "from": msg.from_email,
            "subject": msg.subject[:60],
            "category": msg.category,
            "score": msg.score,
            "action": msg.action_type,
            "time": msg.detected_at,
        }
