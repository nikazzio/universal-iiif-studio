import warnings
import base64
import json
import time
from io import BytesIO
from typing import Any, Dict, List, Optional, Union, Protocol
from dataclasses import dataclass, asdict

import requests
from PIL import Image
from iiif_downloader.logger import get_logger

logger = get_logger(__name__)

# --- Kraken Setup ---
try:
    from kraken.lib import models
    from kraken import binarization, pageseg, rpred
    KRAKEN_AVAILABLE = True
    KRAKEN_IMPORT_ERROR = None
except (ImportError, AttributeError, RuntimeError) as e:
    KRAKEN_AVAILABLE = False
    KRAKEN_IMPORT_ERROR = str(e)

if KRAKEN_AVAILABLE:
    warnings.filterwarnings("ignore", message="Using legacy polygon extractor", category=UserWarning)

# --- Data Models ---
@dataclass
class OCRLine:
    text: str
    confidence: float = 1.0
    box: Optional[List[Any]] = None

@dataclass
class OCRResult:
    full_text: str
    lines: List[OCRLine]
    engine: str
    error: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        # Ensure boxes are serializable if needed, but here they usually are
        return d

# --- Provider Interfaces ---
class OCRProvider(Protocol):
    def process(self, image: Image.Image) -> OCRResult:
        ...

def _image_to_base64(image: Image.Image, quality: int = 95) -> str:
    """Helper to convert PIL Image to base64 JPEG string."""
    from io import BytesIO
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=quality, subsampling=0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# --- Providers Implementation ---

class KrakenProvider:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        if KRAKEN_AVAILABLE and model_path:
            try:
                self.model = models.load_any(model_path)
            except Exception as e:
                self.error = f"Errore caricamento modello: {e}"
        else:
            self.error = "Kraken non disponibile o modello non specificato"

    def process(self, image: Image.Image) -> OCRResult:
        logger.info("Starting Kraken OCR process")
        if not KRAKEN_AVAILABLE or not self.model:
            error_msg = getattr(self, "error", "Kraken non pronto")
            logger.error(f"Kraken failure: {error_msg}")
            return OCRResult("", [], "Kraken", error=error_msg)
        
        try:
            bw_im = binarization.nlbin(image)
            seg = pageseg.segment(bw_im)
            pred = rpred.rpred(self.model, bw_im, seg)
            
            lines = []
            full_text = []
            for record in pred:
                text = getattr(record, "prediction", None) or getattr(record, "pred", None) or ""
                text = str(text)
                full_text.append(text)
                
                conf = 0.0
                for attr in ("avg_confidence", "confidence", "conf"):
                    val = getattr(record, attr, None)
                    if isinstance(val, (int, float)):
                        conf = float(val)
                        break
                
                box = getattr(record, "bounds", None) or getattr(record, "box", None)
                lines.append(OCRLine(text, conf, box))
                
            return OCRResult("\n".join(full_text), lines, "Kraken")
        except Exception as e:
            return OCRResult("", [], "Kraken", error=str(e))

class GoogleVisionProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def process(self, image: Image.Image) -> OCRResult:
        logger.info("Starting Google Vision OCR process")
        if not self.api_key:
            logger.error("Google Vision API Key missing")
            return OCRResult("", [], "Google Vision", error="API Key mancante")
        
        try:
            img_str = _image_to_base64(image)
            
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"
            payload = {
                "requests": [{"image": {"content": img_str}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]}]
            }
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            res = data.get("responses", [{}])[0]
            if "error" in res:
                return OCRResult("", [], "Google Vision", error=res["error"].get("message"))
            
            full_text = res.get("fullTextAnnotation", {}).get("text", "")
            lines = []
            for page in res.get("fullTextAnnotation", {}).get("pages", []):
                for block in page.get("blocks", []):
                    for paragraph in block.get("paragraphs", []):
                        for word in paragraph.get("words", []):
                            text = "".join([s.get("text", "") for s in word.get("symbols", [])])
                            conf = word.get("confidence", 0.0)
                            box = word.get("boundingBox", {}).get("vertices", [])
                            lines.append(OCRLine(text, conf, box))
            
            return OCRResult(full_text, lines, "Google Vision")
        except Exception as e:
            return OCRResult("", [], "Google Vision", error=str(e))

