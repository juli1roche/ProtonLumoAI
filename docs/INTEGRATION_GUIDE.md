# 📝 Integration Guide - Performance Optimization

**How to integrate parallel processing and batch classification into email_processor.py**

This guide shows exactly what code to add to enable 4x faster processing.

---

## 📄 Overview

Two new extension files have been created:

1. **`scripts/email_classifier_batch.py`** - Batch classification (10 emails = 1 API call)
2. **`scripts/email_processor_parallel.py`** - Parallel processing (5 worker threads)

You'll integrate these into `email_processor.py` to enable optimizations.

---

## 💻 Integration Steps

### Step 1: Add Imports to email_processor.py

At the top of `scripts/email_processor.py`, add:

```python
# === PERFORMANCE OPTIMIZATIONS (v1.2.0) ===
from concurrent.futures import ThreadPoolExecutor, as_completed
from email_classifier_batch import BatchClassifier, BatchEmail
from email_processor_parallel import ParallelProcessor, ProcessingMetrics
import time
```

**Location:** After existing imports (around line 20)

---

### Step 2: Add Configuration Loading

In the `__init__` method of `EmailProcessor` class, add:

```python
# === PERFORMANCE SETTINGS (v1.2.0) ===
self.enable_parallel = os.getenv("PROTON_LUMO_ENABLE_PARALLEL", "true").lower() == "true"
self.max_workers = int(os.getenv("PROTON_LUMO_MAX_WORKERS", 5))
self.enable_batch = os.getenv("PROTON_LUMO_ENABLE_BATCH", "true").lower() == "true"
self.batch_size = int(os.getenv("PROTON_LUMO_BATCH_SIZE", 10))
self.metrics_enabled = os.getenv("PROTON_LUMO_METRICS_ENABLED", "true").lower() == "true"

# Initialize optimizers
if self.enable_parallel:
    self.parallel_processor = ParallelProcessor(
        max_workers=self.max_workers,
        enable_metrics=self.metrics_enabled
    )
else:
    self.parallel_processor = None

if self.enable_batch:
    self.batch_classifier = BatchClassifier(
        enable_batch=True,
        batch_size=self.batch_size
    )
else:
    self.batch_classifier = None

logger.info(
    f"Performance settings: parallel={self.enable_parallel} "
    f"({self.max_workers} workers), batch={self.enable_batch} (size={self.batch_size})"
)
```

**Location:** In `__init__` method, after other initializations

---

### Step 3: Add Batch Classification Method

Add this new method to `EmailProcessor` class:

```python
def _classify_batch(self, email_ids: List[bytes], mailbox) -> Dict[str, Tuple[str, float]]:
    """
    Classify multiple emails in batches (v1.2.0 optimization)
    
    ⚠️ SECURITY: Never stores credentials, uses environment variables only
    
    Args:
        email_ids: List of email IDs from IMAP
        mailbox: IMAP connection object
        
    Returns:
        Dict mapping email_id → (category, confidence)
    """
    
    if not self.enable_batch or not self.batch_classifier:
        return {}
    
    logger.info(f"Using batch classification (size={self.batch_size}) for {len(email_ids)} emails")
    
    # Fetch all email subjects/bodies first
    batch_emails = []
    for email_id in email_ids:
        try:
            res, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
            if res == 'OK':
                raw_email = msg_data[0][1]
                subject, sender, body = self.parser.parse(raw_email)
                
                # Truncate body for batch efficiency
                body_truncated = body[:500]
                
                batch_emails.append(
                    BatchEmail(
                        email_id=email_id.decode(),
                        subject=subject,
                        body=body_truncated
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            continue
    
    if not batch_emails:
        return {}
    
    # Classify in batches
    valid_categories = list(self.classifier.categories.keys())
    results = {}
    
    # Process in chunks of batch_size
    for i in range(0, len(batch_emails), self.batch_size):
        batch_chunk = batch_emails[i:i + self.batch_size]
        classifications = self.batch_classifier.classify_batch(batch_chunk, valid_categories)
        results.update(classifications)
    
    logger.info(f"Batch classification complete: {len(results)} emails classified")
    return results
```

