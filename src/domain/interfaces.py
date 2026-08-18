from abc import ABC, abstractmethod
from typing import List
from .entities import TargetFile, AnalysisResult

class IFileSystem(ABC):
    @abstractmethod
    def list_files(self, target_dir: str) -> List[TargetFile]:
        """Lista os arquivos suportados no diretório."""
        pass
        
    @abstractmethod
    def check_if_processed(self, file_path: str, output_dir: str) -> bool:
        """Verifica se o arquivo já possui um .md gerado (idempotência)."""
        pass
        
    @abstractmethod
    def read_file_as_base64_list(self, file_path: str, dpi: int = 200) -> List[str]:
        """Lê a imagem ou PDF (convertendo páginas) e retorna lista de strings base64."""
        pass
        
    @abstractmethod
    def save_result(self, result: AnalysisResult, output_dir: str) -> str:
        """Salva o AnalysisResult em um arquivo .md e retorna o caminho."""
        pass

class ILLMProvider(ABC):
    @abstractmethod
    def analyze_document(self, base64_images: List[str], trace_id: str, original_path: str, temperature: float = 0.0) -> AnalysisResult:
        """Envia imagens para a IA e retorna o resultado estruturado, injetando trace_id e original_path."""
        pass
