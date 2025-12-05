#!/usr/bin/env python3
# ============================================================================
# ADAPTIVE LEARNER - ProtonLumoAI
# Système d'apprentissage adaptatif avec détection de feedback utilisateur
# ============================================================================

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from loguru import logger


class AdaptiveLearner:
    """
    Détecte les déplacements manuels d'emails et apprend des patterns utilisateur.
    Utilise few-shot learning pour améliorer les prompts Perplexity.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")).expanduser()
        self.learning_dir = self.data_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        # Fichiers de persistance
        self.corrections_file = self.learning_dir / "user_corrections.jsonl"
        self.patterns_file = self.learning_dir / "learned_patterns.json"
        self.email_signatures_file = self.learning_dir / "email_signatures.json"
        
        # Chargement des données
        self.corrections: List[Dict] = self._load_corrections()
        self.learned_patterns: Dict = self._load_patterns()
        self.email_signatures: Dict[str, str] = self._load_email_signatures()
        
        logger.info(f"AdaptiveLearner initialisé: {len(self.corrections)} corrections, {len(self.learned_patterns)} patterns")

    def _load_corrections(self) -> List[Dict]:
        """Charge l'historique des corrections utilisateur"""
        corrections = []
        if self.corrections_file.exists():
            try:
                with open(self.corrections_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            corrections.append(json.loads(line))
                logger.debug(f"✓ {len(corrections)} corrections chargées")
            except Exception as e:
                logger.error(f"Erreur chargement corrections: {e}")
        return corrections

    def _load_patterns(self) -> Dict:
        """Charge les patterns appris"""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement patterns: {e}")
        return {
            'sender_rules': {},      # email_sender -> category
            'subject_keywords': {},  # keyword -> category
            'domain_rules': {},      # @domain -> category
            'content_patterns': {}   # pattern -> category
        }

    def _load_email_signatures(self) -> Dict[str, str]:
        """Charge les signatures d'emails (hash du contenu pour détection)"""
        if self.email_signatures_file.exists():
            try:
                with open(self.email_signatures_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement signatures: {e}")
        return {}

    def _save_corrections(self):
        """Sauvegarde les corrections"""
        try:
            with open(self.corrections_file, 'w') as f:
                for correction in self.corrections:
                    f.write(json.dumps(correction, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Erreur sauvegarde corrections: {e}")

    def _save_patterns(self):
        """Sauvegarde les patterns appris"""
        try:
            with open(self.patterns_file, 'w') as f:
                json.dump(self.learned_patterns, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde patterns: {e}")

    def _save_email_signatures(self):
        """Sauvegarde les signatures d'emails"""
        try:
            with open(self.email_signatures_file, 'w') as f:
                json.dump(self.email_signatures, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde signatures: {e}")

    def _create_email_signature(self, subject: str, sender: str, body_preview: str) -> str:
        """Crée une signature unique pour un email"""
        import hashlib
        content = f"{subject}|{sender}|{body_preview[:200]}"
        return hashlib.md5(content.encode()).hexdigest()

    def register_classification(self, email_id: str, subject: str, sender: str, body_preview: str, 
                               predicted_category: str, actual_folder: str):
        """
        Enregistre une classification avec sa destination réelle.
        Permet de détecter si l'utilisateur a déplacé l'email.
        """
        signature = self._create_email_signature(subject, sender, body_preview)
        self.email_signatures[signature] = json.dumps({
            'email_id': email_id,
            'subject': subject,
            'sender': sender,
            'predicted_category': predicted_category,
            'actual_folder': actual_folder,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False)
        self._save_email_signatures()

    def detect_manual_move(self, mailbox, email_id: str, subject: str, sender: str, 
                          body_preview: str, current_folder: str, predicted_category: str) -> Optional[str]:
        """
        Détecte si un email a été déplacé manuellement par l'utilisateur.
        Retourne la catégorie corrigée si détectée, None sinon.
        """
        signature = self._create_email_signature(subject, sender, body_preview)
        
        if signature in self.email_signatures:
            try:
                stored_data = json.loads(self.email_signatures[signature])
                original_folder = stored_data.get('actual_folder')
                predicted = stored_data.get('predicted_category')
                
                # Vérifier si l'email a été déplacé
                if current_folder != original_folder:
                    logger.info(f"👁️  Déplacement manuel détecté: '{subject[:30]}...' de {original_folder} → {current_folder}")
                    
                    # Apprendre de cette correction
                    self.learn_from_correction(
                        email_id=email_id,
                        subject=subject,
                        sender=sender,
                        body_preview=body_preview,
                        wrong_category=predicted,
                        correct_category=self._folder_to_category(current_folder)
                    )
                    
                    return self._folder_to_category(current_folder)
            except Exception as e:
                logger.error(f"Erreur détection déplacement: {e}")
        
        return None

    def _folder_to_category(self, folder: str) -> str:
        """Convertit un nom de dossier en catégorie"""
        # Mapping simple pour l'instant
        folder_lower = folder.lower()
        if 'travail' in folder_lower or 'work' in folder_lower:
            return 'PRO'
        elif 'newsletter' in folder_lower:
            return 'NEWSLETTER'
        elif 'voyage' in folder_lower or 'travel' in folder_lower:
            return 'VOYAGES'
        elif 'banque' in folder_lower or 'bank' in folder_lower:
            return 'BANQUE'
        elif 'achat' in folder_lower or 'shop' in folder_lower:
            return 'VENTE'
        elif 'social' in folder_lower:
            return 'SOCIAL'
        elif 'urgent' in folder_lower:
            return 'URGENT'
        elif 'spam' in folder_lower:
            return 'SPAM'
        return 'UNKNOWN'

    def learn_from_correction(self, email_id: str, subject: str, sender: str, 
                             body_preview: str, wrong_category: str, correct_category: str):
        """
        Apprend d'une correction utilisateur et met à jour les patterns.
        """
        correction = {
            'email_id': email_id,
            'subject': subject,
            'sender': sender,
            'body_preview': body_preview[:200],
            'wrong_category': wrong_category,
            'correct_category': correct_category,
            'timestamp': datetime.now().isoformat()
        }
        
        self.corrections.append(correction)
        self._save_corrections()
        
        # Extraire et apprendre les patterns
        self._extract_patterns(correction)
        
        logger.success(f"✓ Apprentissage: '{subject[:30]}...' {wrong_category} → {correct_category}")

    def _extract_patterns(self, correction: Dict):
        """
        Extrait des patterns d'une correction et met à jour les règles.
        """
        sender = correction['sender']
        subject = correction['subject'].lower()
        correct_category = correction['correct_category']
        
        # 1. Règle par expéditeur exact
        if sender:
            if sender not in self.learned_patterns['sender_rules']:
                self.learned_patterns['sender_rules'][sender] = correct_category
                logger.debug(f"  ➕ Règle expéditeur: {sender} → {correct_category}")
        
        # 2. Règle par domaine
        if sender and '@' in sender:
            domain = '@' + sender.split('@')[1]
            if domain not in self.learned_patterns['domain_rules']:
                # Vérifier si c'est cohérent avec d'autres emails du même domaine
                domain_corrections = [c for c in self.corrections if domain in c['sender']]
                if len(domain_corrections) >= 2:  # Au moins 2 corrections du même domaine
                    categories = [c['correct_category'] for c in domain_corrections]
                    if categories.count(correct_category) / len(categories) > 0.7:  # 70% de confiance
                        self.learned_patterns['domain_rules'][domain] = correct_category
                        logger.debug(f"  ➕ Règle domaine: {domain} → {correct_category}")
        
        # 3. Mots-clés dans le sujet
        words = [w for w in subject.split() if len(w) > 4]  # Mots de plus de 4 lettres
        for word in words[:5]:  # Max 5 mots les plus significatifs
            if word not in self.learned_patterns['subject_keywords']:
                # Vérifier la fréquence de ce mot dans les corrections
                word_corrections = [c for c in self.corrections if word in c['subject'].lower()]
                if len(word_corrections) >= 2:
                    categories = [c['correct_category'] for c in word_corrections]
                    if categories.count(correct_category) / len(categories) > 0.7:
                        self.learned_patterns['subject_keywords'][word] = correct_category
                        logger.debug(f"  ➕ Mot-clé sujet: '{word}' → {correct_category}")
        
        self._save_patterns()

    def get_few_shot_examples(self, max_examples: int = 5) -> List[Dict]:
        """
        Retourne les meilleurs exemples pour few-shot learning.
        Sélectionne les corrections les plus récentes et diversifiées.
        """
        if not self.corrections:
            return []
        
        # Trier par date (plus récents d'abord)
        sorted_corrections = sorted(
            self.corrections,
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
        # Sélectionner des exemples variés par catégorie
        examples_by_category = defaultdict(list)
        for correction in sorted_corrections:
            cat = correction['correct_category']
            if len(examples_by_category[cat]) < 2:  # Max 2 par catégorie
                examples_by_category[cat].append(correction)
        
        # Aplatir et limiter
        examples = []
        for cat_examples in examples_by_category.values():
            examples.extend(cat_examples)
        
        return examples[:max_examples]

    def build_enhanced_prompt(self, base_categories: List[str], subject: str, body: str) -> str:
        """
        Construit un prompt enrichi avec few-shot learning basé sur les corrections.
        """
        few_shot_examples = self.get_few_shot_examples(max_examples=5)
        
        prompt_parts = []
        
        # Section few-shot si disponible
        if few_shot_examples:
            prompt_parts.append("Here are examples of past user corrections you should learn from:")
            for i, example in enumerate(few_shot_examples, 1):
                prompt_parts.append(
                    f"Example {i}: Subject='{example['subject'][:50]}', "
                    f"From={example['sender']}, Correct Category={example['correct_category']}"
                )
            prompt_parts.append("")
        
        # Règles apprises
        if self.learned_patterns['sender_rules'] or self.learned_patterns['domain_rules']:
            prompt_parts.append("Important rules learned from user behavior:")
            
            if self.learned_patterns['sender_rules']:
                prompt_parts.append("- Sender-specific rules:")
                for sender, cat in list(self.learned_patterns['sender_rules'].items())[:3]:
                    prompt_parts.append(f"  • Emails from {sender} should be categorized as {cat}")
            
            if self.learned_patterns['domain_rules']:
                prompt_parts.append("- Domain-specific rules:")
                for domain, cat in list(self.learned_patterns['domain_rules'].items())[:3]:
                    prompt_parts.append(f"  • Emails from {domain} should be categorized as {cat}")
            
            prompt_parts.append("")
        
        # Prompt principal
        prompt_parts.append(f"Now classify this new email into one of: {', '.join(base_categories)}")
        prompt_parts.append(f"Subject: {subject}")
        prompt_parts.append(f"Body: {body[:1000]}")
        
        return "\n".join(prompt_parts)

    def predict_from_rules(self, sender: str, subject: str) -> Optional[Tuple[str, float]]:
        """
        Prédit la catégorie basée sur les règles apprises (avant Perplexity).
        Retourne (category, confidence) ou None.
        """
        # 1. Règle par expéditeur exact (confiance haute)
        if sender in self.learned_patterns['sender_rules']:
            category = self.learned_patterns['sender_rules'][sender]
            logger.info(f"🎯 Règle apprise (expéditeur): {sender} → {category}")
            return (category, 0.95)
        
        # 2. Règle par domaine (confiance moyenne-haute)
        if sender and '@' in sender:
            domain = '@' + sender.split('@')[1]
            if domain in self.learned_patterns['domain_rules']:
                category = self.learned_patterns['domain_rules'][domain]
                logger.info(f"🎯 Règle apprise (domaine): {domain} → {category}")
                return (category, 0.85)
        
        # 3. Mots-clés dans le sujet (confiance moyenne)
        subject_lower = subject.lower()
        for keyword, category in self.learned_patterns['subject_keywords'].items():
            if keyword in subject_lower:
                logger.info(f"🎯 Règle apprise (mot-clé): '{keyword}' → {category}")
                return (category, 0.75)
        
        return None

    def get_stats(self) -> Dict:
        """Retourne des statistiques sur l'apprentissage"""
        return {
            'total_corrections': len(self.corrections),
            'sender_rules': len(self.learned_patterns['sender_rules']),
            'domain_rules': len(self.learned_patterns['domain_rules']),
            'subject_keywords': len(self.learned_patterns['subject_keywords']),
            'categories_learned': len(set(c['correct_category'] for c in self.corrections))
        }