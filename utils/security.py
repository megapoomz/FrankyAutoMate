"""
SEC-1: DPAPI-based config encryption for Windows
SEC-2/3: Checksum verification helpers for downloaded files

Provides secure storage for sensitive config data (license keys, HWIDs)
using Windows Data Protection API (DPAPI) which encrypts data with
machine/user-specific keys.
"""

import os
import json
import hashlib
import logging
import base64

# ── SEC-2/3: Checksum Verification ──────────────────────────────────────

# Known good SHA256 hashes for trusted downloads
KNOWN_CHECKSUMS = {
    "tesseract-ocr-w64-setup-5.5.0.20241111.exe": "PLACEHOLDER_HASH",
    "tesseract-ocr-w64-setup-v5.3.0.20221222.exe": "PLACEHOLDER_HASH",
}


def verify_file_checksum(filepath: str, expected_hash: str = None, filename: str = None) -> bool:
    """
    Verify SHA256 checksum of a downloaded file.

    Args:
        filepath: Path to the file to verify
        expected_hash: Expected SHA256 hash (hex string). If None, lookup by filename.
        filename: Filename to use for KNOWN_CHECKSUMS lookup

    Returns:
        True if hash matches or no known hash exists, False if mismatch
    """
    if not expected_hash and filename:
        expected_hash = KNOWN_CHECKSUMS.get(filename)

    if not expected_hash or expected_hash == "PLACEHOLDER_HASH":
        logging.warning(f"No checksum available for {filepath}, skipping verification")
        return True  # Allow if no known hash

    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        actual_hash = sha256.hexdigest()
        if actual_hash.lower() != expected_hash.lower():
            logging.error(f"CHECKSUM MISMATCH for {filepath}!")
            logging.error(f"  Expected: {expected_hash}")
            logging.error(f"  Actual:   {actual_hash}")
            return False
        logging.info(f"Checksum verified OK: {filepath}")
        return True
    except Exception as e:
        logging.error(f"Checksum verification failed: {e}")
        return False


# ── SEC-1: DPAPI Config Encryption ──────────────────────────────────────


def _dpapi_available():
    """Check if DPAPI is available (Windows only)"""
    try:
        import ctypes
        import ctypes.wintypes

        return hasattr(ctypes.windll, "crypt32")
    except Exception:
        return False


def dpapi_encrypt(data: bytes) -> bytes:
    """Encrypt data using Windows DPAPI (CurrentUser scope)"""
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        input_blob = DATA_BLOB()
        input_blob.cbData = len(data)
        input_blob.pbData = ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_char))

        output_blob = DATA_BLOB()

        if ctypes.windll.crypt32.CryptProtectData(ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
            encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
            ctypes.windll.kernel32.LocalFree(output_blob.pbData)
            return encrypted
        else:
            raise OSError("CryptProtectData failed")
    except Exception as e:
        logging.warning(f"DPAPI encryption failed: {e}, falling back to plaintext")
        return None


def dpapi_decrypt(encrypted: bytes) -> bytes:
    """Decrypt DPAPI-encrypted data"""
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        input_blob = DATA_BLOB()
        input_blob.cbData = len(encrypted)
        input_blob.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted, len(encrypted)), ctypes.POINTER(ctypes.c_char))

        output_blob = DATA_BLOB()

        if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
            decrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
            ctypes.windll.kernel32.LocalFree(output_blob.pbData)
            return decrypted
        else:
            raise OSError("CryptUnprotectData failed")
    except Exception as e:
        logging.warning(f"DPAPI decryption failed: {e}")
        return None


def save_config_secure(config_data: dict, filepath: str):
    """Save config data with DPAPI encryption if available, else plaintext"""
    json_str = json.dumps(config_data, indent=2, ensure_ascii=False)

    if _dpapi_available():
        encrypted = dpapi_encrypt(json_str.encode("utf-8"))
        if encrypted:
            # Save as base64-encoded encrypted blob
            secure_data = {"_encrypted": True, "_data": base64.b64encode(encrypted).decode("ascii")}
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(secure_data, f, indent=2)
            return

    # Fallback: save plaintext
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json_str)


def load_config_secure(filepath: str) -> dict:
    """Load config data, decrypting if DPAPI-encrypted"""
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, dict) and raw.get("_encrypted"):
            # Encrypted config
            encrypted = base64.b64decode(raw["_data"])
            decrypted = dpapi_decrypt(encrypted)
            if decrypted:
                return json.loads(decrypted.decode("utf-8"))
            else:
                logging.error("Failed to decrypt config, returning empty")
                return {}
        else:
            # Legacy plaintext config
            return raw
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return {}
