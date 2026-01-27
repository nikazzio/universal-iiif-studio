import base64
import time
import warnings
from collections.abc import Callable
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any, Protocol

import requests
from PIL import Image

from iiif_downloader.logger import get_logger, summarize_for_debug

logger = get_logger(__name__)

# pylint: disable=broad-exception-caught

# --- Kraken Setup ---
KRAKEN_AVAILABLE = False
KRAKEN_IMPORT_ERROR = "Kraken disabled in config"
KRAKEN_IMPORTED = False
binarization = None
pageseg = None
rpred = None
models = None


def _kraken_enabled() -> bool:
    try:
        from iiif_downloader.config_manager import get_config_manager

        return bool(get_config_manager().get_setting("ocr.kraken_enabled", False))
    except Exception:
        return False


def _ensure_kraken_imported() -> None:
    global KRAKEN_AVAILABLE, KRAKEN_IMPORT_ERROR, KRAKEN_IMPORTED
    if KRAKEN_IMPORTED:
        return
    KRAKEN_IMPORTED = True

    if not _kraken_enabled():
        KRAKEN_AVAILABLE = False
        KRAKEN_IMPORT_ERROR = "Kraken disabled in config"
        return

    try:
        from kraken import binarization, pageseg, rpred
        from kraken.lib import models

        globals()["binarization"] = binarization
        globals()["pageseg"] = pageseg
        globals()["rpred"] = rpred
        globals()["models"] = models
        KRAKEN_AVAILABLE = True
        warnings.filterwarnings("ignore", message="Using legacy polygon extractor", category=UserWarning)
    except (ImportError, AttributeError, RuntimeError) as e:
        KRAKEN_AVAILABLE = False
        KRAKEN_IMPORT_ERROR = str(e)

# --- Data Models ---


@dataclass
class OCRLine:
    """Represents a single OCR line along with confidence metadata."""

    text: str
    confidence: float = 1.0
    box: list[Any] | None = None


@dataclass
class OCRResult:
    """Captures the overall OCR output and associated metadata."""
    full_text: str
    lines: list[OCRLine]
    engine: str
    error: str | None = None

    def to_dict(self):
        """Return a serializable representation of the OCR result."""
        d = asdict(self)
        return d


# --- Provider Interfaces ---


class OCRProvider(Protocol):
    """Protocol for OCR provider implementations."""

    def process(self, image: Image.Image, status_callback: Callable[[str], None] | None = None) -> OCRResult:
        """Process an image and return OCR metadata."""
        ...


def _image_to_base64(image: Image.Image, quality: int = 95) -> str:
    """Helper to convert PIL Image to base64 JPEG string."""
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=quality, subsampling=0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _extract_line_box(line: Any, image: Image.Image) -> list[int] | None:
    poly = getattr(line, "boundary", None) or getattr(line, "baseline", None)
    if not poly:
        return None
    x_coords = [p[0] for p in poly]
    y_coords = [p[1] for p in poly]
    if not x_coords or not y_coords:
        return None
    left, top, right, bottom = min(x_coords), min(y_coords), max(x_coords), max(y_coords)
    left, top = max(0, left), max(0, top)
    right, bottom = min(image.width, right), min(image.height, bottom)
    if right <= left or bottom <= top:
        return None
    return [left, top, right, bottom]


# --- Providers Implementation ---


