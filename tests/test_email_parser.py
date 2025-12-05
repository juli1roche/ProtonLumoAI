#!/usr/bin/env python3
import unittest
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from scripts.email_parser import EmailParser

class TestEmailParser(unittest.TestCase):

    def setUp(self):
        self.parser = EmailParser()

    def test_simple_email(self):
        msg = MIMEText("Ceci est le corps du message.", "plain", "utf-8")
        msg["Subject"] = "Sujet simple"
        msg["From"] = "expediteur@test.com"
        subject, sender, body = self.parser.parse(msg.as_bytes())
        self.assertEqual(subject, "Sujet simple")
        self.assertEqual(sender, "expediteur@test.com")
        self.assertEqual(body, "Ceci est le corps du message.")

    def test_utf8_header(self):
        subject_str = "Sujet avec accent éàç"
        msg = MIMEText("Corps.")
        msg["Subject"] = Header(subject_str, "utf-8")
        subject, _, _ = self.parser.parse(msg.as_bytes())
        self.assertEqual(subject, subject_str)

    def test_corrupted_header(self):
        # Simule un en-tête mal formé
        raw_email = b"From: sender@test.com\nSubject: =?iso-8859-1?Q?Sujet_probl=E8me?=\n\nCorps."
        subject, _, _ = self.parser.parse(raw_email)
        self.assertIn("Sujet problème", subject)

    def test_no_body(self):
        # Email sans partie texte
        msg = MIMEMultipart()
        msg["Subject"] = "Sujet"
        msg.attach(MIMEText("<html><body>Ceci est du HTML</body></html>", "html"))
        _, _, body = self.parser.parse(msg.as_bytes())
        self.assertEqual(body, "")

    def test_latin1_encoding(self):
        body_str = "Corps avec des caractères spèciaux en latin-1"
        msg = MIMEText(body_str, "plain", "latin-1")
        msg["Subject"] = "Sujet Latin-1"
        _, _, body = self.parser.parse(msg.as_bytes())
        self.assertEqual(body, body_str)

if __name__ == '__main__':
    unittest.main()
