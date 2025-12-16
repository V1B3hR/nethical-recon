"""
🦅 Sky Module - Eye in the Sky Surveillance System

> "Sokolim okiem widzę wszystko - każde drzewo, każdą gałąź, każdego kruka czyhającego w koronie"
> "With falcon eyes I see everything - every tree, every branch, every crow lurking in the canopy"

This module provides bird-based surveillance and monitoring for the forest infrastructure.
Each bird has unique capabilities for different aspects of threat detection and monitoring.
"""

from .base_bird import (
    BaseBird,
    BirdType,
    FlightMode,
    AlertLevel,
    BirdAlert
)

from .eagle import Eagle
from .falcon import Falcon
from .owl import Owl
from .sparrow import Sparrow
from .flight_controller import FlightController
from .bird_song import BirdSong, format_colored_alert, visualize_sound

__all__ = [
    # Base classes
    'BaseBird',
    'BirdType',
    'FlightMode',
    'AlertLevel',
    'BirdAlert',
    
    # Bird implementations
    'Eagle',
    'Falcon',
    'Owl',
    'Sparrow',
    
    # Coordination
    'FlightController',
    
    # Alert system
    'BirdSong',
    'format_colored_alert',
    'visualize_sound',
]

__version__ = '1.0.0'
__author__ = 'Nethical Recon Team'
__description__ = 'Eye in the Sky - Bird-based surveillance system'

# Quick start helper
def create_sky_surveillance():
    """
    Create and deploy standard sky surveillance fleet
    
    Returns:
        FlightController with standard fleet deployed and activated
    
    Example:
        >>> from forest.sky import create_sky_surveillance
        >>> sky = create_sky_surveillance()
        >>> results = sky.scan_forest(forest_data)
    """
    controller = FlightController()
    controller.deploy_standard_fleet()
    controller.activate_all()
    return controller
