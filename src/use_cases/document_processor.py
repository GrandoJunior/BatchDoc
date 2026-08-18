import logging
import uuid
from typing import Optional
from src.domain.interfaces import IFileSystem, ILLMProvider
from src.domain.entities import AnalysisResult

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, file_system: IFileSystem, llm_provider: ILLMProvider):
        self._file_system = file_system
        self._llm_provider = llm_provider

    def _validate_semantic(self, content: str) -> bool:
        """Inspeciona o conteúdo retornado para interceptar recusas padronizadas da IA."""
        content_lower = content.lower()
        refusal_terms = [
            "desculpe", "nao posso", "não posso", "incapaz", "sorry", "cannot", "unable",
            "lamento", "nao consigo", "não consigo", "nao e possivel", "não é possível",
            "como um modelo de linguagem", "como uma inteligencia artificial",
            "como uma inteligência artificial", "as an ai", "i cannot"
        ]
        for term in refusal_terms:
            if term in content_lower:
                return False
        return True

    def process_directory(self, target_dir: str, output_dir: str) -> None:
        """
        Orquestra o processamento em lote.
        Aplica idempotência e isolamento de falhas.
        """
        logger.info(f"Iniciando varredura no diretorio: {target_dir}")
        logger.info(f"Diretorio de saida: {output_dir}")
        
        files = self._file_system.list_files(target_dir)
        if not files:
            logger.info("Nenhum arquivo compativel encontrado para processamento.")
            return

        for target_file in files:
            try:
                # 1. Geração precoce e centralizada de UUIDv4 conforme diretriz (Correção 4)
                trace_id = str(uuid.uuid4())
                target_file.trace_id = trace_id
                
                # 2. Checagem de Idempotência
                if self._file_system.check_if_processed(target_file.path, output_dir):
                    logger.info(f"[IGNORADO] Arquivo ja processado anteriormente: {target_file.path}")
                    continue
                
                logger.info(f"[PROCESSANDO] Arquivo: {target_file.path} | Trace-ID: {trace_id}")
                
                # Autoheal: Estratégias de Retentativa
                retry_strategies = [
                    {"dpi": 200, "chunk": 5, "temp": 0.0},
                    {"dpi": 200, "chunk": 3, "temp": 0.0},
                    {"dpi": 150, "chunk": 2, "temp": 0.0}
                ]
                
                final_result = None
                
                for attempt, strategy in enumerate(retry_strategies):
                    try:
                        logger.info(f"Tentativa {attempt+1}/{len(retry_strategies)} - DPI: {strategy['dpi']}, Lotes: {strategy['chunk']}, Temp: {strategy['temp']}")
                        
                        # 3. Leitura / Pré-processamento com DPI variavel
                        base64_images = self._file_system.read_file_as_base64_list(target_file.path, dpi=strategy["dpi"])
                        
                        # 4. Inferência LLM com particionamento dinamico
                        max_images = strategy["chunk"]
                        full_content = ""
                        semantic_failure = False
                        
                        if len(base64_images) > max_images:
                            for i in range(0, len(base64_images), max_images):
                                chunk = base64_images[i:i + max_images]
                                lote_num = i // max_images + 1
                                logger.info(f"Processando lote {lote_num}...")
                                
                                res = self._llm_provider.analyze_document(chunk, trace_id, target_file.path, temperature=strategy["temp"])
                                if not res.is_success:
                                    logger.error(f"Falha técnica no lote {lote_num}: {res.error}")
                                    full_content += f"\n\n[FALHA TÉCNICA NO LOTE {lote_num}]\n{res.error}"
                                    semantic_failure = True
                                    break
                                
                                # Sanity Check Semântico do lote
                                if not self._validate_semantic(res.content):
                                    logger.warning(f"Recusa semântica interceptada no lote {lote_num}.")
                                    semantic_failure = True
                                    break
                                
                                full_content += f"\n\n## Parte {lote_num}\n" + res.content
                                
                            result = AnalysisResult(
                                original_file_path=target_file.path,
                                trace_id=trace_id,
                                content=full_content
                            )
                        else:
                            result = self._llm_provider.analyze_document(
                                base64_images, trace_id, target_file.path, temperature=strategy["temp"]
                            )
                            if result.is_success and not self._validate_semantic(result.content):
                                logger.warning(f"Recusa semântica interceptada na inferência única.")
                                semantic_failure = True
                                
                        if semantic_failure:
                            logger.warning("Falha semântica detectada. Descartando resultado desta tentativa.")
                            continue # Avança para a próxima estratégia de retry
                            
                        # Se passou por tudo sem semantic_failure, é sucesso total!
                        final_result = result
                        break # Sai do loop de retry
                        
                    except Exception as loop_e:
                        logger.error(f"Erro durante a tentativa {attempt+1}: {str(loop_e)}")
                        continue
                        
                # 5. Salvar Resultado ou Quarentena
                if final_result and final_result.is_success:
                    saved_path = self._file_system.save_result(final_result, output_dir)
                    logger.info(f"[SUCESSO] Relatorio gerado: {saved_path}")
                else:
                    # Falha após esgotar todas as tentativas (Quarentena)
                    logger.error(f"[QUARENTENA] {target_file.path} falhou repetidamente. Isolado na origem, nenhum .md foi gerado.")
                
            except Exception as e:
                # Isolamento de falha robusto: não quebra o loop inteiro
                logger.error(f"[FALHA SISTEMICA] Erro ao processar {target_file.path}: {str(e)}")
        
        logger.info("Varredura concluida.")
