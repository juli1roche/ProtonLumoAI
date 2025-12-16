#!/usr/bin/env python3
# ============================================================================
# EMAIL CLASSIFIER - ProtonLumoAI OPTIMIZED
# Système de classification intelligent avec optimisations coûts/performances
# 
# Améliorations:
# - Cache intelligent par hash email (évite appels API redondants)
# - Batch processing (traite 10-20 emails par requête)
# - Rate limiter (respecte les limites API Perplexity)
# - Export vers filtres SIEVE ProtonMail (automatisation post-apprentissage)
# - Métriques de coûts et performances
# ============================================================================

import os
import json
import hashlib
import time
import requests
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from collections import deque, defaultdict

from loguru import logger
from pydantic import BaseModel, Field

# --- CONFIGURATION LOGGING ---
LOG_DIR = Path(os.getenv("PROTON_LUMO_LOGS", "~/ProtonLumoAI/logs")).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(LOG_DIR / "classifier_optimized.log", rotation="10 MB", retention="7 days")

# --- MODÈLES DE DONNÉES ---
class EmailCategory(BaseModel):
    """Représentation d'une catégorie d'email"""
    name: str
    folder: str
    keywords: List[str] = Field(default_factory=list)
    confidence_threshold: float = 0.6
    priority: int = 0
    description: str = ""


class ClassificationResult(BaseModel):
    """Résultat de classification d'un email"""
    email_id: str
    subject: str
    category: str
    confidence: float
    method: str  # "cached", "batch_api", "api", "keyword", "fallback"
    timestamp: str
    explanation: str = ""
    from_address: str = ""


class CachedPattern(BaseModel):
    """Pattern en cache pour classification rapide"""
    email_hash: str
    category: str
    confidence: float
    hit_count: int = 1
    last_used: str
    from_domain: str = ""


class APIMetrics(BaseModel):
    """Métriques d'utilisation API"""
    total_classifications: int = 0
    api_calls: int = 0
    cache_hits: int = 0
    keyword_fallbacks: int = 0
    batch_calls: int = 0
    estimated_cost_usd: float = 0.0


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
        folder="Folders/Achats",
        keywords=["solde", "promo", "offrir", "%", "commander", "panier", "livraison", "code promo"],
        confidence_threshold=0.65,
        priority=2,
        description="Emails commerciaux et offres d'achat"
    ),
    "BANQUE": EmailCategory(
        name="BANQUE",
        folder="Folders/Administratif/Banque",
        keywords=["virement", "compte", "banque", "facture", "paiement", "transaction", "solde"],
        confidence_threshold=0.8,
        priority=3,
        description="Emails bancaires et administratifs"
    ),
    "PRO": EmailCategory(
        name="PRO",
        folder="Folders/Travail",
        keywords=["réunion", "projet", "client", "deadline", "rapport", "présentation", "meeting"],
        confidence_threshold=0.7,
        priority=4,
        description="Emails professionnels"
    ),
    "URGENT": EmailCategory(
        name="URGENT",
        folder="Folders/A_traiter",
        keywords=["urgent", "asap", "important", "action requise", "immédiat"],
        confidence_threshold=0.75,
        priority=5,
        description="Emails marqués comme urgents"
    ),
    "VOYAGES": EmailCategory(
        name="VOYAGES",
        folder="Folders/Voyages",
        keywords=["billet", "train", "vol", "booking", "hôtel", "réservation", "itinéraire"],
        confidence_threshold=0.7,
        priority=2,
        description="Confirmations et informations de voyage"
    ),
    "SOCIAL": EmailCategory(
        name="SOCIAL",
        folder="Folders/Reseaux_sociaux",
        keywords=["like", "comment", "follow", "share", "mention", "notification", "friend request"],
        confidence_threshold=0.65,
        priority=1,
        description="Notifications des réseaux sociaux"
    ),
    "NEWSLETTER": EmailCategory(
        name="NEWSLETTER",
        folder="Folders/Newsletters",
        keywords=["newsletter", "weekly", "monthly", "digest", "subscribe", "unsubscribe"],
        confidence_threshold=0.7,
        priority=1,
        description="Newsletters et digests"
    ),
}