class KrakenProvider:
    """Wrapper around Kraken HTR models."""

    def __init__(self, model_path: str):
        """Prepare Kraken by loading the requested model."""
        self.model_path = model_path
        self.model = None
        _ensure_kraken_imported()
        if KRAKEN_AVAILABLE and model_path:
            try:
                self.model = models.load_any(model_path)
            except Exception as e:
                self.error = f"Errore caricamento modello: {e}"
        else:
            self.error = KRAKEN_IMPORT_ERROR or "Kraken non disponibile o modello non specificato"

    def process(self, image: Image.Image, status_callback: Callable[[str], None] | None = None) -> OCRResult:
        """Execute Kraken OCR on the supplied image."""
        logger.info("Starting Kraken OCR process")
        if status_callback:
            status_callback("Inizializzazione Kraken...")
        if not KRAKEN_AVAILABLE or not self.model:
            error_msg = getattr(self, "error", "Kraken non pronto")
            logger.error("Kraken failure: %s", error_msg)
            return OCRResult("", [], "Kraken", error=error_msg)

        try:
            if status_callback:
                status_callback("Binarizzazione immagine...")
            bw_im = binarization.nlbin(image)
            if status_callback:
                status_callback("Segmentazione pagine...")
            seg = pageseg.segment(bw_im)
            if status_callback:
                status_callback("Riconoscimento caratteri (HTR)...")
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
    """Provider that delegates OCR to Google Cloud Vision."""

    def __init__(self, api_key: str):
        """Store the API key used for Vision requests."""
        self.api_key = api_key

    def process(self, image: Image.Image, status_callback: Callable[[str], None] | None = None) -> OCRResult:
        """Send the image to Google Vision for OCR."""
        logger.info("Starting Google Vision OCR process")
        if status_callback:
            status_callback("Preparazione immagine per Google Vision...")
        if not self.api_key:
            logger.error("Google Vision API Key missing")
            return OCRResult("", [], "Google Vision", error="API Key mancante")

        try:
            img_str = _image_to_base64(image)

            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"
            payload = {"requests": [{"image": {"content": img_str}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]}]}
            if status_callback:
                status_callback("Chiamata alle API di Google Vision...")
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
    """OCR provider backed by Hugging Face Inference API."""

    def __init__(self, token: str, model_id: str = "magistermilitum/tridis_v2_HTR_historical_manuscripts"):
        """Initialize the provider with credentials and model_id."""
        self.token = token
        self.model_id = model_id

    def process(self, image: Image.Image, status_callback: Callable[[str], None] | None = None) -> OCRResult:
        """Submit the image to Hugging Face for OCR."""
        logger.info("Starting Hugging Face OCR process using model: %s", self.model_id)
        if status_callback:
            status_callback(f"Preparazione Hugging Face ({self.model_id})...")
        if not self.token:
            logger.error("Hugging Face Token missing")
            return OCRResult("", [], "Hugging Face", error="Token mancante")

        _ensure_kraken_imported()
        if not KRAKEN_AVAILABLE:
            return self._process_whole_image(image)

        try:
            lines_data, full_text = self._process_with_kraken_lines(image)
        except Exception as e:
            return OCRResult("", [], "Hugging Face", error=str(e))

        if not lines_data:
            return self._process_whole_image(image)

        return OCRResult("\n".join(full_text), lines_data, f"Hugging Face ({self.model_id})")

    def _process_whole_image(self, image: Image.Image) -> OCRResult:
        res = self._query_api(image)
        if "error" in res:
            return OCRResult("", [], "Hugging Face", error=res["error"])
        return OCRResult(res["text"], [OCRLine(res["text"])], "Hugging Face")

    def _process_with_kraken_lines(self, image: Image.Image) -> tuple[list[OCRLine], list[str]]:
        bw_im = binarization.nlbin(image)
        seg = pageseg.segment(bw_im)
        lines_obj = getattr(seg, "lines", [])

        full_text: list[str] = []
        lines_data: list[OCRLine] = []
        for line in lines_obj[:100]:  # Max 100 lines
            box = _extract_line_box(line, image)
            if not box:
                continue
            left, top, right, bottom = box
            line_crop = image.crop((left, top, right, bottom))
            res = self._query_api(line_crop)
            text = res.get("text", f"[Error: {res.get('error')}]")
            full_text.append(text)
            lines_data.append(OCRLine(text, 1.0, [left, top, right, bottom]))

        return lines_data, full_text

    def _query_api(self, image: Image.Image) -> dict[str, str]:
        api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        # Hugging Face expects raw bytes for the `data` parameter.
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=95, subsampling=0)
        raw_bytes = buf.getvalue()

        for _ in range(3):
            try:
                r = requests.post(api_url, headers=headers, data=raw_bytes, timeout=30)
                if r.status_code == 503:
                    time.sleep(10)
                    continue
                r.raise_for_status()
                res = r.json()
                text = res[0].get("generated_text", "") if isinstance(res, list) else res.get("generated_text", "")
                return {"text": text}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Timeout"}