class HFInferenceProvider:
    def __init__(self, token: str, model_id: str = "magistermilitum/tridis_v2_HTR_historical_manuscripts"):
        self.token = token
        self.model_id = model_id

    def process(self, image: Image.Image) -> OCRResult:
        logger.info(f"Starting Hugging Face OCR process using model: {self.model_id}")
        if not self.token:
            logger.error("Hugging Face Token missing")
            return OCRResult("", [], "Hugging Face", error="Token mancante")

        # Use Kraken for segmentation if available
        if not KRAKEN_AVAILABLE:
            res = self._query_api(image)
            if "error" in res: return OCRResult("", [], "Hugging Face", error=res["error"])
            return OCRResult(res["text"], [OCRLine(res["text"])], "Hugging Face")

        try:
            bw_im = binarization.nlbin(image)
            seg = pageseg.segment(bw_im)
            lines_obj = getattr(seg, "lines", [])
            
            full_text = []
            lines_data = []
            for i, line in enumerate(lines_obj[:100]): # Max 100 lines
                poly = getattr(line, "boundary", None) or getattr(line, "baseline", None)
                if not poly: continue
                
                x_coords = [p[0] for p in poly]; y_coords = [p[1] for p in poly]
                if not x_coords or not y_coords: continue
                left, top, right, bottom = min(x_coords), min(y_coords), max(x_coords), max(y_coords)
                
                # Ensure valid crop dimensions
                left, top = max(0, left), max(0, top)
                right, bottom = min(image.width, right), min(image.height, bottom)
                if right <= left or bottom <= top: continue
                
                line_crop = image.crop((left, top, right, bottom))
                
                res = self._query_api(line_crop)
                text = res.get("text", f"[Error: {res.get('error')}]")
                full_text.append(text)
                lines_data.append(OCRLine(text, 1.0, [left, top, right, bottom]))
            
            if not lines_data:
                # Fallback to whole image if no lines found
                res = self._query_api(image)
                if "error" in res: return OCRResult("", [], "Hugging Face", error=res["error"])
                return OCRResult(res["text"], [OCRLine(res["text"])], "Hugging Face")

            return OCRResult("\n".join(full_text), lines_data, f"Hugging Face ({self.model_id})")
        except Exception as e:
            return OCRResult("", [], "Hugging Face", error=str(e))

    def _query_api(self, image: Image.Image) -> Dict[str, str]:
        api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        img_data = _image_to_base64(image)
        # Hugging Face expected raw bytes in some versions, but let's keep it consistent
        # Wait, HF _query_api used raw bytes for 'data' parameter.
        buf = BytesIO(); image.save(buf, format="JPEG", quality=95, subsampling=0)
        raw_bytes = buf.getvalue()
        
        for _ in range(3):
            try:
                r = requests.post(api_url, headers=headers, data=raw_bytes, timeout=30)
                if r.status_code == 503: time.sleep(10); continue
                r.raise_for_status()
                res = r.json()
                text = res[0].get("generated_text", "") if isinstance(res, list) else res.get("generated_text", "")
                return {"text": text}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Timeout"}

class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-5"):
        self.api_key = api_key
        self.model = model

    def process(self, image: Image.Image) -> OCRResult:
        logger.info(f"Starting OpenAI OCR process using model: {self.model}")
        if not self.api_key:
            logger.error("OpenAI API Key missing")
            return OCRResult("", [], "OpenAI", error="API Key mancante")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            base64_image = _image_to_base64(image)
            
            prompt = "Trascrivi accuratamente il testo contenuto in questa immagine di un manoscritto latino. Mantieni l'ortografia originale, inclusi eventuali errori o abbreviazioni. Fornisci solo la trascrizione del testo, riga per riga, senza commenti."
            
            # 2026 Reasoning models (o-series) might need specific token limits
            is_reasoning = self.model.startswith("o")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url", 
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ],
                    }
                ],
                max_completion_tokens=4096 if is_reasoning else 16384,
            )
            
            text = response.choices[0].message.content
            # OpenAI vision doesn't give precise bounding boxes for each word easily in chat mode
            # We return it as a search-friendly result nonetheless
            lines = [OCRLine(l.strip()) for l in text.split("\n") if l.strip()]
            
            return OCRResult(text, lines, f"OpenAI ({self.model})")
        except Exception as e:
            return OCRResult("", [], "OpenAI", error=str(e))