class RateLimiter:
    """Limite le taux d'appels API pour respecter les quotas"""
    
    def __init__(self, max_calls: int = 50, period: int = 60):
        """
        Args:
            max_calls: Nombre max d'appels par période
            period: Période en secondes
        """
        self.calls = deque()
        self.max_calls = max_calls
        self.period = period
        logger.info(f"Rate limiter initialisé: {max_calls} appels/{period}s")
    
    def wait_if_needed(self):
        """Attend si la limite est atteinte"""
        now = time.time()
        
        # Supprimer les appels anciens
        while self.calls and self.calls[0] < now - self.period:
            self.calls.popleft()
        
        # Vérifier la limite
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            logger.warning(f"⏱️  Rate limit atteint, attente de {sleep_time:.1f}s")
            time.sleep(sleep_time + 0.1)
            
            # Nettoyer après l'attente
            now = time.time()
            while self.calls and self.calls[0] < now - self.period:
                self.calls.popleft()
        
        self.calls.append(now)


class EmailClassifierOptimized:
    """Système de classification optimisé avec cache et batch processing"""

    def __init__(self, config_dir: Optional[str] = None, use_api: bool = True):
        """
        Initialise le classifier optimisé
        
        Args:
            config_dir: Répertoire de configuration
            use_api: Utiliser l'API Perplexity si disponible
        """
        self.config_dir = Path(config_dir or os.getenv("PROTON_LUMO_CONFIG", "~/ProtonLumoAI/config")).expanduser()
        self.data_dir = Path(os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")).expanduser()
        self.cache_dir = self.data_dir / "cache"
        
        # Créer les répertoires
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_api = use_api and bool(os.getenv("PERPLEXITY_API_KEY"))
        self.categories = self._load_categories()
        self.cache = self._load_cache()
        self.learned_patterns = self._load_learned_patterns()
        self.metrics = APIMetrics()
        
        # Rate limiter: 50 appels/minute (conservateur)
        self.rate_limiter = RateLimiter(max_calls=50, period=60)
        
        logger.info(f"✅ Classifier optimisé initialisé (API: {self.use_api}, Cache: {len(self.cache)} entrées)")

    def _load_categories(self) -> Dict[str, EmailCategory]:
        """Charge les catégories depuis le fichier de config"""
        categories_file = self.config_dir / "categories.json"
        
        if categories_file.exists():
            try:
                with open(categories_file) as f:
                    data = json.load(f)
                    return {k: EmailCategory(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Erreur chargement catégories : {e}")
        
        self._save_categories(DEFAULT_CATEGORIES)
        return DEFAULT_CATEGORIES

    def _save_categories(self, categories: Dict[str, EmailCategory]):
        """Sauvegarde les catégories"""
        categories_file = self.config_dir / "categories.json"
        with open(categories_file, "w") as f:
            json.dump({k: v.dict() for k, v in categories.items()}, f, indent=2, ensure_ascii=False)

    def _load_cache(self) -> Dict[str, CachedPattern]:
        """Charge le cache de patterns"""
        cache_file = self.cache_dir / "patterns_cache.json"
        
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    return {k: CachedPattern(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Erreur chargement cache : {e}")
        
        return {}

    def _save_cache(self):
        """Sauvegarde le cache"""
        cache_file = self.cache_dir / "patterns_cache.json"
        with open(cache_file, "w") as f:
            json.dump({k: v.dict() for k, v in self.cache.items()}, f, indent=2, ensure_ascii=False)

    def _load_learned_patterns(self) -> Dict[str, Dict]:
        """Charge les patterns appris (expéditeurs fréquents, etc.)"""
        patterns_file = self.data_dir / "learning" / "folder_patterns.json"
        
        if patterns_file.exists():
            try:
                with open(patterns_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement patterns : {e}")
        
        return {}

    def _compute_email_hash(self, from_address: str, subject: str) -> str:
        """Calcule un hash unique pour un email (basé sur expéditeur + sujet normalisé)"""
        # Extraire le domaine de l'expéditeur
        domain = from_address.split("@")[-1] if "@" in from_address else from_address
        
        # Normaliser le sujet (retirer numéros, dates, etc.)
        subject_normalized = subject.lower()
        subject_normalized = subject_normalized[:50]  # Limiter la longueur
        
        hash_input = f"{domain}:{subject_normalized}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def should_use_api(self, email_hash: str, subject: str, body: str) -> bool:
        """
        Décide si l'API est nécessaire ou si le cache/keywords suffisent
        
        Returns:
            True si l'API doit être appelée, False sinon
        """
        # Vérifier le cache
        if email_hash in self.cache:
            self.cache[email_hash].hit_count += 1
            self.cache[email_hash].last_used = datetime.now().isoformat()
            return False  # Utiliser le cache
        
        # Vérifier si les keywords donnent une confidence élevée
        _, confidence, _ = self.classify_with_keywords(subject, body)
        if confidence >= 0.75:  # Seuil élevé pour éviter l'API
            return False  # Utiliser les keywords
        
        return True  # API nécessaire

    def classify_with_keywords(self, subject: str, body: str) -> Tuple[str, float, str]:
        """Classification par mots-clés (fallback rapide et gratuit)"""
        content = f"{subject} {body}".lower()
        scores = {}
        
        for cat_name, category in DEFAULT_CATEGORIES.items():
            matches = sum(1 for keyword in category.keywords if keyword.lower() in content)
            
            if matches > 0:
                confidence = min(0.95, (matches / max(len(category.keywords), 1)) * 0.85)
                scores[cat_name] = (confidence, f"{matches} mot(s)-clé trouvé(s)")
        
        if scores:
            best_category = max(scores.items(), key=lambda x: x[1][0])
            return best_category[0], best_category[1][0], best_category[1][1]
        
        return "SPAM", 0.0, "Aucune correspondance"

    def classify_batch(self, emails: List[Dict]) -> List[ClassificationResult]:
        """
        Classifie plusieurs emails en un seul appel API (optimisation majeure)
        
        Args:
            emails: Liste de dicts avec 'email_id', 'subject', 'body', 'from'
            
        Returns:
            Liste de ClassificationResult
        """
        if not emails:
            return []
        
        results = []
        api_needed = []
        
        # Étape 1: Trier les emails (cache vs API)
        for email in emails:
            email_hash = self._compute_email_hash(email.get('from', ''), email['subject'])
            
            # Vérifier le cache
            if email_hash in self.cache:
                pattern = self.cache[email_hash]
                pattern.hit_count += 1
                pattern.last_used = datetime.now().isoformat()
                
                results.append(ClassificationResult(
                    email_id=email['email_id'],
                    subject=email['subject'],
                    category=pattern.category,
                    confidence=pattern.confidence,
                    method="cached",
                    timestamp=datetime.now().isoformat(),
                    explanation=f"Cache hit #{pattern.hit_count}",
                    from_address=email.get('from', '')
                ))
                self.metrics.cache_hits += 1
                continue
            
            # Essayer keywords
            category, confidence, explanation = self.classify_with_keywords(email['subject'], email.get('body', ''))
            
            if confidence >= 0.75:
                results.append(ClassificationResult(
                    email_id=email['email_id'],
                    subject=email['subject'],
                    category=category,
                    confidence=confidence,
                    method="keyword",
                    timestamp=datetime.now().isoformat(),
                    explanation=explanation,
                    from_address=email.get('from', '')
                ))
                self.metrics.keyword_fallbacks += 1
                
                # Ajouter au cache pour accélérer les prochains
                self.cache[email_hash] = CachedPattern(
                    email_hash=email_hash,
                    category=category,
                    confidence=confidence,
                    last_used=datetime.now().isoformat(),
                    from_domain=email.get('from', '').split('@')[-1]
                )
            else:
                api_needed.append((email, email_hash))
        
        # Étape 2: Batch API pour les emails restants (10-15 par batch)
        if api_needed and self.use_api:
            batch_size = 15
            for i in range(0, len(api_needed), batch_size):
                batch = api_needed[i:i + batch_size]
                batch_results = self._classify_batch_api(batch)
                results.extend(batch_results)
                self.metrics.batch_calls += 1
        
        self.metrics.total_classifications += len(emails)
        return results

    def _classify_batch_api(self, emails_with_hash: List[Tuple[Dict, str]]) -> List[ClassificationResult]:
        """Appelle l'API Perplexity pour un batch d'emails"""
        if not emails_with_hash:
            return []
        
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            logger.error("❌ Clé API Perplexity manquante")
            return []
        
        # Respecter le rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            valid_categories = list(DEFAULT_CATEGORIES.keys())
            categories_desc = "\n".join([
                f"- {cat}: {DEFAULT_CATEGORIES[cat].description}"
                for cat in valid_categories
            ])
            
            # Construire le prompt batch
            emails_text = "\n\n".join([
                f"Email {idx}:\nSubject: {email['subject']}\nFrom: {email.get('from', 'unknown')}\nBody: {email.get('body', '')[:500]}"
                for idx, (email, _) in enumerate(emails_with_hash)
            ])
            
            prompt = f"""Classify these {len(emails_with_hash)} emails into categories:
{categories_desc}

{emails_text}

Return ONLY a JSON array with this format:
[
  {{"email_index": 0, "category": "CATEGORY_NAME", "confidence": 0.9, "explanation": "reason"}},
  ...
]

RULES:
1. ONLY use these categories: {', '.join(valid_categories)}
2. Return ALL emails in order (0 to {len(emails_with_hash)-1})
3. Output MUST be valid JSON array"""

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "system", "content": f"Email classifier. Valid categories: {', '.join(valid_categories)}. Output JSON only."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post("https://api.perplexity.ai/chat/completions", 
                                   headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result_json = response.json()
                content = result_json["choices"][0]["message"]["content"]
                
                # Nettoyage Markdown
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                classifications = json.loads(content)
                
                results = []
                for item in classifications:
                    idx = item.get("email_index", 0)
                    if idx >= len(emails_with_hash):
                        continue
                    
                    email, email_hash = emails_with_hash[idx]
                    category = item.get("category", "SPAM").upper()
                    confidence = float(item.get("confidence", 0.0))
                    explanation = item.get("explanation", "")
                    
                    # Validation catégorie
                    if category not in valid_categories:
                        category = "SPAM"
                        confidence = 0.3
                    
                    result = ClassificationResult(
                        email_id=email['email_id'],
                        subject=email['subject'],
                        category=category,
                        confidence=confidence,
                        method="batch_api",
                        timestamp=datetime.now().isoformat(),
                        explanation=explanation,
                        from_address=email.get('from', '')
                    )
                    
                    results.append(result)
                    
                    # Mettre en cache
                    self.cache[email_hash] = CachedPattern(
                        email_hash=email_hash,
                        category=category,
                        confidence=confidence,
                        last_used=datetime.now().isoformat(),
                        from_domain=email.get('from', '').split('@')[-1]
                    )
                
                self.metrics.api_calls += 1
                # Coût estimé: $0.005 par appel batch (approximatif)
                self.metrics.estimated_cost_usd += 0.005
                
                logger.info(f"✓ Batch API: {len(results)} emails classifiés")
                return results
            else:
                logger.error(f"❌ Erreur API: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Erreur batch API: {e}")
        
        return []

    def classify(self, email_id: str, subject: str, body: str, from_address: str = "") -> ClassificationResult:
        """Classifie un email unique (wrapper pour compatibilité)"""
        results = self.classify_batch([{
            'email_id': email_id,
            'subject': subject,
            'body': body,
            'from': from_address
        }])
        
        return results[0] if results else ClassificationResult(
            email_id=email_id,
            subject=subject,
            category="SPAM",
            confidence=0.0,
            method="fallback",
            timestamp=datetime.now().isoformat(),
            explanation="Erreur classification",
            from_address=from_address
        )

    def export_to_protonmail_filters(self, min_occurrences: int = 5) -> str:
        """
        Génère des règles SIEVE pour ProtonMail Bridge
        
        Args:
            min_occurrences: Nombre minimum d'emails d'un expéditeur pour créer une règle
            
        Returns:
            Règles SIEVE formatées
        """
        logger.info("📤 Export des règles ProtonMail...")
        
        # Analyser les patterns appris
        sender_categories = defaultdict(lambda: defaultdict(int))
        
        # Depuis le cache
        for pattern in self.cache.values():
            if pattern.hit_count >= min_occurrences:
                sender_categories[pattern.from_domain][pattern.category] += pattern.hit_count
        
        # Générer les règles SIEVE
        rules = []
        rules.append("# ProtonLumoAI - Règles automatiques générées")
        rules.append(f"# Date: {datetime.now().isoformat()}")
        rules.append("")
        
        for domain, categories in sender_categories.items():
            if not domain:
                continue
            
            # Catégorie la plus fréquente pour ce domaine
            best_category = max(categories.items(), key=lambda x: x[1])
            category_name, count = best_category
            
            if count >= min_occurrences and category_name in self.categories:
                folder = self.categories[category_name].folder
                
                rules.append(f"# Règle pour {domain} -> {category_name} ({count} emails)")
                rules.append(f'if header :contains "From" "{domain}" {{')
                rules.append(f'    fileinto "{folder}";')
                rules.append(f'    stop;')
                rules.append(f'}}')
                rules.append("")
        
        sieve_rules = "\n".join(rules)
        
        # Sauvegarder
        filters_file = self.config_dir / "protonmail_filters.sieve"
        with open(filters_file, "w") as f:
            f.write(sieve_rules)
        
        logger.info(f"✅ Règles exportées vers {filters_file}")
        return sieve_rules

    def get_metrics(self) -> Dict:
        """Retourne les métriques d'utilisation"""
        cache_size_mb = sum(len(str(p.dict())) for p in self.cache.values()) / 1024 / 1024
        
        savings_pct = 0
        if self.metrics.total_classifications > 0:
            savings_pct = ((self.metrics.cache_hits + self.metrics.keyword_fallbacks) / 
                          self.metrics.total_classifications * 100)
        
        return {
            "total_classifications": self.metrics.total_classifications,
            "api_calls": self.metrics.api_calls,
            "batch_calls": self.metrics.batch_calls,
            "cache_hits": self.metrics.cache_hits,
            "keyword_fallbacks": self.metrics.keyword_fallbacks,
            "cache_size_entries": len(self.cache),
            "cache_size_mb": round(cache_size_mb, 2),
            "estimated_cost_usd": round(self.metrics.estimated_cost_usd, 3),
            "cost_savings_percent": round(savings_pct, 1)
        }

    def save_state(self):
        """Sauvegarde l'état (cache, métriques)"""
        self._save_cache()
        
        metrics_file = self.data_dir / "metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(self.get_metrics(), f, indent=2)
        
        logger.info("💾 État sauvegardé")


# --- FONCTION DE TEST ---
if __name__ == "__main__":
    # Test du classifier optimisé
    classifier = EmailClassifierOptimized()
    
    # Exemple de batch
    test_emails = [
        {"email_id": "1", "subject": "Réunion projet lundi", "body": "Bonjour, rendez-vous...", "from": "chef@company.com"},
        {"email_id": "2", "subject": "Soldes -50%", "body": "Profitez des offres...", "from": "promo@shop.com"},
        {"email_id": "3", "subject": "Virement effectué", "body": "Votre virement...", "from": "banque@credit.fr"},
    ]
    
    results = classifier.classify_batch(test_emails)
    
    for r in results:
        print(f"✓ {r.email_id}: {r.category} ({r.confidence:.2f}) - {r.method}")
    
    print("\n📊 Métriques:")
    print(json.dumps(classifier.get_metrics(), indent=2))
    
    print("\n📤 Export ProtonMail:")
    sieve_rules = classifier.export_to_protonmail_filters(min_occurrences=2)
    print(sieve_rules[:500])
    
    classifier.save_state()
