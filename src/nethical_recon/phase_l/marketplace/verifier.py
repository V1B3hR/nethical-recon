"""
Plugin Verifier
Security verification and validation for marketplace plugins
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class VerificationStatus(Enum):
    """Plugin verification status"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class SecurityCheck:
    """Security check result"""
    check_name: str
    passed: bool
    severity: str  # info, warning, error, critical
    message: str
    details: dict[str, Any]


@dataclass
class VerificationResult:
    """Plugin verification result"""
    plugin_id: UUID
    status: VerificationStatus
    checks: list[SecurityCheck]
    verified_at: datetime
    verifier: str
    notes: str


class PluginVerifier:
    """
    Plugin security verifier
    
    Features:
    - Static code analysis
    - Dependency scanning
    - Security checks
    - Best practices validation
    """
    
    def __init__(self):
        """Initialize plugin verifier"""
        self._verification_results: dict[UUID, VerificationResult] = {}
    
    def verify_plugin(
        self, plugin_id: UUID, plugin_code: str, dependencies: list[str]
    ) -> VerificationResult:
        """
        Verify a plugin for security and best practices
        
        Args:
            plugin_id: Plugin ID
            plugin_code: Plugin source code
            dependencies: List of dependencies
            
        Returns:
            Verification result
        """
        checks: list[SecurityCheck] = []
        
        # Run all security checks
        checks.extend(self._check_dangerous_imports(plugin_code))
        checks.extend(self._check_code_injection(plugin_code))
        checks.extend(self._check_file_operations(plugin_code))
        checks.extend(self._check_network_operations(plugin_code))
        checks.extend(self._check_dependencies(dependencies))
        checks.extend(self._check_best_practices(plugin_code))
        
        # Determine overall status
        critical_failures = [c for c in checks if not c.passed and c.severity == "critical"]
        errors = [c for c in checks if not c.passed and c.severity == "error"]
        warnings = [c for c in checks if not c.passed and c.severity == "warning"]
        
        if critical_failures:
            status = VerificationStatus.FAILED
        elif errors:
            status = VerificationStatus.NEEDS_REVIEW
        elif warnings:
            status = VerificationStatus.NEEDS_REVIEW
        else:
            status = VerificationStatus.PASSED
        
        result = VerificationResult(
            plugin_id=plugin_id,
            status=status,
            checks=checks,
            verified_at=datetime.now(),
            verifier="automated",
            notes=self._generate_notes(checks)
        )
        
        self._verification_results[plugin_id] = result
        return result
    
    def _check_dangerous_imports(self, code: str) -> list[SecurityCheck]:
        """Check for dangerous imports"""
        dangerous = {
            "os.system": "Execution of system commands",
            "subprocess": "Process execution",
            "eval": "Dynamic code evaluation",
            "exec": "Dynamic code execution",
            "__import__": "Dynamic module import",
            "compile": "Code compilation"
        }
        
        checks = []
        for pattern, description in dangerous.items():
            if pattern in code:
                checks.append(SecurityCheck(
                    check_name="dangerous_imports",
                    passed=False,
                    severity="critical",
                    message=f"Found dangerous pattern: {pattern}",
                    details={"pattern": pattern, "description": description}
                ))
        
        if not checks:
            checks.append(SecurityCheck(
                check_name="dangerous_imports",
                passed=True,
                severity="info",
                message="No dangerous imports found",
                details={}
            ))
        
        return checks
    
    def _check_code_injection(self, code: str) -> list[SecurityCheck]:
        """Check for code injection vulnerabilities"""
        injection_patterns = [
            ("eval(", "eval() function"),
            ("exec(", "exec() function"),
            ("compile(", "compile() function"),
        ]
        
        checks = []
        for pattern, description in injection_patterns:
            if pattern in code:
                checks.append(SecurityCheck(
                    check_name="code_injection",
                    passed=False,
                    severity="critical",
                    message=f"Potential code injection: {description}",
                    details={"pattern": pattern}
                ))
        
        if not checks:
            checks.append(SecurityCheck(
                check_name="code_injection",
                passed=True,
                severity="info",
                message="No code injection patterns found",
                details={}
            ))
        
        return checks
    
    def _check_file_operations(self, code: str) -> list[SecurityCheck]:
        """Check for unsafe file operations"""
        file_patterns = [
            ("open(", "File operations"),
            ("os.remove", "File deletion"),
            ("os.unlink", "File deletion"),
            ("shutil.rmtree", "Directory deletion"),
        ]
        
        checks = []
        for pattern, description in file_patterns:
            if pattern in code:
                checks.append(SecurityCheck(
                    check_name="file_operations",
                    passed=False,
                    severity="warning",
                    message=f"File operation detected: {description}",
                    details={"pattern": pattern}
                ))
        
        return checks
    
    def _check_network_operations(self, code: str) -> list[SecurityCheck]:
        """Check for network operations"""
        network_patterns = [
            ("socket.", "Raw socket operations"),
            ("urllib.request", "URL requests"),
            ("requests.", "HTTP requests"),
        ]
        
        checks = []
        for pattern, description in network_patterns:
            if pattern in code:
                checks.append(SecurityCheck(
                    check_name="network_operations",
                    passed=True,
                    severity="info",
                    message=f"Network operation: {description}",
                    details={"pattern": pattern}
                ))
        
        return checks
    
    def _check_dependencies(self, dependencies: list[str]) -> list[SecurityCheck]:
        """Check plugin dependencies"""
        checks = []
        
        # Check for known vulnerable packages (simplified)
        known_vulnerable = ["pickle", "yaml.load"]
        
        for dep in dependencies:
            if any(vuln in dep.lower() for vuln in known_vulnerable):
                checks.append(SecurityCheck(
                    check_name="dependencies",
                    passed=False,
                    severity="error",
                    message=f"Potentially vulnerable dependency: {dep}",
                    details={"dependency": dep}
                ))
        
        # Check dependency count
        if len(dependencies) > 20:
            checks.append(SecurityCheck(
                check_name="dependencies",
                passed=False,
                severity="warning",
                message=f"High number of dependencies ({len(dependencies)})",
                details={"count": len(dependencies)}
            ))
        
        if not checks:
            checks.append(SecurityCheck(
                check_name="dependencies",
                passed=True,
                severity="info",
                message=f"{len(dependencies)} dependencies checked",
                details={"count": len(dependencies)}
            ))
        
        return checks
    
    def _check_best_practices(self, code: str) -> list[SecurityCheck]:
        """Check for best practices"""
        checks = []
        
        # Check for documentation
        if '"""' not in code and "'''" not in code:
            checks.append(SecurityCheck(
                check_name="best_practices",
                passed=False,
                severity="warning",
                message="Missing documentation strings",
                details={}
            ))
        
        # Check for type hints
        if "def " in code and "->" not in code:
            checks.append(SecurityCheck(
                check_name="best_practices",
                passed=False,
                severity="info",
                message="Consider adding type hints",
                details={}
            ))
        
        # Check for error handling
        if "try:" not in code and "except" not in code:
            checks.append(SecurityCheck(
                check_name="best_practices",
                passed=False,
                severity="warning",
                message="Consider adding error handling",
                details={}
            ))
        
        return checks
    
    def _generate_notes(self, checks: list[SecurityCheck]) -> str:
        """Generate verification notes"""
        critical = [c for c in checks if not c.passed and c.severity == "critical"]
        errors = [c for c in checks if not c.passed and c.severity == "error"]
        warnings = [c for c in checks if not c.passed and c.severity == "warning"]
        
        notes = []
        
        if critical:
            notes.append(f"CRITICAL: {len(critical)} critical issues found")
        
        if errors:
            notes.append(f"ERROR: {len(errors)} errors found")
        
        if warnings:
            notes.append(f"WARNING: {len(warnings)} warnings found")
        
        if not (critical or errors or warnings):
            notes.append("All checks passed")
        
        return "; ".join(notes)
    
    def get_verification_result(self, plugin_id: UUID) -> VerificationResult | None:
        """Get verification result for a plugin"""
        return self._verification_results.get(plugin_id)
    
    def is_verified(self, plugin_id: UUID) -> bool:
        """Check if plugin is verified"""
        result = self._verification_results.get(plugin_id)
        return result.status == VerificationStatus.PASSED if result else False
