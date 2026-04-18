"""
Stealth and obfuscation techniques for injection payloads.
Tests whether RAG preprocessing/sanitization catches injections.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict


class StealthEncoder:

    @staticmethod
    def zero_width_inject(clean_text: str, payload: str) -> str:
        """Inject payload using zero-width characters between visible chars."""
        ZWJ = "\u200d"   # Zero-width joiner  → bit 1
        ZWNJ = "\u200c"  # Zero-width non-joiner → bit 0

        encoded = ""
        for char in payload:
            bits = format(ord(char), "08b")
            encoded += "".join(ZWJ if b == "1" else ZWNJ for b in bits)

        mid = len(clean_text) // 2
        return clean_text[:mid] + encoded + clean_text[mid:]

    @staticmethod
    def whitespace_inject(clean_text: str, payload: str) -> str:
        """Encode payload in trailing whitespace patterns (tab=1, space=0)."""
        encoded_lines = []
        for char in payload[:50]:  # Limit to avoid huge documents
            bits = format(ord(char), "08b")
            ws = "".join("\t" if b == "1" else " " for b in bits)
            encoded_lines.append(ws)
        return clean_text + "\n" + "\n".join(encoded_lines)

    @staticmethod
    def html_comment_inject(clean_text: str, payload: str) -> str:
        """Payload in HTML comment — may survive markdown rendering."""
        return f"{clean_text}\n<!-- {payload} -->"

    @staticmethod
    def unicode_homoglyph_inject(payload: str) -> str:
        """Replace ASCII chars with visually identical Unicode homoglyphs."""
        homoglyphs: Dict[str, str] = {
            "a": "\u0430",  # Cyrillic а
            "e": "\u0435",  # Cyrillic е
            "o": "\u043e",  # Cyrillic о
            "p": "\u0440",  # Cyrillic р
            "c": "\u0441",  # Cyrillic с
            "i": "\u0456",  # Cyrillic і
            "x": "\u0445",  # Cyrillic х
        }
        return "".join(homoglyphs.get(c, c) for c in payload)

    @staticmethod
    def base64_obfuscate(payload: str) -> str:
        """Wrap payload in a base64 'encoded attachment' pattern."""
        import base64
        encoded = base64.b64encode(payload.encode()).decode()
        return f"[Attachment data: {encoded}]"

    @staticmethod
    def leetspeak_transform(payload: str) -> str:
        """Replace letters with leet equivalents to bypass keyword filters."""
        leet: Dict[str, str] = {
            "a": "4", "e": "3", "i": "1", "o": "0",
            "s": "5", "t": "7", "l": "1", "g": "9",
        }
        return "".join(leet.get(c.lower(), c) for c in payload)

    @staticmethod
    def detect_stealth_in_document(text: str) -> dict:
        """
        Scan a document for stealth injection attempts.
        Returns a findings dict — used in defensive scanner mode.
        """
        findings: dict = {
            "zero_width_chars": False,
            "suspicious_whitespace": False,
            "html_comments": False,
            "homoglyphs_detected": False,
            "base64_blob": False,
            "risk_score": 0,
            "details": [],
        }

        # Zero-width characters
        zero_width_chars = [
            "\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\ufeff",
        ]
        if any(zw in text for zw in zero_width_chars):
            findings["zero_width_chars"] = True
            findings["risk_score"] += 40
            findings["details"].append("Zero-width characters detected")

        # Suspicious whitespace patterns (encoding in tab/space sequences)
        lines = text.split("\n")
        tab_heavy = sum(1 for line in lines if line.count("\t") > 3)
        if tab_heavy > 2:
            findings["suspicious_whitespace"] = True
            findings["risk_score"] += 20
            findings["details"].append(f"{tab_heavy} lines with suspicious tab patterns")

        # HTML comments
        if "<!--" in text and "-->" in text:
            findings["html_comments"] = True
            findings["risk_score"] += 15
            findings["details"].append("HTML comment blocks present")

        # Homoglyph detection — check for mixed scripts in same word
        for word in text.split():
            scripts = set()
            for char in word:
                if char.isalpha():
                    cat = unicodedata.name(char, "").split(" ")[0]
                    scripts.add(cat)
            if len(scripts) > 1 and "CYRILLIC" in scripts:
                findings["homoglyphs_detected"] = True
                findings["risk_score"] += 30
                findings["details"].append(f"Mixed-script word detected: '{word[:20]}'")
                break

        # Base64 blobs in brackets
        if re.search(r"\[Attachment data: [A-Za-z0-9+/=]{20,}\]", text):
            findings["base64_blob"] = True
            findings["risk_score"] += 25
            findings["details"].append("Base64 blob pattern detected")

        return findings
