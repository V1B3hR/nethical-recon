"""
Risk Scoring System

Provides risk scoring and assessment for hosts, assets, and indicators
based on multiple factors including threat intelligence, vulnerabilities,
and configuration.
"""

import logging
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskFactor:
    """Represents a risk factor contributing to overall risk score."""

    name: str
    category: str  # threat_intel, vulnerability, configuration, exposure
    score: float  # 0-100
    weight: float = 1.0
    description: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class RiskScore:
    """Comprehensive risk score for an asset."""

    asset_id: str
    asset_type: str
    overall_score: float  # 0-100
    risk_level: str  # low, medium, high, critical
    factors: list[RiskFactor] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RiskScorer:
    """
    Risk Scorer

    Calculates risk scores for assets based on multiple factors:
    - Threat intelligence data
    - Vulnerability presence
    - Configuration issues
    - Exposure level
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def score_asset(self, asset: dict[str, Any], enrichment_data: dict[str, Any] | None = None) -> RiskScore:
        """
        Calculate risk score for an asset.

        Args:
            asset: Asset data
            enrichment_data: Optional threat intelligence enrichment data

        Returns:
            Risk score
        """
        asset_id = asset.get("asset_id", "unknown")
        asset_type = asset.get("asset_type", "unknown")

        self.logger.info(f"Calculating risk score for asset {asset_id}")

        factors = []

        # Threat intelligence factor
        if enrichment_data:
            ti_factor = self._score_threat_intelligence(enrichment_data)
            if ti_factor:
                factors.append(ti_factor)

        # Exposure factor
        exposure_factor = self._score_exposure(asset)
        if exposure_factor:
            factors.append(exposure_factor)

        # Configuration factor
        config_factor = self._score_configuration(asset)
        if config_factor:
            factors.append(config_factor)

        # Calculate overall score (weighted average)
        overall_score = self._calculate_overall_score(factors)
        risk_level = self._determine_risk_level(overall_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(factors, asset)

        return RiskScore(
            asset_id=asset_id,
            asset_type=asset_type,
            overall_score=overall_score,
            risk_level=risk_level,
            factors=factors,
            recommendations=recommendations,
            metadata={
                "total_factors": len(factors),
                "weighted_factors": sum(f.weight for f in factors),
            },
        )

    def _score_threat_intelligence(self, enrichment_data: dict[str, Any]) -> RiskFactor | None:
        """Score based on threat intelligence data."""
        threat_level = enrichment_data.get("aggregated_threat_level", "unknown")
        confidence = enrichment_data.get("aggregated_confidence", 0.0)

        threat_scores = {
            "critical": 90,
            "high": 70,
            "medium": 40,
            "low": 20,
            "unknown": 0,
        }

        base_score = threat_scores.get(threat_level, 0)
        adjusted_score = base_score * confidence

        if adjusted_score > 0:
            return RiskFactor(
                name="Threat Intelligence",
                category="threat_intel",
                score=adjusted_score,
                weight=2.0,  # High weight for threat intel
                description=f"Threat level: {threat_level} (confidence: {confidence:.2f})",
                evidence=enrichment_data.get("sources", []),
            )

        return None

    def _score_exposure(self, asset: dict[str, Any]) -> RiskFactor | None:
        """Score based on exposure level."""
        # Check if asset has public-facing services
        port = asset.get("port")
        services = asset.get("services", [])

        score = 0.0
        evidence = []

        # High-risk ports
        high_risk_ports = [21, 23, 3389, 445, 1433, 3306, 5432, 27017]
        if port in high_risk_ports:
            score += 40
            evidence.append(f"High-risk port {port} exposed")

        # Internet-facing services
        if services:
            score += 20
            evidence.append(f"{len(services)} service(s) exposed")

        if score > 0:
            return RiskFactor(
                name="Exposure",
                category="exposure",
                score=score,
                weight=1.5,
                description="Asset exposure to internet/network",
                evidence=evidence,
            )

        return None

    def _score_configuration(self, asset: dict[str, Any]) -> RiskFactor | None:
        """Score based on configuration issues."""
        technologies = asset.get("technologies", [])

        score = 0.0
        evidence = []

        # Check for outdated or risky technologies
        for tech in technologies:
            tech_name = tech.get("name", "").lower()
            version = tech.get("version")

            # Example checks (would be expanded with real version checking)
            if not version:
                score += 10
                evidence.append(f"Unversioned technology: {tech_name}")

        if score > 0:
            return RiskFactor(
                name="Configuration",
                category="configuration",
                score=score,
                weight=1.0,
                description="Configuration and technology risks",
                evidence=evidence,
            )

        return None

    def _calculate_overall_score(self, factors: list[RiskFactor]) -> float:
        """Calculate weighted overall score."""
        if not factors:
            return 0.0

        weighted_sum = sum(f.score * f.weight for f in factors)
        total_weight = sum(f.weight for f in factors)

        return min(100.0, weighted_sum / total_weight)

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score."""
        if score >= 75:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 25:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(self, factors: list[RiskFactor], asset: dict[str, Any]) -> list[str]:
        """Generate remediation recommendations based on risk factors."""
        recommendations = []

        for factor in factors:
            if factor.category == "threat_intel" and factor.score > 50:
                recommendations.append("Investigate threat intelligence alerts and consider blocking/isolating asset")

            if factor.category == "exposure" and factor.score > 30:
                recommendations.append("Reduce attack surface by closing unnecessary ports and services")

            if factor.category == "configuration" and factor.score > 20:
                recommendations.append("Review and harden configuration, update software versions")

        if not recommendations:
            recommendations.append("Continue monitoring asset for changes")

        return recommendations
