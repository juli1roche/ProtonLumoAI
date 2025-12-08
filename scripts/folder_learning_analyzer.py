#!/usr/bin/env python3
# ============================================================================
# FOLDER LEARNING ANALYZER - ProtonLumoAI v1.3.0
# Apprentissage intelligent par analyse des dossiers existants
# Extrait patterns et associations à partir des derniers 10 emails
# ============================================================================

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict
import imaplib
import email.utils
from email.header import decode_header

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class EmailFeatures:
    """Extraction des caractéristiques d'un email"""
    subject: str
    sender: str
    sender_domain: str
    recipient: str
    body_preview: str  # 500 premiers caractères
    keywords: Set[str]
    signature_text: str
    has_attachment: bool
    word_count: int
    sentiment_indicators: Dict[str, int]  # positive, negative, urgent, financial
    

@dataclass
class FolderPattern:
    """Pattern appris d'un dossier"""
    folder_name: str
    category: str  # La catégorie que ce dossier représente
    
    # Patterns identifiés
    common_senders: Dict[str, int]  # {email: count}
    common_domains: Dict[str, int]  # {domain: count}
    common_keywords: Dict[str, int]  # {keyword: count}
    common_subjects_patterns: List[str]  # Patterns de sujets
    signature_patterns: List[str]  # Signatures identifiées
    body_patterns: Dict[str, int]  # {pattern: count}
    
    # Statistiques
    email_count: int
    avg_word_count: float
    urgency_score: float  # 0-1
    formality_score: float  # 0-1 (0=casual, 1=formal)
    
    # Confiance
    confidence: float  # 0-1, basé sur nb d'emails analysés
    last_updated: str


