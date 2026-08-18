import base64
import uuid
import pathlib
import hashlib
import fitz  # PyMuPDF
from typing import List

from src.domain.interfaces import IFileSystem
from src.domain.entities import TargetFile, AnalysisResult

class LocalFileSystem(IFileSystem):
    def __init__(self):
        # Extensões suportadas por modelos de visão padrão
        self.supported_extensions = {'.png', '.jpg', '.jpeg', '.pdf'}

    def _extend_path(self, p: pathlib.Path) -> pathlib.Path:
        """Aplica prefixo estendido para contornar MAX_PATH no Windows."""
        abs_path = str(p.resolve())
        if not abs_path.startswith("\\\\?\\"):
            if abs_path.startswith("\\\\"):
                # Caminho UNC (\\server\share) -> \\?\UNC\server\share
                abs_path = "\\\\?\\UNC\\" + abs_path[2:]
            else:
                # Caminho local (C:\pasta) -> \\?\C:\pasta
                abs_path = "\\\\?\\" + abs_path
        return pathlib.Path(abs_path)

    def list_files(self, target_dir: str) -> List[TargetFile]:
        # Suporte dinâmico e resiliente a caminhos, incluindo UNC bypass (MAX_PATH)
        directory = self._extend_path(pathlib.Path(target_dir))
        
        if not directory.exists() or not directory.is_dir():
            raise FileNotFoundError(f"O diretorio especificado nao existe ou e invalido: {directory}")

        files = []
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                files.append(TargetFile(
                    path=str(file_path),
                    trace_id=""  # Correção 4: Decoupled, UUIDv4 será gerado pelo UseCase
                ))
                
        return files

    def _generate_report_filename(self, original_file_path: str) -> str:
        """Gera um nome de arquivo consistente baseado no caminho original para facilitar idempotência."""
        # Usa um hash do caminho completo para garantir unicidade, ou o próprio nome do arquivo.
        # Preferimos combinar o nome original + hash do caminho original.
        path_obj = pathlib.Path(original_file_path)
        base_name = path_obj.stem
        
        # Gerar hash do path para evitar colisão se processar arquivos com mesmo nome em subpastas
        path_hash = hashlib.md5(str(path_obj.resolve()).encode('utf-8')).hexdigest()[:8]
        
        return f"{base_name}_{path_hash}_report.md"

    def check_if_processed(self, file_path: str, output_dir: str) -> bool:
        """Idempotência estrita: verifica se o .md já existe no output_dir."""
        out_dir_path = self._extend_path(pathlib.Path(output_dir))
        expected_filename = self._generate_report_filename(file_path)
        
        # Correção 3: Concatenação segura de string literal
        safe_absolute_path = str(out_dir_path) + "\\" + expected_filename
        expected_filepath = pathlib.Path(safe_absolute_path)
        
        return expected_filepath.exists()

    def read_file_as_base64_list(self, file_path: str, dpi: int = 200) -> List[str]:
        """Lê a imagem ou PDF (convertendo páginas) e retorna lista de strings base64."""
        path_obj = self._extend_path(pathlib.Path(file_path))
        
        if path_obj.suffix.lower() == '.pdf':
            base64_images = []
            try:
                # Correção 1: Context Manager nativo PyMuPDF e deleção do buffer pixelado
                with fitz.open(str(path_obj)) as doc:
                    for page in doc:
                        pix = page.get_pixmap(dpi=dpi)
                        # Autoheal: JPEG reduz drasticamente o payload HTTP (evitando 413)
                        img_data = pix.tobytes("jpeg")
                        base64_images.append(base64.b64encode(img_data).decode('utf-8'))
                        del pix
                return base64_images
            except Exception as e:
                raise RuntimeError(f"Falha ao rasterizar PDF {file_path}: {str(e)}")
                
        # Imagem normal
        with open(path_obj, "rb") as f:
            return [base64.b64encode(f.read()).decode('utf-8')]

    def save_result(self, result: AnalysisResult, output_dir: str) -> str:
        out_dir_path = self._extend_path(pathlib.Path(output_dir))
        out_dir_path.mkdir(parents=True, exist_ok=True)
        
        filename = self._generate_report_filename(result.original_file_path)
        file_path = out_dir_path / filename
        
        # Formatando o resultado MD
        report_content = f"# Relatorio de Processamento IA\n\n"
        report_content += f"**Arquivo Original**: `{result.original_file_path}`\n"
        report_content += f"**Rastreabilidade (UUID)**: `{result.trace_id}`\n\n"
        report_content += f"## Transcricao e Analise\n\n"
        report_content += result.content
        
        # Gravando usando utf-8 explicitly to comply with the global rule
        file_path.write_text(report_content, encoding='utf-8')
        
        return str(file_path)
