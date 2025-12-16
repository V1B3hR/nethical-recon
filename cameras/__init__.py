"""
Nethical Recon - Cameras Module (IR Night Vision)

The cameras module provides "Deep/Dark Discovery" capabilities,
seeing what normal sensors cannot detect:

🌙 Night Vision - Shodan/Censys (hidden services in the dark)
🌧️ Bad Weather - theHarvester (OSINT through the fog)
🔥 Thermal - Masscan (hot/active ports)
👻 Ghost - DNS enumeration (invisible subdomains)
🕳️ X-ray - SSL/TLS analysis (through encryption)
🎭 Mask - WAF detection (hidden defenses)
"""

from .base import BaseCamera, CameraMode, CameraStatus, CameraDiscovery
from .manager import CameraManager
from .shodan_eye import ShodanEye
from .censys_eye import CensysEye
from .harvester_eye import HarvesterEye
from .ssl_scanner import SSLScanner
from .dns_enum import DNSEnumerator
from .waf_detector import WAFDetector

__all__ = [
    "BaseCamera",
    "CameraMode",
    "CameraStatus",
    "CameraDiscovery",
    "CameraManager",
    "ShodanEye",
    "CensysEye",
    "HarvesterEye",
    "SSLScanner",
    "DNSEnumerator",
    "WAFDetector",
]