class FolderLearningAnalyzer:
    """
    Analyse les dossiers existants pour extraire patterns et apprendre
    la classification automatiquement.
    """
    
    def __init__(self):
        self.data_dir = Path(os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.learning_dir = self.data_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        self.patterns_file = self.learning_dir / "folder_patterns.json"
        self.feature_file = self.learning_dir / "extracted_features.jsonl"
        self.associations_file = self.learning_dir / "content_associations.json"
        
        self.patterns: Dict[str, FolderPattern] = {}
        self.load_existing_patterns()
        
        # Regex patterns pour extraction
        self.urgent_keywords = {
            'urgent', 'important', 'critical', 'asap', 'immediate', 'vital',
            'urgent', 'urgent', 'vite', 'rapidement', 'critique', 'capital'
        }
        
        self.formal_indicators = {
            'dear', 'sincerely', 'regards', 'respectfully',
            'cher', 'chère', 'cordialement', 'respectueusement'
        }
        
        self.financial_keywords = {
            'payment', 'invoice', 'amount', 'transfer', 'cost', 'price',
            'budget', 'finance', 'payment', 'facture', 'montant', 'virement'
        }
        
        logger.info("🧠 FolderLearningAnalyzer initialized")
    
    def load_existing_patterns(self):
        """Charge les patterns existants"""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Reconvertir en FolderPattern objects
                    self.patterns = {k: FolderPattern(**v) for k, v in data.items()}
                    logger.info(f"✓ Loaded {len(self.patterns)} existing patterns")
            except Exception as e:
                logger.error(f"Error loading patterns: {e}")
    
    def save_patterns(self):
        """Sauvegarde les patterns appris"""
        try:
            patterns_dict = {k: asdict(v) for k, v in self.patterns.items()}
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(patterns_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Saved {len(self.patterns)} patterns")
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")
    
    def extract_features(self, email_data: dict) -> Optional[EmailFeatures]:
        """
        Extrait les caractéristiques d'un email pour analyse
        
        Args:
            email_data: {'subject': str, 'sender': str, 'body': str, 'has_attachment': bool}
        """
        try:
            subject = email_data.get('subject', 'Unknown')
            sender = email_data.get('sender', 'Unknown')
            body = email_data.get('body', '')[:500]  # 500 chars preview
            has_attachment = email_data.get('has_attachment', False)
            
            # Extraction du domaine expéditeur
            sender_domain = 'unknown'
            if '@' in sender:
                sender_domain = sender.split('@')[1].lower()
            
            # Extraction des keywords
            keywords = self._extract_keywords(subject, body)
            
            # Extraction de la signature
            signature = self._extract_signature(body)
            
            # Indicateurs de sentiment
            sentiment = self._analyze_sentiment(subject, body)
            
            # Compte de mots
            word_count = len(body.split())
            
            return EmailFeatures(
                subject=subject,
                sender=sender,
                sender_domain=sender_domain,
                recipient='',  # À récupérer depuis headers
                body_preview=body,
                keywords=keywords,
                signature_text=signature,
                has_attachment=has_attachment,
                word_count=word_count,
                sentiment_indicators=sentiment
            )
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _extract_keywords(self, subject: str, body: str, top_n: int = 20) -> Set[str]:
        """Extrait les keywords significatifs"""
        # Stop words français et anglais
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'dans', 'sur', 'à', 'pour'
        }
        
        # Tokeniser et nettoyer
        text = (subject + ' ' + body).lower()
        words = re.findall(r'\b[a-zàâäéèêëïîôöçù]{3,}\b', text)
        
        # Filtrer stop words et compter
        keywords = set()
        for word in words:
            if word not in stop_words and len(word) > 2:
                keywords.add(word)
        
        return keywords
    
    def _extract_signature(self, body: str) -> str:
        """Extrait la signature de l'email"""
        # Patterns courants de signature
        sig_patterns = [
            r'(?:^|\n)[-=]{2,}.*?(?:\Z|\n)',  # Séparateur
            r'(?:^|\n)(?:Best regards|Sincerely|Cordialement|Cdt|BR|--)[\s\S]*?(?:\Z|\n)',
            r'(?:^|\n)[A-Z][a-z]+ [A-Z][a-z]+[\s\S]*?(?:\Z|\n)',  # Nom + infos
        ]
        
        for pattern in sig_patterns:
            match = re.search(pattern, body, re.MULTILINE)
            if match:
                return match.group(0)[:200]  # Max 200 chars
        
        return ''
    
    def _analyze_sentiment(self, subject: str, body: str) -> Dict[str, int]:
        """Analyse les indicateurs de sentiment"""
        text = (subject + ' ' + body).lower()
        
        indicators = {
            'urgent': 0,
            'positive': 0,
            'negative': 0,
            'financial': 0
        }
        
        # Urgent
        for keyword in self.urgent_keywords:
            indicators['urgent'] += text.count(keyword)
        
        # Financial
        for keyword in self.financial_keywords:
            indicators['financial'] += text.count(keyword)
        
        # Positive indicators
        positive = {'thanks', 'congratulations', 'great', 'excellent', 'merci', 'félicitations'}
        for word in positive:
            indicators['positive'] += text.count(word)
        
        # Negative indicators
        negative = {'problem', 'issue', 'error', 'failed', 'problème', 'erreur', 'échoué'}
        for word in negative:
            indicators['negative'] += text.count(word)
        
        return indicators
    
    def analyze_folder(self, folder_name: str, emails_data: List[dict], 
                      expected_category: str = None) -> Optional[FolderPattern]:
        """
        Analyse les 10 derniers emails d'un dossier pour extraire patterns
        
        Args:
            folder_name: Nom du dossier à analyser
            emails_data: Liste de dicts avec subject, sender, body, has_attachment
            expected_category: Catégorie attendue pour ce dossier (optionnel)
        
        Returns:
            FolderPattern ou None
        """
        logger.info(f"📊 Analyzing folder: {folder_name}")
        
        if not emails_data or len(emails_data) == 0:
            logger.warning(f"No emails to analyze in {folder_name}")
            return None
        
        # Limiter à 10 emails
        emails_data = emails_data[:10]
        
        # Extraire features
        features_list = []
        for email_data in emails_data:
            features = self.extract_features(email_data)
            if features:
                features_list.append(features)
        
        if not features_list:
            logger.warning(f"Could not extract features from {folder_name}")
            return None
        
        # Analyser les patterns
        common_senders = defaultdict(int)
        common_domains = defaultdict(int)
        all_keywords = defaultdict(int)
        subject_patterns = []
        signatures = []
        body_patterns = defaultdict(int)
        
        total_word_count = 0
        total_urgency = 0
        total_formality = 0
        
        for features in features_list:
            # Senders
            common_senders[features.sender] += 1
            common_domains[features.sender_domain] += 1
            
            # Keywords
            for kw in features.keywords:
                all_keywords[kw] += 1
            
            # Subjects
            subject_patterns.append(features.subject[:50])  # First 50 chars
            
            # Signatures
            if features.signature_text:
                signatures.append(features.signature_text[:100])
            
            # Word count
            total_word_count += features.word_count
            
            # Urgency
            urgency_count = features.sentiment_indicators.get('urgent', 0)
            total_urgency += urgency_count
            
            # Formality (présence de formal indicators)
            formal_count = sum(1 for word in self.formal_indicators if word in features.body_preview.lower())
            total_formality += formal_count
        
        # Calculer scores
        email_count = len(features_list)
        avg_word_count = total_word_count / email_count if email_count > 0 else 0
        urgency_score = min(total_urgency / email_count, 1.0) if email_count > 0 else 0
        formality_score = min(total_formality / (email_count * 3), 1.0) if email_count > 0 else 0
        
        # Confidence basée sur nombre d'emails
        confidence = min(email_count / 10, 1.0)  # Max confidence at 10 emails
        
        # Créer le pattern
        pattern = FolderPattern(
            folder_name=folder_name,
            category=expected_category or 'UNKNOWN',
            common_senders=dict(common_senders),
            common_domains=dict(common_domains),
            common_keywords=dict(sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:20]),
            common_subjects_patterns=subject_patterns[:5],
            signature_patterns=list(set(signatures))[:3],
            body_patterns=dict(sorted(body_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
            email_count=email_count,
            avg_word_count=avg_word_count,
            urgency_score=urgency_score,
            formality_score=formality_score,
            confidence=confidence,
            last_updated=datetime.now().isoformat()
        )
        
        self.patterns[folder_name] = pattern
        
        logger.info(
            f"✓ Folder pattern extracted: {folder_name} "
            f"({email_count} emails, confidence: {confidence:.2%})"
        )
        logger.debug(
            f"  Keywords: {', '.join(list(pattern.common_keywords.keys())[:5])}\n"
            f"  Senders: {', '.join(list(pattern.common_senders.keys())[:3])}\n"
            f"  Urgency: {urgency_score:.2%}, Formality: {formality_score:.2%}"
        )
        
        return pattern
    
    def generate_learning_rules(self) -> Dict[str, List[str]]:
        """
        Génère des règles de filtrage basées sur les patterns appris
        
        Returns:
            Dict avec règles par catégorie
        """
        rules = defaultdict(list)
        
        for folder_name, pattern in self.patterns.items():
            category = pattern.category
            
            # Règle 1: Expéditeurs connus
            if pattern.common_senders:
                top_sender = max(pattern.common_senders.items(), key=lambda x: x[1])[0]
                if pattern.common_senders[top_sender] >= 3:  # Au moins 3 emails
                    rules[category].append(
                        f"FROM:{top_sender} -> {category}"
                    )
            
            # Règle 2: Domaines connus
            if pattern.common_domains:
                top_domain = max(pattern.common_domains.items(), key=lambda x: x[1])[0]
                if pattern.common_domains[top_domain] >= 4:
                    rules[category].append(
                        f"DOMAIN:{top_domain} -> {category}"
                    )
            
            # Règle 3: Keywords
            if pattern.common_keywords:
                top_keywords = sorted(pattern.common_keywords.items(), 
                                    key=lambda x: x[1], reverse=True)[:3]
                for keyword, count in top_keywords:
                    if count >= 2:
                        rules[category].append(
                            f"KEYWORD:{keyword} -> {category}"
                        )
            
            # Règle 4: Urgence
            if pattern.urgency_score > 0.5:
                rules[category].append(
                    f"URGENT_CONTENT -> {category} (confidence: {pattern.urgency_score:.0%})"
                )
            
            # Règle 5: Formalité
            if pattern.formality_score > 0.6:
                rules[category].append(
                    f"FORMAL_CONTENT -> {category} (formality: {pattern.formality_score:.0%})"
                )
        
        return dict(rules)
    
    def generate_report(self) -> str:
        """
        Génère un rapport d'apprentissage
        """
        report = []
        report.append("═" * 80)
        report.append("🧠 FOLDER LEARNING ANALYSIS REPORT - ProtonLumoAI v1.3.0")
        report.append("═" * 80)
        report.append(f"\nAnalyzed: {len(self.patterns)} folders")
        report.append(f"Updated: {datetime.now().isoformat()}\n")
        
        for folder_name, pattern in sorted(self.patterns.items()):
            report.append(f"\n📁 {folder_name} ({pattern.category})")
            report.append(f"   Emails analyzed: {pattern.email_count}/10 (confidence: {pattern.confidence:.0%})")
            report.append(f"   Avg words/email: {pattern.avg_word_count:.0f}")
            report.append(f"   Urgency score: {pattern.urgency_score:.0%}")
            report.append(f"   Formality score: {pattern.formality_score:.0%}")
            
            if pattern.common_senders:
                top_senders = sorted(pattern.common_senders.items(), 
                                   key=lambda x: x[1], reverse=True)[:2]
                report.append(f"   Top senders: {', '.join([f'{s[0]} ({s[1]}x)' for s in top_senders])}")
            
            if pattern.common_keywords:
                top_kw = sorted(pattern.common_keywords.items(), 
                              key=lambda x: x[1], reverse=True)[:5]
                report.append(f"   Keywords: {', '.join([f'{k[0]} ({k[1]}x)' for k in top_kw])}")
        
        # Règles générées
        rules = self.generate_learning_rules()
        if rules:
            report.append("\n" + "─" * 80)
            report.append("📋 GENERATED FILTERING RULES:\n")
            for category, category_rules in sorted(rules.items()):
                report.append(f"  [{category}]")
                for rule in category_rules[:3]:  # Max 3 rules par catégorie
                    report.append(f"    → {rule}")
        
        report.append("\n" + "═" * 80)
        return "\n".join(report)


if __name__ == "__main__":
    analyzer = FolderLearningAnalyzer()
    print(analyzer.generate_report())
