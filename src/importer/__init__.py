"""
Importer Package Init
"""

try:
    from .eurojackpot_importer import EurojackpotImporter
except ImportError:
    try:
        from .opap_fetcher import OPAPFetcher as EurojackpotImporter
    except ImportError:
        EurojackpotImporter = None
