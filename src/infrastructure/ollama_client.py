import requests
import json
from src.domain.interfaces import ILLMProvider
from src.domain.entities import AnalysisResult

class OllamaClient(ILLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llava"):
        self.base_url = base_url
        self.model = model
        self.prompt = (
            "Atue como um especialista em analise de dados, processamento de documentos complexos e visao computacional. "
            "Sua tarefa e analisar o documento ou imagem fornecido e retornar uma transcricao estruturada, combinando "
            "Reconhecimento Optico de Caracteres (OCR) e interpretacao semantica de elementos visuais.\n\n"
            "Instrucoes de processamento:\n"
            "Cadeia de Raciocinio (Chain-of-Thought): Primeiro, forneca uma visao geral de todo o documento e sua estrutura logica. "
            "Segundo, processe o texto legivel. Terceiro, descreva detalhadamente os elementos graficos e visuais.\n"
            "Transcricao de Texto (OCR): Extraia todo o texto legivel com precisao. Preserve a hierarquia estrutural original, indicando claramente onde estao os titulos, paragrafos e listas de dados.\n"
            "Localizacao Espacial: Descreva o layout geral e indique a posicao exata de elementos visuais cruciais no espaco do documento (exemplo: no quadrante superior esquerdo, no rodape).\n"
            "Interpretacao de Graficos e Diagramas: Para qualquer representacao grafica presente, identifique o tipo (barras, linhas, pizza, dispersao), extraia os rotulos dos eixos X e Y, transcreva as legendas e descreva as principais tendencias, picos ou dados numericos visiveis.\n"
            "Analise de Imagens e Fotografias: Descreva o conteudo visual de fotografias, selos ou logotipos com riqueza de detalhes contextuais e literais.\n"
            "Precisao e Mitigacao de Alucinacao: Baseie sua resposta estritamente no que e verificavel na imagem. Se um elemento estiver borrado, ilegivel ou parcialmente cortado, declare explicitamente a impossibilidade de processamento tecnico para aquele trecho especifico, sem tentar adivinhar dados ausentes."
        )

    def analyze_document(self, base64_images: list[str], trace_id: str, original_path: str, temperature: float = 0.0) -> AnalysisResult:
        try:
            # Reordenação e travamento de determinismo (temperature=0.0 por padrão)
            payload = {
                "model": self.model,
                "images": base64_images,
                "prompt": self.prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": 8192
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Idempotency-Key": trace_id  # Injetado no header
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload, 
                headers=headers,
                timeout=300
            )
            response.raise_for_status()
            
            data = response.json()
            return AnalysisResult(
                original_file_path=original_path,  # Populado atômicamente
                trace_id=trace_id,
                content=data.get("response", "")
            )
            
        except requests.exceptions.RequestException as e:
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                error_details = f" | Detalhes: {e.response.text}"
            return AnalysisResult(
                original_file_path=original_path,
                trace_id=trace_id,
                content="",
                error=f"Falha de comunicacao com o Ollama: {str(e)}{error_details}"
            )
        except Exception as e:
            return AnalysisResult(
                original_file_path=original_path,
                trace_id=trace_id,
                content="",
                error=f"Erro inesperado na IA: {str(e)}"
            )
