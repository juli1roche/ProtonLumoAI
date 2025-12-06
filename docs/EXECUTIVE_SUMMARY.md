# Executive Summary Feature

## Overview

The Executive Summary feature automatically detects important emails and generates periodic HTML reports with key information and required actions.

**Purpose**: Provide a high-level overview of critical messages that require attention, especially during relocation to Scotland.

---

## Detection Criteria & Scoring

### Base Scores

| Criterion | Points | Reason |
|-----------|--------|--------|
| PRO (Work) | +30 | Professional/work emails |
| BANQUE (Financial) | +25 | Banking/financial matters |
| Important Contact | +20 | Key family/professional contacts |
| Important Domain | +20 | Key business domains |
| Urgent Keywords | +15 | urgent, important, action required |
| Relocation Keywords | +10 | scotland, visa, relocation, etc. |
| Frequent Sender | +10 | >3 emails/month from contact |
| New Domain | +10 | First contact from domain |
| No Reply >7 days | +5 | Waiting for response |

### Thresholds

- **Important**: Score ≥ 30
- **High Priority**: Score ≥ 50
- **Urgent**: Score ≥ 85

### Important Contacts (Examples)

```
brigitte.clavel@gmail.com      # Family
frederic.roche@gmail.com       # Family
robert.clavel@gmail.com        # Family
tibo.clavel@gmail.com          # Family
charles.roche@gmail.com        # Family
clavel.roche@proton.me         # Personal/family
Paul.Deas@cirrus.com           # Employer contact
```

### Important Domains

```
cirrus.com           → +20 pts (Employer)
iqaimmigration.com   → +15 pts (Immigration)
scottsrelocation.co.uk → +15 pts (Relocation)
currie.edin.sch.uk   → +15 pts (School)
```

### Relocation Keywords

```
scotland, visa, relocation, edinburgh, currie,
enrollment, school, immigration, accommodation, moving
```

---

## Report Generation

### Schedule

Executive summaries are generated **3 times daily**:

- **09:00 AM CET** - Morning digest
- **13:00 PM CET** - Midday brief
- **17:00 PM CET** - Evening summary

### Report Format

HTML email with sections:

```
🔴 URGENT (Score 85+)
   → Messages requiring immediate action

🟠 HIGH PRIORITY (Score 50-85)
   → Important messages

🟡 MEDIUM PRIORITY (Score 30-50)
   → Regular important messages (collapsed by default)

📊 Daily Statistics
   → Count breakdown by urgency
```

### Action Types

Each message is tagged with recommended action:

- **RESPOND** - Requires reply/action
- **VERIFY** - Needs verification (financial)
- **TRACK** - Package/order tracking
- **REVIEW** - Requires review

---

## Configuration

### `.env` Variables

```bash
# Enable/disable feature
PROTON_LUMO_SUMMARY_ENABLED=true

# Report schedule (24h format, comma-separated)
PROTON_LUMO_SUMMARY_HOURS=09,13,17

# Minimum score to include (0-100)
PROTON_LUMO_SUMMARY_MIN_SCORE=30

# Output format: console, email, or both
PROTON_LUMO_SUMMARY_FORMAT=email

# Email recipient
PROTON_LUMO_SUMMARY_EMAIL=juli1.roche@gmail.com

# Target folder (created automatically)
PROTON_LUMO_SUMMARY_FOLDER=Folders/Exec-Summary

# Important contacts (comma-separated)
PROTON_LUMO_IMPORTANT_CONTACTS=brigitte.clavel@gmail.com,frederic.roche@gmail.com

# Relocation keywords (comma-separated)
PROTON_LUMO_RELOCATION_KEYWORDS=scotland,visa,relocation,edinburgh

# Important domains (format: domain:score,domain:score)
PROTON_LUMO_IMPORTANT_DOMAINS=cirrus.com:20,iqaimmigration.com:15
```

---

