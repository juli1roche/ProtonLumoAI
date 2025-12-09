#!/usr/bin/env python3
"""
Pré-tri automatique pour Folders/2025 et Gmail
Crée les sous-dossiers et déplace les emails par catégories intelligentes
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
import imaplib
import email
from email.header import decode_header

load_dotenv()

class PreTriAutomatique:
    """Pré-tri automatique des dossiers génériques"""

    def __init__(self):
        self.imap_host = os.getenv("PROTON_LUMO_IMAP_HOST", "localhost")
        self.imap_port = int(os.getenv("PROTON_LUMO_IMAP_PORT", 1143))
        self.username = os.getenv("PROTON_USERNAME")
        self.password = os.getenv("PROTON_PASSWORD")
        self.mail = None
        self.mailbox_selected = False
        self.rapport = {
            "dossiers_analyses": [],
            "sous_dossiers_crees": [],
            "emails_deplaces": 0,
            "categories_detectees": {},
        }

    def connecter(self):
        """Connecter à ProtonMail Bridge"""
        try:
            print(f"🔗 Connexion à {self.imap_host}:{self.imap_port}...")
            self.mail = imaplib.IMAP4(self.imap_host, self.imap_port)
            self.mail.starttls()
            self.mail.login(self.username, self.password)
            print("✅ Connecté!\n")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

    def parse_mailbox_name(self, mailbox_line):
        """Parser le nom de mailbox à partir d'une ligne LIST IMAP"""
        try:
            line_str = (
                mailbox_line.decode("utf-8")
                if isinstance(mailbox_line, bytes)
                else str(mailbox_line)
            )
            # Format typique: (\HasNoChildren) "/" "Folders/2025"
            match = re.search(r'"([^\"]+)"\s*$', line_str)
            if match:
                return match.group(1)
            # Fallback très défensif
            parts = line_str.split()
            if len(parts) >= 3:
                return parts[-1].strip('"')
            return None
        except Exception:
            return None

    def extraire_features_email(self, email_data):
        """Extraire features d'un email"""
        try:
            msg = email.message_from_bytes(email_data)

            subject = msg.get("Subject", "")
            if not isinstance(subject, str):
                try:
                    decoded = decode_header(subject)
                    subject = decoded[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode("utf-8", errors="ignore")
                except Exception:
                    subject = ""
            subject = subject.lower()

            sender = msg.get("From", "").lower()

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = (
                                part.get_payload(decode=True)
                                .decode("utf-8", errors="ignore")
                                .lower()
                            )
                            break
                        except Exception:
                            pass
            else:
                try:
                    body = (
                        msg.get_payload(decode=True)
                        .decode("utf-8", errors="ignore")
                        .lower()
                    )
                except Exception:
                    body = ""

            return {
                "subject": subject,
                "sender": sender,
                "body": body,
                "full_text": f"{subject} {sender} {body}",
            }
        except Exception:
            return {"subject": "", "sender": "", "body": "", "full_text": ""}

    def detecter_categorie(self, features):
        """Détecter la catégorie d'un email"""
        full_text = features["full_text"]
        subject = features["subject"]

        scores = {
            "PRO": 0,
            "FINANCE": 0,
            "NEWSLETTER": 0,
            "COMMERCE": 0,
            "VOYAGE": 0,
            "PERSONNEL": 0,
        }

        # PRO
        if any(
            kw in full_text
            for kw in [
                "meeting",
                "reunion",
                "project",
                "deadline",
                "report",
                "agenda",
            ]
        ):
            scores["PRO"] += 3
        if any(kw in subject for kw in ["meeting", "reunion", "project"]):
            scores["PRO"] += 2

        # FINANCE
        if any(
            kw in full_text
            for kw in [
                "invoice",
                "facture",
                "payment",
                "virement",
                "account",
                "salary",
            ]
        ):
            scores["FINANCE"] += 3

        # NEWSLETTER
        if any(
            kw in full_text for kw in ["newsletter", "digest", "weekly", "unsubscribe"]
        ):
            scores["NEWSLETTER"] += 3

        # COMMERCE
        if any(
            kw in full_text for kw in ["order", "commande", "delivery", "tracking"]
        ):
            scores["COMMERCE"] += 3

        # VOYAGE
        if any(
            kw in full_text for kw in ["flight", "hotel", "booking", "reservation"]
        ):
            scores["VOYAGE"] += 3

        # PERSONNEL
        if any(
            kw in full_text
            for kw in ["family", "famille", "friend", "ami", "birthday"]
        ):
            scores["PERSONNEL"] += 3

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        if best_score >= 2:
            return best_category, best_score / 10.0
        return "MIXED", 0.5

    def analyser_dossier(self, dossier_name):
        """Analyser un dossier et retourner les stats"""
        print(f"\n📁 Analysing {dossier_name}...")
        try:
            status, mailbox_list = self.mail.list()
            dossier_imap = None

            for mailbox_line in mailbox_list:
                mailbox_name = self.parse_mailbox_name(mailbox_line)
                if mailbox_name and dossier_name.lower() in mailbox_name.lower():
                    dossier_imap = mailbox_name
                    break

            if not dossier_imap:
                print("  ❌ Dossier non trouvé")
                return None

            status, _ = self.mail.select(f'"{dossier_imap}"')
            if status != "OK":
                print(f"  ❌ Impossible de sélectionner {dossier_imap}")
                return None
            self.mailbox_selected = True

            status, email_ids = self.mail.search(None, "ALL")
            if status != "OK" or not email_ids or not email_ids[0]:
                print("  📧 0 emails trouvés")
                return None

            email_ids = email_ids[0].split()[-100:]
            print(f"  📧 Found {len(email_ids)} emails")

            categories_count = Counter()
            emails_par_categorie = {}

            for idx, email_id in enumerate(email_ids, 1):
                status, email_data = self.mail.fetch(email_id, "(RFC822)")
                if status != "OK" or not email_data:
                    continue
                features = self.extraire_features_email(email_data[0][1])
                categorie, score = self.detecter_categorie(features)

                categories_count[categorie] += 1

                emails_par_categorie.setdefault(categorie, []).append(
                    {
                        "id": email_id,
                        "subject": features["subject"],
                        "score": score,
                    }
                )

                if idx % 20 == 0:
                    print(f"    ✓ Processed {idx}/{len(email_ids)}")

            print(f"\n  📊 Résultats pour {dossier_name}:")
            for cat, count in categories_count.most_common():
                pct = (count / len(email_ids)) * 100
                print(f"    [{cat:12s}] {count:3d} emails ({pct:5.1f}%)")

            self.rapport["categories_detectees"][dossier_name] = dict(categories_count)

            return {
                "dossier": dossier_name,
                "dossier_imap": dossier_imap,
                "total_emails": len(email_ids),
                "categories": categories_count,
                "emails_par_categorie": emails_par_categorie,
            }
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback

            traceback.print_exc()
            return None

    def creer_sous_dossiers(self, analyse_resultat):
        """Créer les sous-dossiers nécessaires"""
        dossier_parent = analyse_resultat["dossier_imap"]
        categories = analyse_resultat["categories"]

        print(f"\n🔨 Creating subfolders for {dossier_parent}...")

        categories_a_creer = [
            cat
            for cat, count in categories.items()
            if count >= 5 and cat != "MIXED"
        ]

        for categorie in categories_a_creer:
            sous_dossier = f"{dossier_parent}/{categorie}"
            try:
                status, _ = self.mail.create(f'"{sous_dossier}"')
                if status == "OK":
                    print(f"  ✅ Created: {sous_dossier}")
                    self.rapport["sous_dossiers_crees"].append(sous_dossier)
                else:
                    print(f"  ⚠️  {sous_dossier} (already exists or error)")
            except Exception as e:
                print(f"  ⚠️  Error creating {sous_dossier}: {e}")

    def deplacer_emails(self, analyse_resultat):
        """Déplacer les emails vers les sous-dossiers"""
        dossier_parent = analyse_resultat["dossier_imap"]
        emails_par_categorie = analyse_resultat["emails_par_categorie"]

        print("\n📮 Moving emails...")

        status, _ = self.mail.select(f'"{dossier_parent}"')
        if status != "OK":
            print(f"  ❌ Impossible de re-sélectionner {dossier_parent}")
            return
        self.mailbox_selected = True

        total_deplace = 0

        for categorie, emails in emails_par_categorie.items():
            if len(emails) < 5 or categorie == "MIXED":
                continue

            sous_dossier = f"{dossier_parent}/{categorie}"

            for email_info in emails[: min(20, len(emails))]:
                try:
                    self.mail.copy(email_info["id"], f'"{sous_dossier}"')
                    self.mail.store(email_info["id"], "+FLAGS", "\\Deleted")
                    total_deplace += 1
                except Exception as e:
                    subject_preview = (
                        email_info["subject"][:50]
                        if email_info["subject"]
                        else "No subject"
                    )
                    print(f"  ❌ Error moving '{subject_preview}': {e}")

        try:
            self.mail.expunge()
            print(f"  ✅ Moved {total_deplace} emails")
            self.rapport["emails_deplaces"] += total_deplace
        except Exception as e:
            print(f"  ⚠️  Error expunging: {e}")

    def sauvegarder_rapport(self):
        """Sauvegarder le rapport"""
        rapport_file = Path.home() / "ProtonLumoAI/data/learning/pretri_rapport.json"
        rapport_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rapport_file, "w") as f:
            json.dump(self.rapport, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Rapport sauvegardé: {rapport_file}")

    def afficher_resume(self):
        """Afficher un résumé du pré-tri"""
        print("\n" + "=" * 60)
        print("✅ PRÉ-TRI TERMINÉ")
        print("=" * 60 + "\n")

        print("📊 RÉSUMÉ:")
        print(f"  Dossiers analysés: {len(self.rapport['dossiers_analyses'])}")
        print(f"  Sous-dossiers créés: {len(self.rapport['sous_dossiers_crees'])}")
        print(f"  Emails déplacés: {self.rapport['emails_deplaces']}")

        if self.rapport["sous_dossiers_crees"]:
            print("\n📁 Sous-dossiers créés:")
            for sd in self.rapport["sous_dossiers_crees"]:
                print(f"  ✓ {sd}")

        if self.rapport["categories_detectees"]:
            print("\n🎯 Catégories détectées:")
            for dossier, categories in self.rapport["categories_detectees"].items():
                print(f"\n  {dossier}:")
                total = sum(categories.values()) or 1
                for cat, count in sorted(
                    categories.items(), key=lambda x: x[1], reverse=True
                ):
                    pct = (count / total) * 100
                    print(f"    - {cat}: {count} emails ({pct:.1f}%)")

        print("\n" + "=" * 60)
        print("🚀 PROCHAINES ÉTAPES:")
        print("=" * 60)
        print("\n1. Vérifier les sous-dossiers dans ProtonMail")
        print("2. Ajuster manuellement les emails mal classés")
        print("3. Lancer la passe d'apprentissage:")
        print("\n   python scripts/sync_and_learn.py\n")

    def run(self):
        """Exécuter le pré-tri"""
        print("\n" + "=" * 60)
        print("🤖 PRÉ-TRI AUTOMATIQUE - Folders/2025 et Gmail")
        print("=" * 60 + "\n")

        if not self.connecter():
            return False

        try:
            analyse_2025 = self.analyser_dossier("Folders/2025")
            if analyse_2025:
                self.rapport["dossiers_analyses"].append("Folders/2025")
                self.creer_sous_dossiers(analyse_2025)
                self.deplacer_emails(analyse_2025)

            analyse_gmail = self.analyser_dossier("Gmail")
            if analyse_gmail:
                self.rapport["dossiers_analyses"].append("Gmail")
                self.creer_sous_dossiers(analyse_gmail)
                self.deplacer_emails(analyse_gmail)

            self.sauvegarder_rapport()
            self.afficher_resume()
            return True
        except Exception as e:
            print(f"\n❌ Erreur globale: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            if self.mail and self.mailbox_selected:
                try:
                    self.mail.close()
                except Exception:
                    pass
            if self.mail:
                try:
                    self.mail.logout()
                except Exception:
                    pass


if __name__ == "__main__":
    pretri = PreTriAutomatique()
    ok = pretri.run()
    sys.exit(0 if ok else 1)
