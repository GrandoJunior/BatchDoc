from dataclasses import dataclass
from typing import Optional

@dataclass
class TargetFile:
    path: str
    trace_id: str
    is_processed: bool = False
    
@dataclass
class AnalysisResult:
    original_file_path: str
    trace_id: str
    content: str
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.error is None
