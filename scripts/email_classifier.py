#!/usr/bin/env python3
# ============================================================================
# EMAIL CLASSIFIER - ProtonLumoAI
# Système de classification intelligent avec Lumo et apprentissage continu
# ============================================================================

import os
import json
import subprocess
import requests
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import pickle
import re

from loguru import logger
from pydantic import BaseModel, Field

# --- CONFIGURATION LOGGING ---
LOG_DIR = Path(os.getenv("PROTON_LUMO_LOGS", "~/ProtonLumoAI/logs")).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(LOG_DIR / "classifier.log", rotation="10 MB", retention="7 days")

# --- MODÈLES DE DONNÉES ---
class EmailCategory(BaseModel):
    """Représentation d'une catégorie d'email"""
    name: str
    folder: str
    keywords: List[str] = Field(default_factory=list)
    confidence_threshold: float = 0.6
    priority: int = 0  # Plus élevé = plus prioritaire
    description: str = ""


class ClassificationResult(BaseModel):
    """Résultat de classification d'un email"""
    email_id: str
    subject: str
    category: str
    confidence: float
    method: str  # "lumo", "keyword", "fallback"
    timestamp: str
    explanation: str = ""


class TrainingExample(BaseModel):
    """Exemple d'entraînement pour amélioration continue"""
    email_id: str
    subject: str
    body: str
    category: str
    user_corrected: bool = False
    timestamp: str
    feedback: str = ""


# --- CATÉGORIES PAR DÉFAUT ---
DEFAULT_CATEGORIES = {
    "SPAM": EmailCategory(
        name="SPAM",
        folder="Spam",
        keywords=["unsubscribe", "click here", "limited time", "act now", "free money"],
        confidence_threshold=0.7,
        priority=1,
        description="Emails non sollicités et publicités"
    ),
    "VENTE": EmailCategory(
        name="VENTE",
        folder="Achats",
        keywords=["solde", "promo", "offrir", "%", "commander", "panier", "livraison", "code promo"],
        confidence_threshold=0.65,
        priority=2,
        description="Emails commerciaux et offres d'achat"
    ),
    "BANQUE": EmailCategory(
        name="BANQUE",
        folder="Administratif/Banque",
        keywords=["virement", "compte", "banque", "facture", "paiement", "transaction", "solde"],
        confidence_threshold=0.8,
        priority=3,
        description="Emails bancaires et administratifs"
    ),
    "PRO": EmailCategory(
        name="PRO",
        folder="Travail",
        keywords=["réunion", "projet", "client", "deadline", "rapport", "présentation", "meeting"],
        confidence_threshold=0.7,
        priority=4,
        description="Emails professionnels"
    ),
    "URGENT": EmailCategory(
        name="URGENT",
        folder="À traiter",
        keywords=["urgent", "asap", "important", "action requise", "immédiat"],
        confidence_threshold=0.75,
        priority=5,
        description="Emails marqués comme urgents"
    ),
    "VOYAGES": EmailCategory(
        name="VOYAGES",
        folder="Voyages",
        keywords=["billet", "train", "vol", "booking", "hôtel", "réservation", "itinéraire"],
        confidence_threshold=0.7,
        priority=2,
        description="Confirmations et informations de voyage"
    ),
    "SOCIAL": EmailCategory(
        name="SOCIAL",
        folder="Réseaux sociaux",
        keywords=["like", "comment", "follow", "share", "mention", "notification", "friend request"],
        confidence_threshold=0.65,
        priority=1,
        description="Notifications des réseaux sociaux"
    ),
    "NEWSLETTER": EmailCategory(
        name="NEWSLETTER",
        folder="Newsletters",
        keywords=["newsletter", "weekly", "monthly", "digest", "subscribe", "unsubscribe"],
        confidence_threshold=0.7,
        priority=1,
        description="Newsletters et digests"
    ),
}


