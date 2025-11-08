"""
OCR focus verification for Claude-in-VSCode.

Provides one-shot OCR scanning to verify Claude chat input is focused.
No retries - caller decides what to do on failure.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Import OCR dependencies
try:
    import pytesseract
    from PIL import Image, ImageGrab, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR dependencies not available (pytesseract/PIL)")


def _preprocess_image(image: 'Image.Image') -> 'Image.Image':
    """
    Preprocess screenshot for better OCR accuracy.

    Args:
        image: PIL Image to preprocess

    Returns:
        Preprocessed PIL Image
    """
    # Convert to grayscale
    gray = image.convert('L')

    # Slight sharpen
    sharpened = gray.filter(ImageFilter.SHARPEN)

    # Simple threshold to enhance contrast
    # This helps OCR detect text more reliably
    enhancer = ImageEnhance.Contrast(sharpened)
    enhanced = enhancer.enhance(2.0)

    return enhanced


def _normalize_text(text: str) -> str:
    """
    Normalize OCR text for matching.

    Args:
        text: Raw OCR text

    Returns:
        Normalized text (lowercase, stripped, collapsed spaces)
    """
    # Lowercase
    normalized = text.lower()

    # Strip whitespace
    normalized = normalized.strip()

    # Collapse multiple spaces
    import re
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized


def ocr_scan_for_any(
    target_phrases: List[str],
    *,
    region: Optional[Tuple[int, int, int, int]] = None,
    save_fail_path: Optional[Path] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Scan screen for any of the target phrases using OCR.

    One-shot scan - no retries. Caller decides what to do on failure.

    Args:
        target_phrases: List of phrases to search for (will be normalized)
        region: Optional (left, top, right, bottom) region to scan
        save_fail_path: If provided and no match, save screenshot here

    Returns:
        Tuple of (matched, metadata)
        - matched: True if any phrase found
        - metadata: Dict with keys:
            - matched_phrase: The phrase that was found (or None)
            - confidence: OCR confidence (0.0-1.0, or None)
            - screenshot_path: Path to saved screenshot (if saved)
            - ocr_text_sample: First 200 chars of OCR text
    """
    if not OCR_AVAILABLE:
        logger.error("OCR not available - cannot verify focus")
        return False, {
            "matched_phrase": None,
            "confidence": None,
            "screenshot_path": None,
            "error": "OCR dependencies not installed"
        }

    logger.debug("Starting OCR scan for focus verification...")

    try:
        # Capture screenshot
        if region:
            screenshot = ImageGrab.grab(bbox=region)
        else:
            screenshot = ImageGrab.grab()

        # Preprocess for better OCR
        processed = _preprocess_image(screenshot)

        # Run OCR
        ocr_text = pytesseract.image_to_string(processed)

        # Normalize
        normalized_text = _normalize_text(ocr_text)

        logger.debug(f"OCR text sample: {normalized_text[:200]}")

        # Check for any target phrase
        target_phrases_normalized = [_normalize_text(p) for p in target_phrases]

        for original_phrase, normalized_phrase in zip(target_phrases, target_phrases_normalized):
            if normalized_phrase in normalized_text:
                logger.info(f"[OCR] Match found: '{original_phrase}'")

                # Try to get detailed OCR data for confidence
                try:
                    ocr_data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
                    # Average confidence of detected text
                    confidences = [float(c) for c in ocr_data['conf'] if c != -1]
                    avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.8
                except Exception:
                    avg_confidence = 0.8  # Default estimate

                return True, {
                    "matched_phrase": original_phrase,
                    "confidence": avg_confidence,
                    "screenshot_path": None,
                    "ocr_text_sample": normalized_text[:200]
                }

        # No match found
        logger.warning("[OCR] No match found for any target phrase")

        # Save screenshot if requested
        screenshot_path = None
        if save_fail_path:
            save_fail_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot.save(save_fail_path)
            screenshot_path = str(save_fail_path)
            logger.info(f"[OCR] Failure screenshot saved: {screenshot_path}")

        return False, {
            "matched_phrase": None,
            "confidence": None,
            "screenshot_path": screenshot_path,
            "ocr_text_sample": normalized_text[:200]
        }

    except Exception as e:
        logger.error(f"[OCR] Error during scan: {e}", exc_info=True)
        return False, {
            "matched_phrase": None,
            "confidence": None,
            "screenshot_path": None,
            "error": str(e)
        }


# Default target phrases for Claude chat input
CLAUDE_INPUT_PHRASES = [
    "send a message",
    "ask claude",
    "message claude",
    "type a message",
    "chat with claude"
]


def verify_claude_input_focus(
    save_fail_path: Optional[Path] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to verify Claude input is focused.

    Uses default CLAUDE_INPUT_PHRASES.

    Args:
        save_fail_path: If provided and no match, save screenshot here

    Returns:
        Tuple of (matched, metadata)
    """
    return ocr_scan_for_any(
        CLAUDE_INPUT_PHRASES,
        save_fail_path=save_fail_path
    )
