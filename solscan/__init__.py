"""SolScan — static vulnerability scanner for Solana (Anchor) programs."""
from .scanner import scan_path, scan_source, clone_and_scan
from .report import ScanResult, Finding

__version__ = "0.1.0"
__all__ = ["scan_path", "scan_source", "clone_and_scan", "ScanResult", "Finding"]