class OpenAIProvider:
    """OpenAI-based OCR assistant encouraging precise transcription."""

    def __init__(self, api_key: str, model: str = "o3-mini"):
        """Store transfer credentials and preferred model."""
        self.api_key = api_key
        self.model = model

    def process(self, image: Image.Image, status_callback: Callable[[str], None] | None = None) -> OCRResult:
        """Send the image to OpenAI for transcription."""
        logger.info("Starting OpenAI OCR process using model: %s", self.model)
        if status_callback:
            status_callback(f"Conversione immagine per OpenAI ({self.model})...")

        if not self.api_key:
            logger.error("OpenAI API Key missing")
            return OCRResult("", [], "OpenAI", error="API Key mancante")

        try:
            w, h = image.size
            logger.info("Processing image for OpenAI: %sx%s, mode=%s", w, h, image.mode)
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            base64_image = _image_to_base64(image)
            # Estimate size in MB
            img_size_mb = (len(base64_image) * 3 / 4) / (1024 * 1024)
            logger.info("Image converted to Base64 (%.2f MB)", img_size_mb)

            prompt = (
                "Trascrivi accuratamente il testo contenuto in questa immagine di un manoscritto latino. "
                "Mantieni l'ortografia originale, inclusi eventuali errori o abbreviazioni. "
                "Fornisci solo la trascrizione del testo, riga per riga, senza commenti."
            )
            logger.debug("Prompt: %s", prompt)

            # 2026 Reasoning models (o-series) might need specific token limits
            is_reasoning = self.model.startswith("o")

            if status_callback:
                status_callback(f"Richiesta API OpenAI ({self.model}) in corso...")
            logger.info("Calling OpenAI chat.completions.create with model=%s", self.model)

            start_time = time.time()
            # 2026 Reasoning/Frontier models use the 'developer' role for instructions
            use_developer_role = self.model.startswith("o") or "gpt-5" in self.model

            # 2026: Official guidance: Instructions in developer role, Data in user role
            messages = []
            if use_developer_role:
                messages.append({"role": "developer", "content": prompt})
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"},
                        },
                    ],
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"},
                        },
                    ],
                })

            # 2026: Explicit timeouts to prevent hanging calls
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=4096 if is_reasoning else 16384,
                timeout=60.0,
            )
            elapsed = time.time() - start_time
            logger.info("OpenAI API response received in %.2fs", elapsed)

            text = response.choices[0].message.content
            logger.debug("Raw OpenAI Response Content: %s", summarize_for_debug(text))

            if status_callback:
                status_callback("Elaborazione risposta OpenAI...")
            lines = [OCRLine(line_text.strip()) for line_text in text.split("\n") if line_text.strip()]

            return OCRResult(text, lines, f"OpenAI ({self.model})")
        except Exception as e:
            logger.exception("OpenAI OCR Error: %s", e)
            return OCRResult("", [], "OpenAI", error=str(e))


class AnthropicProvider:
    """Anthropic-powered OCR layer using Claude models."""

    def __init__(self, api_key: str, model: str = "claude-4-sonnet"):
        """Store credentials and model name."""
        self.api_key = api_key
        self.model = model

    def process(self, image: Image.Image, status_callback: Callable[[str], None] | None = None) -> OCRResult:
        """Ask Anthropic to transcribe the provided manuscript image."""
        logger.info("Starting Anthropic OCR process using model: %s", self.model)
        if status_callback:
            status_callback(f"Chiamata API Anthropic ({self.model})...")
        if not self.api_key:
            logger.error("Anthropic API Key missing")
            return OCRResult("", [], "Anthropic", error="API Key mancante")

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)

            img_data = _image_to_base64(image)

            prompt = (
                "Sei un esperto paleografo. Trascrivi questo manoscritto latino con la massima precisione diplomatica. "
                "Rispetta ogni riga e carattere. Non aggiungere introduzioni o conclusioni, fornisci solo il testo."
            )

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
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                timeout=60.0,
            )

            # Extract content correctly from the response
            # Anthropic response.content is a list of ContentBlock items
            text = ""
            for block in message.content:
                if hasattr(block, "text"):
                    text += block.text

            logger.debug("Raw Anthropic Response Content: %s", summarize_for_debug(text))

            lines = [OCRLine(line_text.strip()) for line_text in text.split("\n") if line_text.strip()]

            return OCRResult(text, lines, f"Anthropic ({self.model})")
        except Exception as e:
            return OCRResult("", [], "Anthropic", error=str(e))


# --- Main Processor Proxy (Backward Compatibility) ---


