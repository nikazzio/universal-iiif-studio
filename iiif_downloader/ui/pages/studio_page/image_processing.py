"""
Image Processing Module for Studio Page
Handles all image manipulation operations (brightness, contrast, cropping)
Separated from UI logic for better maintainability and testability.
"""

from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
from PIL import Image, ImageEnhance


from iiif_downloader.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """Handles image processing operations for the Studio page."""

    @staticmethod
    @st.cache_data(show_spinner=False)
    def load_image(image_path: Path) -> Optional[Image.Image]:
        """
        Load an image from disk.

        Args:
            image_path: Path to the image file

        Returns:
            PIL Image object or None if loading fails
        """
        try:
            if image_path.exists():
                return Image.open(str(image_path))
        except Exception as e:
            logger.error(f"Error loading image: {e}")
        return None

    @staticmethod
    def adjust_brightness(image: Image.Image, brightness: float) -> Image.Image:
        """
        Adjust image brightness.

        Args:
            image: PIL Image object
            brightness: Brightness factor (0.0 = black, 1.0 = original, 2.0 = twice as bright)

        Returns:
            Adjusted PIL Image
        """
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(brightness)

    @staticmethod
    def adjust_contrast(image: Image.Image, contrast: float) -> Image.Image:
        """
        Adjust image contrast.

        Args:
            image: PIL Image object
            contrast: Contrast factor (0.0 = gray, 1.0 = original, 2.0 = twice the contrast)

        Returns:
            Adjusted PIL Image
        """
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(contrast)

    @staticmethod
    def apply_adjustments(image: Image.Image, brightness: float = 1.0, contrast: float = 1.0) -> Image.Image:
        """
        Apply multiple adjustments to an image.

        Args:
            image: PIL Image object
            brightness: Brightness factor (default: 1.0)
            contrast: Contrast factor (default: 1.0)

        Returns:
            Adjusted PIL Image
        """
        # Apply brightness first, then contrast
        if brightness != 1.0:
            image = ImageProcessor.adjust_brightness(image, brightness)
        if contrast != 1.0:
            image = ImageProcessor.adjust_contrast(image, contrast)
        return image

    @staticmethod
    def crop_image(image: Image.Image, coordinates: Tuple[int, int, int, int]) -> Image.Image:
        """
        Crop an image to specified coordinates.

        Args:
            image: PIL Image object
            coordinates: Tuple of (x0, y0, x1, y1) in pixels

        Returns:
            Cropped PIL Image
        """
        return image.crop(coordinates)

    @staticmethod
    def save_crop_to_bytes(cropped_image: Image.Image) -> bytes:
        """
        Convert a cropped image to PNG bytes for database storage.

        Args:
            cropped_image: PIL Image object

        Returns:
            PNG image as bytes
        """
        buffer = BytesIO()
        cropped_image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def get_image_stats(image: Image.Image) -> dict:
        """
        Get basic statistics about an image.

        Args:
            image: PIL Image object

        Returns:
            Dictionary with width, height, format, and mode
        """
        return {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
            "size_mb": len(image.tobytes()) / (1024 * 1024),
        }