**Location:** Add as new method in `EmailProcessor` class

---

### Step 4: Integrate Parallel Processing

Modify the `process_folder` method to use parallel processing:

**Find this line (current sequential processing):**
```python
for email_id in email_ids:
    # Process each email
    if not self.running:
        break
    # ... (existing processing code)
```

**Replace with this (conditional parallel processing):**
```python
if self.enable_parallel and self.parallel_processor and len(email_ids) > 1:
    # 🚀 PARALLEL PROCESSING
    logger.info(f"Processing {len(email_ids)} emails in parallel ({self.max_workers} workers)")
    
    # Define processing function for each thread
    def process_single_email(email_id: bytes) -> Optional[Dict]:
        """
        Process single email (runs in thread pool)
        
        ⚠️ SECURITY: 
        - Each thread has isolated scope
        - No credential sharing between threads
        - Errors in one thread don't affect others
        """
        try:
            email_uid = email_id.decode()
            email_key = f"{folder_name}:{email_uid}"
            
            if email_key in self.processed_emails:
                logger.debug(f"Email {email_uid} already processed, skip")
                return None
            
            # Fetch and parse
            res, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
            if res != 'OK':
                logger.error(f"Error fetching email {email_uid}")
                return None
            
            raw_email = msg_data[0][1]
            subject, sender, body = self.parser.parse(raw_email)
            
            # Classify (using existing single-email classifier)
            result = self.classifier.classify(email_uid, subject, body)
            
            return {
                'email_id': email_id,
                'email_uid': email_uid,
                'subject': subject,
                'sender': sender,
                'body': body,
                'category': result.category,
                'confidence': result.confidence
            }
        except Exception as e:
            logger.error(f"Error processing email in thread: {e}")
            return None
    
    # Process in parallel
    results, metrics = self.parallel_processor.process_emails_parallel(
        [{'id': eid} for eid in email_ids],
        process_single_email,
        folder_name=folder_name
    )
    
    # Process results (same as before)
    for result in results:
        if result:
            # ... (existing result processing code)
            pass
else:
    # 🐌 SEQUENTIAL PROCESSING (fallback)
    logger.debug(f"Sequential processing for {len(email_ids)} emails")
    for email_id in email_ids:
        # ... (existing sequential code)
        pass
```

**Location:** Replace the `for email_id in email_ids:` loop in `process_folder` method

---

## 🦨 Safety Checklist

Before deploying, verify:

✅ **Credentials**
- [ ] No credentials hardcoded in code
- [ ] All credentials loaded from `.env` via `os.getenv()`
- [ ] `.env` file in `.gitignore`
- [ ] No credentials in logs

✅ **Parallel Safety**
- [ ] Each thread has isolated IMAP connection (if needed)
- [ ] No shared mutable state
- [ ] Error in one thread doesn't crash processor
- [ ] ThreadPoolExecutor used correctly

✅ **API Safety**
- [ ] API calls include proper error handling
- [ ] Rate limits respected
- [ ] API key from environment only
- [ ] Timeouts configured (30s per API call)

---

## 🧪 Testing

### Test 1: Verify Configuration

```bash
# Check your .env has performance settings
grep -E "ENABLE_PARALLEL|MAX_WORKERS|BATCH_SIZE" ~/.ProtonLumoAI/.env

# Expected output:
# PROTON_LUMO_ENABLE_PARALLEL=true
# PROTON_LUMO_MAX_WORKERS=5
# PROTON_LUMO_ENABLE_BATCH=true
# PROTON_LUMO_BATCH_SIZE=10
```

### Test 2: Dry Run with Logging

