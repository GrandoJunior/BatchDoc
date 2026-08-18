import sys
import argparse
import logging
import pathlib

from src.infrastructure.filesystem import LocalFileSystem
from src.infrastructure.ollama_client import OllamaClient
from src.use_cases.document_processor import DocumentProcessor

def setup_logging(output_path: pathlib.Path = None):
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if output_path:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = output_path / f"batchdoc_execucao_{timestamp}.log"
        output_path.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(str(log_file), encoding='utf-8'))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=handlers,
        force=True
    )

def main():
    # Obrigatório: Configuração de stdout e stderr para evitar UnicodeEncodeError no Windows.
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    
    parser = argparse.ArgumentParser(description="Descritor IA de Documentos - Processamento em Lote com Ollama")
    parser.add_argument("target_dir", help="Caminho (local ou UNC) do diretorio contendo os documentos a serem processados")
    parser.add_argument("--output_dir", "-o", help="Caminho do diretorio de saida. Opcional, padrao e criar uma pasta 'output' dentro do diretorio alvo.", default=None)
    parser.add_argument("--model", "-m", help="Modelo do Ollama a ser utilizado. Padrao: llava", default="llava")
    
    args = parser.parse_args()
    
    try:
        # Resolver o caminho de saída
        target_path = pathlib.Path(args.target_dir).resolve()
        if args.output_dir:
            output_path = pathlib.Path(args.output_dir).resolve()
        else:
            output_path = target_path / "output_ai_reports"
            
        setup_logging(output_path)
        logger = logging.getLogger(__name__)
            
        # Injeção de dependências manual (Composition Root)
        fs = LocalFileSystem()
        llm = OllamaClient(model=args.model)
        processor = DocumentProcessor(file_system=fs, llm_provider=llm)
        
        # Execução
        processor.process_directory(
            target_dir=str(target_path),
            output_dir=str(output_path)
        )
        
    except Exception as e:
        logger.error(f"Erro critico na inicializacao: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