class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-4-sonnet"):
        self.api_key = api_key
        self.model = model

    def process(self, image: Image.Image) -> OCRResult:
        logger.info(f"Starting Anthropic OCR process using model: {self.model}")
        if not self.api_key:
            logger.error("Anthropic API Key missing")
            return OCRResult("", [], "Anthropic", error="API Key mancante")
        
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key)
            
            img_data = _image_to_base64(image)
            
            prompt = "Sei un esperto paleografo. Trascrivi questo manoscritto latino con la massima precisione diplomatica. Rispetta ogni riga e carattere. Non aggiungere introduzioni o conclusioni, fornisci solo il testo."
            
            message = client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": img_data,
                                },
                            },
                            {"type": "text", "text": prompt}
                        ],
                    }
                ],
            )
            
            # Extract content correctly from the response
            # Anthropic response.content is a list of ContentBlock items
            text = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    text += block.text
            
            lines = [OCRLine(l.strip()) for l in text.split("\n") if l.strip()]
            return OCRResult(text, lines, f"Anthropic ({self.model})")
        except Exception as e:
            return OCRResult("", [], "Anthropic", error=str(e))

# --- Main Processor Proxy (Backward Compatibility) ---

class OCRProcessor:
    def __init__(self, model_path=None, google_api_key=None, hf_token=None, openai_api_key=None, anthropic_api_key=None):
        self.model_path = model_path
        self.google_api_key = google_api_key
        self.hf_token = hf_token
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        
        # Internal provider cache if needed, but usually we recreate based on task
        self._kraken = None

    def _get_kraken(self):
        if not self._kraken and self.model_path:
            self._kraken = KrakenProvider(self.model_path)
        return self._kraken

    def process_image(self, image_input: Union[str, Any, Image.Image]) -> Dict[str, Any]:
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im: return im
        prov = self._get_kraken()
        if not prov: return {"error": "Modello Kraken non caricato"}
        return prov.process(im).to_dict()

    def process_image_google_vision(self, image_input: Union[str, Any, Image.Image]) -> Dict[str, Any]:
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im: return im
        return GoogleVisionProvider(self.google_api_key).process(im).to_dict()

    def process_image_huggingface(self, image_input: Union[str, Any, Image.Image], model_id=None) -> Dict[str, Any]:
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im: return im
        model_id = model_id or "magistermilitum/tridis_v2_HTR_historical_manuscripts"
        return HFInferenceProvider(self.hf_token, model_id).process(im).to_dict()

    def process_image_openai(self, image_input: Union[str, Any, Image.Image], model="gpt-5") -> Dict[str, Any]:
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im: return im
        return OpenAIProvider(self.openai_api_key, model).process(im).to_dict()

    def process_image_anthropic(self, image_input: Union[str, Any, Image.Image], model="claude-4-sonnet") -> Dict[str, Any]:
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im: return im
        return AnthropicProvider(self.anthropic_api_key, model).process(im).to_dict()

    def process_page(self, image: Image.Image, engine: str = "kraken", model: Optional[str] = None) -> Dict[str, Any]:
        """Unified entry point for OCR."""
        if engine == "kraken":
            return self.process_image(image)
        elif engine == "google":
            return self.process_image_google_vision(image)
        elif engine == "openai":
            return self.process_image_openai(image, model=model or "gpt-5")
        elif engine == "anthropic":
            return self.process_image_anthropic(image, model=model or "claude-4-sonnet")
        elif engine == "huggingface":
            return self.process_image_huggingface(image, model_id=model)
        else:
            return {"error": f"Motore '{engine}' non supportato."}

    def _load_im(self, image_input):
        try:
            if isinstance(image_input, Image.Image): return image_input
            return Image.open(image_input)
        except Exception as e:
            return {"error": f"Errore caricamento immagine: {e}"}