## Usage

### Check Today's Summary

```bash
cd ~/ProtonLumoAI/data
ls -lh summary*.json | tail -1
cat summary_*.json | jq '.urgent_count,.high_count,.medium_count'
```

### View HTML Report

```bash
# Open latest HTML report
open ~/ProtonLumoAI/data/summary_*.html | tail -1
```

### Customize Scoring

Edit `.env` to adjust:

```bash
# Add new important contact
PROTON_LUMO_IMPORTANT_CONTACTS=...,new.contact@domain.com

# Add relocation keywords
PROTON_LUMO_RELOCATION_KEYWORDS=...,keyword

# Adjust report frequency
PROTON_LUMO_SUMMARY_HOURS=08,14,18  # Changed from 09,13,17
```

Then restart:

```bash
lumo-stop
lumo-start
```

---

## Output Locations

### Email Reports

**Folder**: `Folders/Exec-Summary` (created automatically)
- Messages stored as unseen emails
- HTML formatted for easy reading
- Daily reports at 09:00, 13:00, 17:00 CET

### Local Backups

**Directory**: `~/ProtonLumoAI/data/`
- `summary_YYYYMMDD_HHMMSS.json` - Structured data
- `summary_YYYYMMDD_HHMMSS.html` - Formatted report
- `important_messages.json` - All important messages log

### Logs

```bash
lumo-logs | grep "Executive\|Executive"
lumo-logs | grep "summary"
```

---

## Examples

### Example Scoring: Cirrus Onboarding Email

```
From: Paul.Deas@cirrus.com
Subject: [ACTION REQUIRED] Onboarding documents needed
Body: Please complete your onboarding by Dec 10. Urgent.

Scoring:
  - Category: PRO           → +30 pts
  - Domain: cirrus.com      → +20 pts
  - Urgent keywords         → +15 pts
  - Frequent sender         → +10 pts
  ────────────────────────────
  TOTAL SCORE: 75 pts       → HIGH PRIORITY ✅
  Action: RESPOND
```

### Example Scoring: Immigration Email

```
From: beverley.harper@iqaimmigration.com
Subject: Visa applications submitted
Body: Your visa applications have been submitted. Edinburgh arrival date confirmed Jan 2.

Scoring:
  - Category: PRO           → +30 pts
  - Domain: iqaimmigration.com → +15 pts
  - Important contact       → +20 pts
  - Relocation keywords     → +10 pts
  ────────────────────────────
  TOTAL SCORE: 75 pts       → HIGH PRIORITY ✅
  Action: VERIFY
```

### Example Scoring: Shopping Email

```
From: amazon.com
Subject: Order #12345 shipped
Body: Your laptop charger has shipped. Delivery Dec 10-15.

Scoring:
  - Category: VENTE         → +5 pts
  ────────────────────────────
  TOTAL SCORE: 5 pts        → NOT IMPORTANT ✗
  (Below 30 threshold)
```

---

## Troubleshooting

### Reports Not Generating

1. **Check if enabled**:
   ```bash
   grep "SUMMARY_ENABLED" ~/.env
   ```

2. **Check logs**:
   ```bash
   lumo-logs | grep -i summary
   ```

3. **Verify time settings**:
   ```bash
   grep "SUMMARY_HOURS" ~/.env
   ```

4. **Check folder exists**:
   ```bash
   ls -la ~/ProtonLumoAI/data/important_messages.json
   ```

### Wrong Importance Score

1. Review criteria breakdown in JSON report
2. Verify contacts/domains in `.env`
3. Check relocation keywords match
4. Adjust thresholds if needed

---

## Future Enhancements

- [ ] Machine learning refinement based on user actions
- [ ] Custom scoring rules per sender
- [ ] Integration with calendar for deadline tracking
- [ ] Slack/Teams notifications
- [ ] Web dashboard for summary viewing
- [ ] Historical trend analysis
