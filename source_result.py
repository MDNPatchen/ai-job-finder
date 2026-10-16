"""List-compatible provider records with explicit coverage information."""
from datetime import datetime,timezone

class SourceRecords(list):
    def __init__(self,records=(),diagnostics=None):
        super().__init__(records)
        self.diagnostics={'fetched_at':datetime.now(timezone.utc).isoformat(),**(diagnostics or {})}