class EmailClassifier:
    """Système de classification intelligent avec Lumo"""

    def __init__(self, config_dir: Optional[str] = None, use_lumo: bool = True):
        """
        Initialise le classifier
        
        Args:
            config_dir: Répertoire de configuration
            use_lumo: Utiliser Lumo CLI si disponible
        """
        self.config_dir = Path(config_dir or os.getenv("PROTON_LUMO_CONFIG", "~/ProtonLumoAI/config")).expanduser()
        self.data_dir = Path(os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")).expanduser()
        self.models_dir = self.data_dir / "models"
        self.training_dir = self.data_dir / "training"
        
        # Créer les répertoires
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.training_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_lumo = use_lumo or bool(os.getenv("PERPLEXITY_API_KEY"))
        self.categories = self._load_categories()
        self.training_examples = self._load_training_examples()
        self.classification_history = []
        
        logger.info(f"Classifier initialisé (Lumo: {self.use_lumo})")

    def _check_lumo_available(self) -> bool:
        """Vérifie si Lumo CLI est disponible"""
        try:
            result = subprocess.run(["lumo", "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                logger.info("Lumo CLI détecté")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        logger.warning("Lumo CLI non disponible, utilisation du fallback")
        return False

    def _load_categories(self) -> Dict[str, EmailCategory]:
        """Charge les catégories depuis le fichier de config ou utilise les défauts"""
        categories_file = self.config_dir / "categories.json"
        
        if categories_file.exists():
            try:
                with open(categories_file) as f:
                    data = json.load(f)
                    return {k: EmailCategory(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Erreur chargement catégories : {e}")
        
        # Sauvegarder les catégories par défaut
        self._save_categories(DEFAULT_CATEGORIES)
        return DEFAULT_CATEGORIES

    def _save_categories(self, categories: Dict[str, EmailCategory]):
        """Sauvegarde les catégories"""
        categories_file = self.config_dir / "categories.json"
        with open(categories_file, "w") as f:
            json.dump({k: v.dict() for k, v in categories.items()}, f, indent=2, ensure_ascii=False)

    def _load_training_examples(self) -> List[TrainingExample]:
        """Charge les exemples d'entraînement"""
        training_file = self.training_dir / "examples.jsonl"
        examples = []
        
        if training_file.exists():
            try:
                with open(training_file) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            examples.append(TrainingExample(**data))
            except Exception as e:
                logger.error(f"Erreur chargement exemples : {e}")
        
        return examples

    def _save_training_examples(self):
        """Sauvegarde les exemples d'entraînement"""
        training_file = self.training_dir / "examples.jsonl"
        with open(training_file, "w") as f:
            for example in self.training_examples:
                f.write(example.model_dump_json() + "\n")

    def classify_with_lumo(self, subject: str, body: str) -> Tuple[str, float, str]:
        """
        Classification via Perplexity API (remplace Lumo CLI)
        """
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            logger.warning("Clé API Perplexity manquante. Configurez PERPLEXITY_API_KEY dans .env")
            return None, 0.0, ""

        try:
            # Préparation du prompt pour l'IA
            categories_list = ", ".join(self.categories.keys())
            prompt = (
                f"Analyze this email and classify it into exactly one of these categories: {categories_list}.\n"
                f"Subject: {subject}\n"
                f"Body: {body[:1000]}\n\n"
                "Return ONLY a JSON object with this format: {\\\"category\\\": \\\"CATEGORY_NAME\\\", \\\"confidence\\\": 0.9, \\\"explanation\\\": \\\"short reason\\\"}"
            )

            # Appel API Perplexity
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "sonar-pro", # Ou "sonar" pour moins cher
                "messages": [
                    {"role": "system", "content": "You are a helpful email classification assistant that outputs only JSON."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result_json = response.json()
                content = result_json["choices"][0]["message"]["content"]
                
                # Nettoyage du Markdown json ```json ... ``` si présent
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                output = json.loads(content)
                
                category = output.get("category", "UNKNOWN").upper()
                confidence = float(output.get("confidence", 0.0))
                explanation = output.get("explanation", "")
                
                logger.info(f"✓ Perplexity: {category} ({confidence:.2f})")
                return category, confidence, explanation
            else:
                logger.error(f"Erreur API Perplexity: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Erreur appel Perplexity: {e}")
        
        return None, 0.0, ""

    def classify_with_keywords(self, subject: str, body: str) -> Tuple[str, float, str]:
        """
        Classification par mots-clés (fallback)
        
        Returns:
            (category, confidence, explanation)
        """
        content = f"{subject} {body}".lower()
        scores = {}
        
        for cat_name, category in self.categories.items():
            # Compter les correspondances
            matches = sum(1 for keyword in category.keywords if keyword.lower() in content)
            
            if matches > 0:
                # Score basé sur le nombre de correspondances
                confidence = min(0.99, (matches / max(len(category.keywords), 1)) * 0.8)
                scores[cat_name] = (confidence, f"{matches} mot(s)-clé trouvé(s)")
        
        if scores:
            best_category = max(scores.items(), key=lambda x: x[1][0])
            return best_category[0], best_category[1][0], best_category[1][1]
        
        return "UNKNOWN", 0.0, "Aucune correspondance"

    def classify(self, email_id: str, subject: str, body: str) -> ClassificationResult:
        """
        Classifie un email avec stratégie multi-niveaux
        
        1. Essayer Lumo si disponible
        2. Fallback sur mots-clés
        3. Fallback sur UNKNOWN
        """
        logger.info(f"Classification de l'email: {email_id} - {subject[:50]}")
        
        category = None
        confidence = 0.0
        explanation = ""
        method = "fallback"
        
        # Étape 1 : Lumo
        if self.use_lumo:
            category, confidence, explanation = self.classify_with_lumo(subject, body)
            if category and confidence >= 0.5:
                method = "lumo"
                logger.info(f"✓ Lumo: {category} ({confidence:.2f})")
        
        # Étape 2 : Mots-clés (si Lumo échoue ou est incertain)
        if not category or confidence < 0.5:
            category, confidence, explanation = self.classify_with_keywords(subject, body)
            method = "keyword"
        
        # Étape 3 : Fallback final
        if not category or confidence < 0.1:
            category = "UNKNOWN"
            confidence = 0.0
            explanation = "Aucune classification possible"
            method = "fallback"

        result = ClassificationResult(
            email_id=email_id,
            subject=subject,
            category=category,
            confidence=confidence,
            method=method,
            timestamp=datetime.now().isoformat(),
            explanation=explanation
        )
        
        self.classification_history.append(result)
        return result

    def add_training_example(self, email_id: str, subject: str, body: str, category: str, user_corrected: bool = False):
        """Ajoute un nouvel exemple d'entraînement"""
        example = TrainingExample(
            email_id=email_id,
            subject=subject,
            body=body,
            category=category,
            user_corrected=user_corrected,
            timestamp=datetime.now().isoformat()
        )
        self.training_examples.append(example)
        self._save_training_examples()
        logger.info(f"Nouvel exemple d'entraînement ajouté pour la catégorie {category}")

    def train_lumo(self, category: str, texts: List[str]):
        """(Ré)entraîne un modèle Lumo pour une catégorie spécifique"""
        if not self.use_lumo:
            return

        # Cette fonction est un placeholder car Lumo CLI ne supporte pas le réentraînement via API
        # Dans un vrai scénario, on pourrait appeler une API de réentraînement
        logger.info(f"Réentraînement Lumo pour {category} avec {len(texts)} exemples...")
