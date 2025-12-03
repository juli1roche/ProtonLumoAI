#!/usr/bin/env python3
# ============================================================================
# TRAIN CLASSIFIER - ProtonLumoAI
# Système d'entraînement et d'auto-amélioration des filtres
# ============================================================================

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

from loguru import logger
from imap_tools import MailBox, AND

from email_classifier import EmailClassifier, TrainingExample

# --- CONFIGURATION LOGGING ---
LOG_DIR = Path(os.getenv("PROTON_LUMO_LOGS", "~/ProtonLumoAI/logs")).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(LOG_DIR / "trainer.log", rotation="10 MB", retention="7 days")

# --- CONFIGURATION IMAP ---
IMAP_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
IMAP_PORT = int(os.getenv("PROTON_BRIDGE_PORT", "1143"))
IMAP_USERNAME = os.getenv("PROTON_USERNAME", "")
IMAP_PASSWORD = os.getenv("PROTON_PASSWORD", "")

# --- DOSSIERS D'ENTRAÎNEMENT ---
TRAINING_FOLDER_ROOT = "Training"
FEEDBACK_FOLDER = "Feedback"
CORRECTION_FOLDER = "Corrections"


class TrainingManager:
    """Gère l'entraînement et l'amélioration continue"""

    def __init__(self, classifier: EmailClassifier):
        """
        Initialise le gestionnaire d'entraînement
        
        Args:
            classifier: Instance du classifier
        """
        self.classifier = classifier
        self.data_dir = Path(os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")).expanduser()
        self.stats_file = self.data_dir / "training_stats.json"
        self.performance_file = self.data_dir / "performance_metrics.json"
        
        self.stats = self._load_stats()
        self.performance = self._load_performance()

    def _load_stats(self) -> Dict:
        """Charge les statistiques d'entraînement"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement stats: {e}")
        
        return {
            "total_trained": 0,
            "by_category": defaultdict(int),
            "last_training": None,
            "training_sessions": 0
        }

    def _save_stats(self):
        """Sauvegarde les statistiques"""
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False, default=str)

    def _load_performance(self) -> Dict:
        """Charge les métriques de performance"""
        if self.performance_file.exists():
            try:
                with open(self.performance_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement performance: {e}")
        
        return {
            "accuracy": 0.0,
            "precision": defaultdict(float),
            "recall": defaultdict(float),
            "f1_score": defaultdict(float),
            "last_evaluation": None,
            "confusion_matrix": {}
        }

    def _save_performance(self):
        """Sauvegarde les métriques"""
        with open(self.performance_file, "w") as f:
            json.dump(self.performance, f, indent=2, ensure_ascii=False, default=str)

    def learn_from_training_folder(self, mailbox: MailBox) -> Dict:
        """
        Apprend depuis le dossier Training/
        Structure attendue : Training/CATEGORY/
        
        Returns:
            Statistiques d'apprentissage
        """
        logger.info("Apprentissage depuis le dossier Training...")
        stats = {
            "total_processed": 0,
            "by_category": defaultdict(int),
            "errors": 0
        }
        
        try:
            # Lister les sous-dossiers de Training
            folders = mailbox.folder.list(TRAINING_FOLDER_ROOT)
            
            for folder_info in folders:
                folder_name = folder_info['name']
                
                # Extraire la catégorie (ex: "Training/VENTE" -> "VENTE")
                if '/' not in folder_name:
                    continue
                
                category = folder_name.split('/')[-1].upper()
                
                if category not in self.classifier.categories:
                    logger.warning(f"Catégorie inconnue: {category}")
                    continue
                
                logger.info(f"Traitement de {folder_name} pour {category}...")
                
                try:
                    mailbox.folder.set(folder_name)
                    emails = list(mailbox.fetch())
                    
                    for email in emails:
                        try:
                            # Ajouter comme exemple d'entraînement
                            self.classifier.add_training_example(
                                email_id=email.uid,
                                subject=email.subject or "",
                                body=email.text or email.html or "",
                                category=category,
                                user_corrected=True  # L'utilisateur a manuellement classé
                            )
                            
                            stats["total_processed"] += 1
                            stats["by_category"][category] += 1
                            
                            # Entraîner Lumo si disponible
                            if self.classifier.use_lumo:
                                self.classifier.train_lumo(category, [f"{email.subject} {email.text or ''}"])
                            
                            # Déplacer vers le dossier final
                            target_folder = self.classifier.categories[category].folder
                            mailbox.move(email.uid, target_folder)
                            logger.debug(f"Email déplacé vers {target_folder}")
                        
                        except Exception as e:
                            logger.error(f"Erreur traitement email: {e}")
                            stats["errors"] += 1
                
                except Exception as e:
                    logger.error(f"Erreur accès dossier {folder_name}: {e}")
                    stats["errors"] += 1
        
        except Exception as e:
            logger.error(f"Erreur apprentissage: {e}")
        
        # Mettre à jour les stats
        self.stats["total_trained"] += stats["total_processed"]
        self.stats["last_training"] = datetime.now().isoformat()
        self.stats["training_sessions"] += 1
        for cat, count in stats["by_category"].items():
            self.stats["by_category"][cat] = self.stats["by_category"].get(cat, 0) + count
        self._save_stats()
        
        logger.info(f"Apprentissage terminé: {stats}")
        return stats

    def learn_from_corrections(self, mailbox: MailBox) -> Dict:
        """
        Apprend depuis les corrections manuelles
        Structure attendue : Corrections/EMAIL_ID/CORRECT_CATEGORY
        """
        logger.info("Apprentissage depuis les corrections...")
        stats = {
            "total_corrections": 0,
            "by_category": defaultdict(int),
            "errors": 0
        }
        
        try:
            mailbox.folder.set(CORRECTION_FOLDER)
            corrections = list(mailbox.fetch())
            
            for email in corrections:
                try:
                    # Parser le sujet pour extraire la catégorie correcte
                    # Format attendu: "[CATEGORY] Original Subject"
                    subject = email.subject or ""
                    
                    if subject.startswith("[") and "]" in subject:
                        category = subject.split("]")[0][1:].upper()
                        
                        if category in self.classifier.categories:
                            # Ajouter comme correction
                            self.classifier.add_training_example(
                                email_id=email.uid,
                                subject=subject,
                                body=email.text or email.html or "",
                                category=category,
                                user_corrected=True,
                                feedback="Correction manuelle"
                            )
                            
                            stats["total_corrections"] += 1
                            stats["by_category"][category] += 1
                            
                            # Entraîner Lumo
                            if self.classifier.use_lumo:
                                self.classifier.train_lumo(category, [f"{subject} {email.text or ''}"])
                            
                            # Archiver la correction
                            mailbox.move(email.uid, "Archive")
                        else:
                            logger.warning(f"Catégorie inconnue dans correction: {category}")
                    else:
                        logger.warning(f"Format de correction invalide: {subject}")
                
                except Exception as e:
                    logger.error(f"Erreur traitement correction: {e}")
                    stats["errors"] += 1
        
        except Exception as e:
            logger.error(f"Erreur accès corrections: {e}")
        
        logger.info(f"Corrections traitées: {stats}")
        return stats

    def evaluate_performance(self, test_size: int = 100) -> Dict:
        """
        Évalue la performance du classifier
        
        Args:
            test_size: Nombre d'exemples à tester
        """
        logger.info(f"Évaluation de la performance ({test_size} exemples)...")
        
        if len(self.classifier.training_examples) < test_size:
            logger.warning(f"Pas assez d'exemples ({len(self.classifier.training_examples)} < {test_size})")
            return {}
        
        # Diviser en ensemble de test
        test_examples = self.classifier.training_examples[-test_size:]
        
        correct = 0
        confusion_matrix = defaultdict(lambda: defaultdict(int))
        category_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
        
        for example in test_examples:
            result = self.classifier.classify(
                example.email_id,
                example.subject,
                example.body
            )
            
            predicted = result.category
            actual = example.category
            
            # Confusion matrix
            confusion_matrix[actual][predicted] += 1
            
            # Statistiques par catégorie
            if predicted == actual:
                correct += 1
                category_stats[actual]["tp"] += 1
            else:
                category_stats[actual]["fn"] += 1
                category_stats[predicted]["fp"] += 1
        
        # Calculer les métriques
        accuracy = correct / len(test_examples) if test_examples else 0.0
        
        metrics = {
            "accuracy": round(accuracy, 3),
            "total_tests": len(test_examples),
            "correct": correct,
            "confusion_matrix": dict(confusion_matrix),
            "by_category": {}
        }
        
        for category, stats in category_stats.items():
            tp = stats["tp"]
            fp = stats["fp"]
            fn = stats["fn"]
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            metrics["by_category"][category] = {
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1_score": round(f1, 3)
            }
        
        # Sauvegarder les métriques
        self.performance = {
            "accuracy": metrics["accuracy"],
            "precision": {cat: m["precision"] for cat, m in metrics["by_category"].items()},
            "recall": {cat: m["recall"] for cat, m in metrics["by_category"].items()},
            "f1_score": {cat: m["f1_score"] for cat, m in metrics["by_category"].items()},
            "last_evaluation": datetime.now().isoformat(),
            "confusion_matrix": metrics["confusion_matrix"]
        }
        self._save_performance()
        
        logger.info(f"Évaluation terminée: Accuracy={metrics['accuracy']}")
        return metrics

    def auto_improve(self, mailbox: MailBox) -> Dict:
        """
        Amélioration automatique complète
        
        1. Apprendre depuis Training/
        2. Apprendre depuis Corrections/
        3. Évaluer la performance
        4. Générer un rapport
        """
        logger.info("Démarrage de l'amélioration automatique...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "training": {},
            "corrections": {},
            "evaluation": {},
            "status": "success"
        }
        
        try:
            # 1. Apprentissage depuis Training
            report["training"] = self.learn_from_training_folder(mailbox)
            
            # 2. Apprentissage depuis Corrections
            report["corrections"] = self.learn_from_corrections(mailbox)
            
            # 3. Évaluation
            if len(self.classifier.training_examples) >= 10:
                report["evaluation"] = self.evaluate_performance()
            
            logger.info("Amélioration automatique terminée avec succès")
        
        except Exception as e:
            logger.error(f"Erreur amélioration automatique: {e}")
            report["status"] = "error"
            report["error"] = str(e)
        
        return report

    def get_summary(self) -> Dict:
        """Retourne un résumé des statistiques"""
        return {
            "training_stats": self.stats,
            "performance": self.performance,
            "classifier_stats": self.classifier.get_statistics()
        }


def main():
    """Point d'entrée principal"""
    logger.info("Démarrage du trainer...")
    
    # Vérifier les variables d'environnement
    if not IMAP_USERNAME or not IMAP_PASSWORD:
        logger.error("PROTON_USERNAME et PROTON_PASSWORD doivent être définis")
        return
    
    try:
        # Initialiser le classifier
        classifier = EmailClassifier()
        trainer = TrainingManager(classifier)
        
        # Connexion IMAP
        logger.info(f"Connexion à {IMAP_HOST}:{IMAP_PORT}...")
        with MailBox(IMAP_HOST, IMAP_PORT).login(IMAP_USERNAME, IMAP_PASSWORD) as mailbox:
            # Amélioration automatique
            report = trainer.auto_improve(mailbox)
            
            # Afficher le résumé
            logger.info(f"Rapport d'amélioration: {json.dumps(report, indent=2, ensure_ascii=False, default=str)}")
            
            # Sauvegarder le rapport
            report_file = Path(os.getenv("PROTON_LUMO_LOGS", "~/ProtonLumoAI/logs")).expanduser() / f"improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Rapport sauvegardé: {report_file}")
    
    except Exception as e:
        logger.error(f"Erreur: {e}")


if __name__ == "__main__":
    main()