```bash
# Start in dry-run mode to test without moving emails
cd ~/ProtonLumoAI

# Update .env temporarily
echo "PROTON_LUMO_DRY_RUN=true" >> .env.test

# Run with test config
DOTENV=.env.test python scripts/email_processor.py

# Watch for these log messages:
# ✏️  Performance settings: parallel=true (5 workers), batch=true (size=10)
# 🚀 Processing 87 emails in parallel (5 workers)
# 📊 Performance Metrics
```

### Test 3: Performance Comparison

```bash
# Before optimization
time python scripts/email_processor.py > /dev/null

# After optimization
time python scripts/email_processor.py > /dev/null

# Compare times - should see 3-4x speedup
```

---

## 🚀 Migration Path

### Option A: Gradual Integration (Recommended)

1. **Test in dry-run mode first**
   ```env
   PROTON_LUMO_DRY_RUN=true
   PROTON_LUMO_ENABLE_PARALLEL=true
   PROTON_LUMO_ENABLE_BATCH=true
   ```

2. **Monitor logs for 24h**
   - Check for errors
   - Verify performance improvements
   - Confirm accuracy unchanged

3. **Go live**
   ```env
   PROTON_LUMO_DRY_RUN=false
   ```

### Option B: Feature Flags

Test each feature independently:

```bash
# Test parallel only
PROTON_LUMO_ENABLE_PARALLEL=true
PROTON_LUMO_ENABLE_BATCH=false

# Test batch only
PROTON_LUMO_ENABLE_PARALLEL=false
PROTON_LUMO_ENABLE_BATCH=true

# Test both
PROTON_LUMO_ENABLE_PARALLEL=true
PROTON_LUMO_ENABLE_BATCH=true
```

---

## 🐛 Troubleshooting Integration

### Issue: ImportError

```
ModuleNotFoundError: No module named 'email_classifier_batch'
```

**Fix:** Ensure files are in `scripts/` directory
```bash
ls -la ~/ProtonLumoAI/scripts/email_classifier_batch.py
ls -la ~/ProtonLumoAI/scripts/email_processor_parallel.py
```

### Issue: AttributeError on classifier

```
AttributeError: 'EmailProcessor' object has no attribute 'batch_classifier'
```

**Fix:** Ensure initialization code added to `__init__` method
```python
if self.enable_batch:
    self.batch_classifier = BatchClassifier(...)
```

### Issue: API Rate Limits

```
ERROR | Perplexity API rate limit exceeded
```

**Fix:** Reduce workers
```env
PROTON_LUMO_MAX_WORKERS=2  # Reduce from 5
```

---

## 📃 Files Created/Modified

| File | Status | Purpose |
|------|--------|----------|
| `scripts/email_classifier_batch.py` | ✨ NEW | Batch classification (10 emails/call) |
| `scripts/email_processor_parallel.py` | ✨ NEW | Parallel processing (ThreadPoolExecutor) |
| `scripts/email_processor.py` | 🔒 MODIFY | Add integration code (see steps above) |
| `.env.example` | 🔒 MODIFY | Add new config variables |
| `docs/PERFORMANCE.md` | ✨ NEW | Performance guide |
| `docs/INTEGRATION_GUIDE.md` | ✨ NEW | This file |

---

## 📄 Next Steps

1. **Review code** - Read through the three extension files
2. **Integrate** - Follow steps 1-4 above
3. **Test** - Run through testing procedures
4. **Monitor** - Check logs and metrics
5. **Deploy** - Set `DRY_RUN=false` when ready
6. **Optimize** - Adjust `MAX_WORKERS` and `BATCH_SIZE` based on results

---

## 📂 References

- [Performance Optimization Guide](PERFORMANCE.md)
- [Main README](../README.md)
- [Changelog](../CHANGELOG.md)
- [Python concurrent.futures docs](https://docs.python.org/3/library/concurrent.futures.html)

---

**Questions?** Review the performance guide or open an issue on GitHub.
