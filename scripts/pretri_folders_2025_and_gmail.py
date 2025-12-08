#!/usr/bin/env python3
"""
Pré-tri automatique pour Folders/2025 et Gmail
Crée les sous-dossiers et déplace les emails par catégories intelligentes
"""

import os
import sys
import json
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
import imaplib
import email
from email.header import decode_header

load_dotenv()

class PreTriAutomatique:
    """
    Pré-tri automatique des dossiers génériques
    """
    
    def __init__(self):
        self.imap_host = os.getenv('PROTON_LUMO_IMAP_HOST', 'localhost')
        self.imap_port = int(os.getenv('PROTON_LUMO_IMAP_PORT', 1143))
        self.username = os.getenv('PROTON_USERNAME')
        self.password = os.getenv('PROTON_PASSWORD')
        self.mail = None
        self.rapport = {
            'dossiers_analyses': [],
            'sous_dossiers_crees': [],
            'emails_deplaces': 0,
            'categories_detectees': {},
            'regles_appliquees': []
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
    
    def extraire_features_email(self, email_data):
        """Extraire features d'un email"""
        try:
            msg = email.message_from_bytes(email_data)
            
            subject = msg.get('Subject', '')
            if isinstance(subject, str):
                subject = subject.lower()
            else:
                try:
                    decoded = decode_header(subject)
                    subject = decoded[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode('utf-8', errors='ignore')
                    subject = subject.lower()
                except:
                    subject = ''
            
            sender = msg.get('From', '').lower()
            
            # Extraire body
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore').lower()
                            break
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore').lower()
                except:
                    body = ''
            
            return {
                'subject': subject,
                'sender': sender,
                'body': body,
                'full_text': f"{subject} {sender} {body}"
            }
        except Exception as e:
            return {'subject': '', 'sender': '', 'body': '', 'full_text': ''}
    
    def detecter_categorie(self, features):
        """Détecter la catégorie d'un email"""
        full_text = features['full_text']
        subject = features['subject']
        
        # Scoring par catégorie
        scores = {
            'PRO': 0,
            'FINANCE': 0,
            'NEWSLETTER': 0,
            'COMMERCE': 0,
            'VOYAGE': 0,
            'PERSONNEL': 0
        }
        
        # Keywords PRO
        if any(kw in full_text for kw in ['meeting', 'reunion', 'project', 'deadline', 'report', 'agenda', 'calendrier', 'standup', 'sprint']):
            scores['PRO'] += 3
        if any(kw in subject for kw in ['meeting', 'reunion', 'project', 'deadline', 'report']):
            scores['PRO'] += 2
        
        # Keywords FINANCE
        if any(kw in full_text for kw in ['invoice', 'facture', 'payment', 'virement', 'account', 'montant', 'prix', 'amount', 'salary', 'salaire', 'remboursement']):
            scores['FINANCE'] += 3
        if any(kw in subject for kw in ['invoice', 'facture', 'payment', 'salary']):
            scores['FINANCE'] += 2
        
        # Keywords NEWSLETTER
        if any(kw in full_text for kw in ['newsletter', 'digest', 'weekly', 'hebdo', 'weekly update', 'news', 'bulletin']):
            scores['NEWSLETTER'] += 3
        if 'unsubscribe' in full_text or 'se désabonner' in full_text:
            scores['NEWSLETTER'] += 2
        
        # Keywords COMMERCE
        if any(kw in full_text for kw in ['order', 'commande', 'shop', 'achat', 'delivery', 'livraison', 'tracking', 'panier']):
            scores['COMMERCE'] += 3
        if any(kw in subject for kw in ['order', 'commande', 'delivery', 'confirmation']):
            scores['COMMERCE'] += 2
        
        # Keywords VOYAGE
        if any(kw in full_text for kw in ['travel', 'voyage', 'flight', 'avion', 'hotel', 'booking', 'reservation', 'aeroport']):
            scores['VOYAGE'] += 3
        if any(kw in subject for kw in ['flight', 'booking', 'hotel', 'reservation']):
            scores['VOYAGE'] += 2
        
        # Keywords PERSONNEL
        if any(kw in full_text for kw in ['family', 'famille', 'personal', 'personnel', 'friend', 'ami', 'birthday', 'anniversaire', 'invitation']):
            scores['PERSONNEL'] += 3
        
        # Retourner la meilleure catégorie (avec minimum 2 points)
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        if best_score >= 2:
            return best_category, best_score / 10.0
        else:
            return 'MIXED', 0.5
    
    def analyser_dossier(self, dossier_name):
        """Analyser un dossier et retourner les statistiques"""
        print(f"\n📁 Analysing {dossier_name}...")
        
        try:
            status, mailbox_list = self.mail.list()
            dossier_imap = None
            
            # Trouver le dossier exact (peut avoir des variations de nom)
            for _, mailbox in mailbox_list:
                mailbox_str = mailbox.decode('utf-8') if isinstance(mailbox, bytes) else mailbox
                if dossier_name.lower() in mailbox_str.lower() or mailbox_str.lower().endswith(dossier_name.lower()):
                    dossier_imap = mailbox_str
                    break
            
            if not dossier_imap:
                print(f"  ❌ Dossier non trouvé")
                return None
            
            # Sélectionner le dossier
            self.mail.select(dossier_imap)
            
            # Récupérer les 100 derniers emails
            status, email_ids = self.mail.search(None, 'ALL')
            email_ids = email_ids[0].split()[-100:]  # Derniers 100
            
            print(f"  📧 Found {len(email_ids)} emails")
            
            categories_count = Counter()
            emails_par_categorie = {}
            
            for idx, email_id in enumerate(email_ids, 1):
                status, email_data = self.mail.fetch(email_id, '(RFC822)')
                features = self.extraire_features_email(email_data[0][1])
                categorie, score = self.detecter_categorie(features)
                
                categories_count[categorie] += 1
                
                if categorie not in emails_par_categorie:
                    emails_par_categorie[categorie] = []
                
                emails_par_categorie[categorie].append({
                    'id': email_id,
                    'subject': features['subject'],
                    'score': score
                })
                
                if idx % 20 == 0:
                    print(f"    ✓ Processed {idx}/{len(email_ids)}")
            
            print(f"\n  📊 Résultats pour {dossier_name}:")
            for cat, count in categories_count.most_common():
                pct = (count / len(email_ids)) * 100
                print(f"    [{cat:12s}] {count:3d} emails ({pct:5.1f}%)")
            
            self.rapport['categories_detectees'][dossier_name] = dict(categories_count)
            
            return {
                'dossier': dossier_name,
                'dossier_imap': dossier_imap,
                'total_emails': len(email_ids),
                'categories': categories_count,
                'emails_par_categorie': emails_par_categorie
            }
        
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            return None
    
    def creer_sous_dossiers(self, analyse_resultat):
        """Créer les sous-dossiers nécessaires"""
        dossier_parent = analyse_resultat['dossier']
        categories = analyse_resultat['categories']
        
        print(f"\n🔨 Creating subfolders for {dossier_parent}...")
        
        # Ne créer que les catégories avec 5+ emails
        categories_a_creer = [cat for cat, count in categories.items() if count >= 5]
        
        for categorie in categories_a_creer:
            sous_dossier = f"{dossier_parent}/{categorie}"
            
            try:
                # Essayer de créer le dossier
                status, response = self.mail.create(sous_dossier)
                
                if status == 'OK':
                    print(f"  ✅ Created: {sous_dossier}")
                    self.rapport['sous_dossiers_crees'].append(sous_dossier)
                else:
                    # Peut déjà exister
                    print(f"  ⚠️  {sous_dossier} (already exists or error)")
            
            except Exception as e:
                print(f"  ⚠️  Error creating {sous_dossier}: {e}")
    
    def deplacer_emails(self, analyse_resultat):
        """Déplacer les emails vers les sous-dossiers"""
        dossier_parent = analyse_resultat['dossier']
        dossier_imap = analyse_resultat['dossier_imap']
        emails_par_categorie = analyse_resultat['emails_par_categorie']
        
        print(f"\n📮 Moving emails...")
        
        # Sélectionner le dossier source
        self.mail.select(dossier_imap)
        
        total_deplace = 0
        
        for categorie, emails in emails_par_categorie.items():
            # Ne déplacer que si au moins 5 emails
            if len(emails) < 5:
                continue
            
            sous_dossier = f"{dossier_parent}/{categorie}"
            
            for email in emails[:min(20, len(emails))]:
                try:
                    # Copier l'email
                    self.mail.copy(email['id'], sous_dossier)
                    
                    # Marquer comme supprimé (sera vraiment supprimé au EXPUNGE)
                    self.mail.store(email['id'], '+FLAGS', '\\Deleted')
                    
                    total_deplace += 1
                    
                except Exception as e:
                    print(f"  ❌ Error moving {email['subject']}: {e}")
        
        # Finalement, expunge les emails marqués
        try:
            self.mail.expunge()
            print(f"  ✅ Moved {total_deplace} emails")
            self.rapport['emails_deplaces'] += total_deplace
        except Exception as e:
            print(f"  ⚠️  Error expunging: {e}")
    
    def sauvegarder_rapport(self):
        """Sauvegarder le rapport"""
        rapport_file = Path.home() / "ProtonLumoAI/data/learning/pretri_rapport.json"
        rapport_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(rapport_file, 'w') as f:
            json.dump(self.rapport, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Rapport sauvegardé: {rapport_file}")
    
    def afficher_resume(self):
        """Afficher un résumé du pré-tri"""
        print("\n" + "="*60)
        print("✅ PRÉ-TRI TERMINÉ")
        print("="*60 + "\n")
        
        print("📊 RÉSUMÉ:")
        print(f"  Dossiers analysés: {len(self.rapport['dossiers_analyses'])}")
        print(f"  Sous-dossiers créés: {len(self.rapport['sous_dossiers_crees'])}")
        print(f"  Emails déplacés: {self.rapport['emails_deplaces']}")
        
        print("\n📁 Sous-dossiers créés:")
        for sd in self.rapport['sous_dossiers_crees']:
            print(f"  ✓ {sd}")
        
        print("\n🎯 Catégories détectées:")
        for dossier, categories in self.rapport['categories_detectees'].items():
            print(f"\n  {dossier}:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                pct = (count / sum(categories.values())) * 100
                print(f"    - {cat}: {count} emails ({pct:.1f}%)")
        
        print("\n" + "="*60)
        print("🚀 PROCHAINES ÉTAPES:")
        print("="*60)
        print("\n1. Vérifier les sous-dossiers dans ProtonMail")
        print("2. Ajuster manuellement les emails mal classés")
        print("3. Lancer la passe d'apprentissage:")
        print("\n   python scripts/sync_and_learn.py\n")
    
    def run(self):
        """Exécuter le pré-tri"""
        print("\n" + "="*60)
        print("🤖 PRÉ-TRI AUTOMATIQUE - Folders/2025 et Gmail")
        print("="*60 + "\n")
        
        if not self.connecter():
            return False
        
        try:
            # Analyser Folders/2025
            analyse_2025 = self.analyser_dossier('Folders/2025')
            if analyse_2025:
                self.rapport['dossiers_analyses'].append('Folders/2025')
                self.creer_sous_dossiers(analyse_2025)
                self.deplacer_emails(analyse_2025)
            
            # Analyser Gmail
            analyse_gmail = self.analyser_dossier('Gmail')
            if analyse_gmail:
                self.rapport['dossiers_analyses'].append('Gmail')
                self.creer_sous_dossiers(analyse_gmail)
                self.deplacer_emails(analyse_gmail)
            
            # Sauvegarder le rapport
            self.sauvegarder_rapport()
            
            # Afficher le résumé
            self.afficher_resume()
            
            return True
        
        finally:
            if self.mail:
                self.mail.close()
                self.mail.logout()

if __name__ == "__main__":
    pretri = PreTriAutomatique()
    success = pretri.run()
    sys.exit(0 if success else 1)
