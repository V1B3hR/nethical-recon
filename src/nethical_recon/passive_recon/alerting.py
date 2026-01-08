"""Alerting module for passive reconnaissance findings."""

import json
import requests
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""

    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"


@dataclass
class Alert:
    """Alert message."""

    title: str
    message: str
    severity: AlertSeverity
    metadata: Optional[dict[str, Any]] = None


class AlertManager:
    """Manages alerting for reconnaissance findings."""

    def __init__(self):
        self.channels = {}

    def add_webhook(self, name: str, url: str):
        """Add webhook alert channel.

        Args:
            name: Channel name
            url: Webhook URL
        """
        self.channels[name] = {"type": AlertChannel.WEBHOOK, "url": url}

    def add_slack(self, name: str, webhook_url: str):
        """Add Slack alert channel.

        Args:
            name: Channel name
            webhook_url: Slack webhook URL
        """
        self.channels[name] = {"type": AlertChannel.SLACK, "url": webhook_url}

    def add_discord(self, name: str, webhook_url: str):
        """Add Discord alert channel.

        Args:
            name: Channel name
            webhook_url: Discord webhook URL
        """
        self.channels[name] = {"type": AlertChannel.DISCORD, "url": webhook_url}

    def send_alert(self, alert: Alert, channel_name: Optional[str] = None):
        """Send alert to configured channels.

        Args:
            alert: Alert to send
            channel_name: Specific channel name, or None for all channels
        """
        channels_to_send = []
        if channel_name:
            if channel_name in self.channels:
                channels_to_send = [self.channels[channel_name]]
        else:
            channels_to_send = list(self.channels.values())

        for channel in channels_to_send:
            self._send_to_channel(alert, channel)

    def _send_to_channel(self, alert: Alert, channel: dict):
        """Send alert to a specific channel.

        Args:
            alert: Alert to send
            channel: Channel configuration
        """
        channel_type = channel["type"]
        url = channel["url"]

        try:
            if channel_type in [AlertChannel.WEBHOOK, AlertChannel.SLACK]:
                # Slack-compatible webhook format
                payload = {
                    "text": f"*{alert.title}*",
                    "attachments": [
                        {
                            "color": self._get_severity_color(alert.severity),
                            "text": alert.message,
                            "fields": [
                                {"title": "Severity", "value": alert.severity.value, "short": True},
                            ],
                        }
                    ],
                }
                if alert.metadata:
                    payload["attachments"][0]["fields"].append(
                        {"title": "Metadata", "value": json.dumps(alert.metadata, indent=2), "short": False}
                    )

                requests.post(url, json=payload, timeout=10)

            elif channel_type == AlertChannel.DISCORD:
                # Discord webhook format
                payload = {
                    "content": f"**{alert.title}**",
                    "embeds": [
                        {
                            "description": alert.message,
                            "color": self._get_severity_color_int(alert.severity),
                            "fields": [{"name": "Severity", "value": alert.severity.value, "inline": True}],
                        }
                    ],
                }
                if alert.metadata:
                    payload["embeds"][0]["fields"].append(
                        {"name": "Metadata", "value": json.dumps(alert.metadata, indent=2)[:1024], "inline": False}
                    )

                requests.post(url, json=payload, timeout=10)

        except Exception:
            # Silent failure for alerting
            pass

    def _get_severity_color(self, severity: AlertSeverity) -> str:
        """Get color for severity level (Slack format).

        Args:
            severity: Alert severity

        Returns:
            Color code
        """
        colors = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.LOW: "#2196F3",
            AlertSeverity.MEDIUM: "#FF9800",
            AlertSeverity.HIGH: "#FF5722",
            AlertSeverity.CRITICAL: "#F44336",
        }
        return colors.get(severity, "#808080")

    def _get_severity_color_int(self, severity: AlertSeverity) -> int:
        """Get color for severity level (Discord format).

        Args:
            severity: Alert severity

        Returns:
            Color integer
        """
        colors = {
            AlertSeverity.INFO: 3581519,  # Green
            AlertSeverity.LOW: 2196915,  # Blue
            AlertSeverity.MEDIUM: 16753920,  # Orange
            AlertSeverity.HIGH: 16729090,  # Red-orange
            AlertSeverity.CRITICAL: 16007990,  # Red
        }
        return colors.get(severity, 8421504)  # Gray
