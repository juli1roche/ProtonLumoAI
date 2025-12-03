#!/usr/bin/env python3
# ============================================================================
# EMAIL CLASSIFIER - ProtonLumoAI
# Système de classification intelligent avec Lumo et apprentissage continu
# ============================================================================

import os
import json
import subprocess
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
        
        self.use_lumo = use_lumo and self._check_lumo_available()
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
            json.dump({k: asdict(v) for k, v in categories.items()}, f, indent=2, ensure_ascii=False)

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
        Classification via Lumo CLI
        
        Returns:
            (category, confidence, explanation)
        """
        try:
            text_content = f"{subject}\n{body[:1000]}"
            
            # Appel Lumo CLI
            result = subprocess.run(
                ["lumo", "classify", "--text", text_content, "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    category = output.get("category", "UNKNOWN").upper()
                    confidence = float(output.get("confidence", 0.0))
                    explanation = output.get("explanation", "")
                    
                    logger.debug(f"Lumo classification: {category} ({confidence:.2f})")
                    return category, confidence, explanation
                except json.JSONDecodeError:
                    logger.warning("Réponse Lumo non-JSON")
            else:
                logger.warning(f"Erreur Lumo: {result.stderr}")
        except Exception as e:
            logger.error(f"Erreur appel Lumo: {e}")
        
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
        
        # Étape 2 : Mots-clés
        if not category or confidence < 0.5:
            kw_category, kw_confidence, kw_explanation = self.classify_with_keywords(subject, body)
            if kw_confidence > confidence:
                category = kw_category
                confidence = kw_confidence
                explanation = kw_explanation
                method = "keyword"
                logger.info(f"✓ Keyword: {category} ({confidence:.2f})")
        
        # Étape 3 : Fallback
        if not category:
            category = "UNKNOWN"
            confidence = 0.0
            method = "fallback"
            logger.info("✓ Fallback: UNKNOWN")
        
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
        """Ajoute un exemple d'entraînement"""
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
        logger.info(f"Exemple d'entraînement ajouté: {email_id} -> {category}")

    def train_lumo(self, category: str, examples: Optional[List[str]] = None):
        """Entraîne Lumo avec des exemples"""
        if not self.use_lumo:
            logger.warning("Lumo non disponible pour l'entraînement")
            return
        
        if examples is None:
            # Utiliser les exemples d'entraînement pour cette catégorie
            examples = [
                f"{ex.subject} {ex.body[:500]}"
                for ex in self.training_examples
                if ex.category == category
            ]
        
        if not examples:
            logger.warning(f"Aucun exemple pour l'entraînement de {category}")
            return
        
        try:
            for example in examples:
                result = subprocess.run(
                    ["lumo", "train", "--label", category, "--text", example],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning(f"Erreur entraînement Lumo: {result.stderr}")
            
            logger.info(f"Entraînement Lumo complété pour {category} ({len(examples)} exemples)")
        except Exception as e:
            logger.error(f"Erreur entraînement: {e}")

    def get_statistics(self) -> Dict:
        """Retourne les statistiques de classification"""
        stats = {
            "total_classifications": len(self.classification_history),
            "by_category": {},
            "by_method": {},
            "average_confidence": 0.0
        }
        
        if not self.classification_history:
            return stats
        
        # Compter par catégorie et méthode
        for result in self.classification_history:
            stats["by_category"][result.category] = stats["by_category"].get(result.category, 0) + 1
            stats["by_method"][result.method] = stats["by_method"].get(result.method, 0) + 1
        
        # Confiance moyenne
        avg_confidence = sum(r.confidence for r in self.classification_history) / len(self.classification_history)
        stats["average_confidence"] = round(avg_confidence, 3)
        
        return stats

    def export_results(self, filepath: str):
        """Exporte l'historique de classification"""
        with open(filepath, "w") as f:
            for result in self.classification_history:
                f.write(result.model_dump_json() + "\n")
        logger.info(f"Résultats exportés vers {filepath}")


if __name__ == "__main__":
    # Test
    classifier = EmailClassifier()
    
    # Test de classification
    test_email = classifier.classify(
        "test-001",
        "Offre spéciale : 50% de réduction",
        "Nous vous proposons une offre exclusive avec 50% de réduction sur tous nos produits..."
    )
    print(f"Résultat: {test_email}")
    
    # Ajouter un exemple d'entraînement
    classifier.add_training_example(
        "test-001",
        "Offre spéciale : 50% de réduction",
        "Nous vous proposons une offre exclusive...",
        "VENTE"
    )
    
    # Statistiques
    print(f"Statistiques: {classifier.get_statistics()}")