class OCRProcessor:
    """Facade that exposes OCR entry points across multiple providers."""

    def __init__(
        self, model_path=None, google_api_key=None, hf_token=None, openai_api_key=None, anthropic_api_key=None
    ):
        """Capture credentials and provider hooks."""
        self.model_path = model_path
        self.google_api_key = google_api_key
        self.hf_token = hf_token
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key

        # Internal provider cache
        self._kraken = None

    @staticmethod
    def get_available_models(engine: str) -> list[tuple[str, str]]:
        """Return a list of (label, value) for the given OCR engine."""
        engine_models = {
            "openai": [
                ("OpenAI GPT-5.2 (Flagship)", "gpt-5.2"),
                ("OpenAI GPT-5.2 Pro", "gpt-5.2-pro"),
                ("OpenAI GPT-5 Mini", "gpt-5-mini"),
                ("OpenAI o3-mini (Reasoning)", "o3-mini"),
            ],
            "anthropic": [
                ("Claude 4.5 Opus", "claude-4.5-opus"),
                ("Claude 4.5 Sonnet", "claude-4.5-sonnet"),
                ("Claude 4.5 Haiku", "claude-4.5-haiku"),
            ],
            "google": [
                ("Google Vision (Production)", "google-vision"),
            ],
            "gemini": [
                ("Gemini 3 Pro", "gemini-3-pro"),
                ("Gemini 3 Flash", "gemini-3-flash"),
            ],
            "huggingface": [
                ("Historical HTR (Tridis v2)", "magistermilitum/tridis_v2_HTR_historical_manuscripts"),
            ],
            "tesseract": [
                ("Tesseract (Auto)", "auto"),
            ],
            "kraken": [
                ("Kraken (Default)", "default"),
            ],
        }
        return engine_models.get(engine, [])

    def is_provider_ready(self, engine: str) -> bool:
        """Check if the required API key for the engine is presence."""
        if engine == "openai":
            return bool(self.openai_api_key)
        elif engine == "anthropic":
            return bool(self.anthropic_api_key)
        elif engine == "google":
            return bool(self.google_api_key)
        elif engine == "huggingface":
            return bool(self.hf_token)
        elif engine == "kraken":
            return True
        return False

    def _get_kraken(self):
        """Lazy-load or return the cached Kraken provider."""
        _ensure_kraken_imported()
        if not KRAKEN_AVAILABLE:
            return None
        if not self._kraken and self.model_path:
            self._kraken = KrakenProvider(self.model_path)
        return self._kraken

    def process_image(self, image_input: str | Any | Image.Image, status_callback=None) -> dict[str, Any]:
        """Run Kraken OCR on the provided input."""
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im:
            return im
        prov = self._get_kraken()
        if not prov:
            return {"error": "Modello Kraken non caricato"}
        return prov.process(im, status_callback=status_callback).to_dict()

    def process_image_google_vision(
        self, image_input: str | Any | Image.Image, status_callback=None
    ) -> dict[str, Any]:
        """Route the input through Google Vision OCR."""
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im:
            return im
        return GoogleVisionProvider(self.google_api_key).process(im, status_callback=status_callback).to_dict()

    def process_image_huggingface(
        self, image_input: str | Any | Image.Image, model_id=None, status_callback=None
    ) -> dict[str, Any]:
        """Run OCR via Hugging Face inference API."""
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im:
            return im
        model_id = model_id or "magistermilitum/tridis_v2_HTR_historical_manuscripts"
        return HFInferenceProvider(self.hf_token, model_id).process(im, status_callback=status_callback).to_dict()

    def process_image_openai(
        self, image_input: str | Any | Image.Image, model="o3-mini", status_callback=None
    ) -> dict[str, Any]:
        """Ask OpenAI for the transcription output."""
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im:
            return im
        return OpenAIProvider(self.openai_api_key, model).process(im, status_callback=status_callback).to_dict()

    def process_image_anthropic(
        self, image_input: str | Any | Image.Image, model="claude-4-sonnet", status_callback=None
    ) -> dict[str, Any]:
        """Delegate OCR to Anthropic Claude models."""
        im = self._load_im(image_input)
        if isinstance(im, dict) and "error" in im:
            return im
        return AnthropicProvider(self.anthropic_api_key, model).process(im, status_callback=status_callback).to_dict()

    def process_page(
        self,
        image: Image.Image,
        engine: str = "kraken",
        model: str | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Unified entry point for OCR."""
        if engine == "kraken":
            return self.process_image(image, status_callback=status_callback)
        elif engine == "google":
            return self.process_image_google_vision(image, status_callback=status_callback)
        elif engine == "openai":
            return self.process_image_openai(image, model=model or "gpt-5", status_callback=status_callback)
        elif engine == "anthropic":
            return self.process_image_anthropic(
                image, model=model or "claude-4-sonnet", status_callback=status_callback
            )
        elif engine == "huggingface":
            return self.process_image_huggingface(image, model_id=model, status_callback=status_callback)
        else:
            return {"error": f"Motore '{engine}' non supportato."}

    def _load_im(self, image_input):
        """Load an image given a path or PIL object."""
        try:
            if isinstance(image_input, Image.Image):
                return image_input
            return Image.open(image_input)
        except Exception as e:
            return {"error": f"Errore caricamento immagine: {e}"}
