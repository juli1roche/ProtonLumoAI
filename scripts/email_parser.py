#!/usr/bin/env python3
# ============================================================================
# EMAIL PARSER - ProtonLumoAI
# Parser robuste pour les emails bruts
# ============================================================================

import email
from email.message import Message
from email.header import decode_header
from typing import Optional, Tuple

from loguru import logger

class EmailParser:
    """Classe dédiée au parsing robuste des emails bruts."""

    def parse(self, raw_email: bytes) -> Tuple[str, str, str]:
        """Parse un email brut et retourne le sujet, le corps et l'expéditeur."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            subject = self._decode_header(msg.get("Subject", ""))
            sender = self._decode_header(msg.get("From", ""))
            body = self._get_body(msg)
            
            return subject, sender, body
        except Exception as e:
            logger.error(f"Erreur de parsing de l'email: {e}")
            return "", "", ""

    def _decode_header(self, header: str) -> str:
        """Décode un en-tête d'email de manière robuste."""
        if not header:
            return ""
        
        try:
            decoded_parts = decode_header(header)
            header_parts = []
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    header_parts.append(part.decode(charset or 'utf-8', errors='ignore'))
                else:
                    header_parts.append(part)
            return " ".join(header_parts)
        except Exception as e:
            logger.warning(f"Impossible de décoder l'en-tête: {e}")
            return str(header) # Fallback

    def _get_body(self, msg: Message) -> str:
        """Extrait le corps de l'email de manière robuste."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        return self._decode_payload(payload)
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'extraction du corps (multipart): {e}")
        else:
            try:
                payload = msg.get_payload(decode=True)
                return self._decode_payload(payload)
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction du corps (non-multipart): {e}")
        
        return body

    def _decode_payload(self, payload: bytes) -> str:
        """Tente de décoder le payload avec plusieurs encodages."""
        for encoding in ["utf-8", "latin-1", "iso-8859-1"]:
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        logger.warning("Impossible de décoder le payload avec les encodages courants. Utilisation de utf-8 avec ignore.")
        return payload.decode("utf-8", errors="ignore")
