#!/usr/bin/env bash
# Download and prepare the SCIN (Skin Condition Image Network) dataset.
#
# The SCIN dataset is publicly hosted on Google Cloud Storage.
# Source: https://github.com/google-research-datasets/scin
#
# Usage:
#   bash scripts/download_scin.sh              # Download full dataset
#   bash scripts/download_scin.sh --skip-images # Download metadata only (fast)
#   bash scripts/download_scin.sh --limit 100   # Download first N cases only
#
# No cloud SDK or authentication required — uses public HTTPS URLs.
#
# What it does:
#   1. Downloads scin_cases.csv and scin_labels.csv via HTTPS
#   2. Converts CSV data into metadata.json (our app's expected format)
#   3. Downloads all case images via HTTPS
#
# Output:
#   data/raw/scin/
#   ├── scin_cases.csv          # Raw CSV from Google
#   ├── scin_labels.csv         # Raw CSV from Google
#   ├── metadata.json           # Converted for our app
#   └── images/                 # Downloaded images
#       ├── <case_id>_1.jpg
#       └── ...
#
# Covers: REQ-RUN-001

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="${SCIN_DATA_DIR:-data/raw/scin}"
SKIP_IMAGES=false
LIMIT=0
GCS_BASE="https://storage.googleapis.com/dx-scin-public-data/dataset"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-images)
            SKIP_IMAGES=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--skip-images] [--limit N]"
            echo ""
            echo "Options:"
            echo "  --skip-images  Download metadata CSVs only, skip image files"
            echo "  --limit N      Convert only the first N cases"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== SCIN Dataset Downloader ==="
echo ""
echo "Target directory: $DATA_DIR"
echo "Skip images:     $SKIP_IMAGES"
[[ $LIMIT -gt 0 ]] && echo "Limit:           $LIMIT cases"
echo ""

mkdir -p "$DATA_DIR/images"

# ---- Download CSVs ----
CASES_CSV="$DATA_DIR/scin_cases.csv"
LABELS_CSV="$DATA_DIR/scin_labels.csv"

if [[ -f "$CASES_CSV" ]]; then
    echo "scin_cases.csv already exists, skipping download"
else
    echo "Downloading scin_cases.csv ..."
    curl -fSL --progress-bar -o "$CASES_CSV" "$GCS_BASE/scin_cases.csv"
fi

if [[ -f "$LABELS_CSV" ]]; then
    echo "scin_labels.csv already exists, skipping download"
else
    echo "Downloading scin_labels.csv ..."
    curl -fSL --progress-bar -o "$LABELS_CSV" "$GCS_BASE/scin_labels.csv"
fi

echo ""
echo "CSVs downloaded. Converting to metadata.json ..."
echo ""

# ---- Convert CSVs to metadata.json and download images ----
uv run python -c "
import ast
import csv
import json
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path('$DATA_DIR')
SKIP_IMAGES = $( [[ "$SKIP_IMAGES" == "true" ]] && echo "True" || echo "False" )
LIMIT = $LIMIT
GCS_BASE = '$GCS_BASE'

# ---- Parse CSVs ----
with open(DATA_DIR / 'scin_cases.csv', encoding='utf-8') as f:
    cases = list(csv.DictReader(f))
print(f'Cases loaded: {len(cases)}')

with open(DATA_DIR / 'scin_labels.csv', encoding='utf-8') as f:
    labels_by_id = {row['case_id']: row for row in csv.DictReader(f)}
print(f'Labels loaded: {len(labels_by_id)}')

# ---- Mappings ----
FST_MAP = {
    'FST1': 'I', 'FST2': 'II', 'FST3': 'III',
    'FST4': 'IV', 'FST5': 'V', 'FST6': 'VI',
}

BODY_PART_MAP = {
    'HEAD_OR_NECK': 'head/neck', 'ARM': 'arm', 'PALM': 'palm',
    'BACK_OF_HAND': 'hand', 'ANTERIOR_TORSO': 'chest',
    'POSTERIOR_TORSO': 'back', 'GENITALIA_OR_GROIN': 'groin',
    'BUTTOCKS': 'buttocks', 'LEG': 'leg',
    'TOP_OF_FOOT': 'foot', 'SOLE_OF_FOOT': 'foot',
}

AGE_MAP = {
    'AGE_18_TO_29': 'adult', 'AGE_30_TO_39': 'adult',
    'AGE_40_TO_49': 'adult', 'AGE_50_TO_59': 'adult',
    'AGE_60_TO_69': 'adult', 'AGE_70_TO_79': 'elderly',
    'AGE_80_OR_ABOVE': 'elderly',
}

CONDITION_ICD_MAP = {
    'acne': 'L70.0', 'atopic dermatitis': 'L20.0', 'eczema': 'L20.0',
    'psoriasis': 'L40.0', 'contact dermatitis': 'L25.0',
    'seborrheic dermatitis': 'L21.0', 'urticaria': 'L50.0',
    'fungal infection': 'L30.0', 'tinea': 'B35.0',
    'melanoma': 'L43.0', 'basal cell carcinoma': 'L43.0',
    'squamous cell carcinoma': 'L43.0', 'wart': 'L82.0',
    'mole': 'L82.0', 'rosacea': 'L71.0', 'vitiligo': 'L80.0',
    'alopecia': 'L63.0', 'folliculitis': 'L73.0',
    'herpes': 'L00.0', 'impetigo': 'L01.0', 'cellulitis': 'L03.0',
    'insect bite': 'L24.0', 'drug eruption': 'L27.0',
    'scabies': 'L86.0', 'lichen planus': 'L43.0',
}


def get_icd_code(label_str):
    if not label_str:
        return 'L98.9'
    lower = label_str.lower()
    for condition, code in CONDITION_ICD_MAP.items():
        if condition in lower:
            return code
    return 'L98.9'


def get_body_location(case):
    for col, location in BODY_PART_MAP.items():
        key = f'body_parts_{col}'
        if case.get(key, '').lower() in ('true', '1', 'yes'):
            return location
    return ''


def get_diagnosis_label(label_row):
    if not label_row:
        return ''
    label = label_row.get('weighted_skin_condition_label', '')
    if label:
        try:
            d = ast.literal_eval(label)
            if isinstance(d, dict) and d:
                return max(d, key=d.get)
        except (ValueError, SyntaxError):
            pass
    name = label_row.get('dermatologist_skin_condition_label_name', '')
    if name:
        try:
            names = ast.literal_eval(name)
            if isinstance(names, list) and names:
                return names[0]
        except (ValueError, SyntaxError):
            return name
    return ''


# ---- Convert to metadata.json ----
records = []
image_downloads = []  # (url, local_path)
count = 0

for case in cases:
    if LIMIT > 0 and count >= LIMIT:
        break

    case_id = case.get('case_id', '')
    if not case_id:
        continue

    label_row = labels_by_id.get(case_id, {})
    diagnosis = get_diagnosis_label(label_row)
    fst_raw = case.get('fitzpatrick_skin_type', '')
    fst = FST_MAP.get(fst_raw, '')

    if not fst:
        continue

    icd_code = get_icd_code(diagnosis)
    body_location = get_body_location(case)
    age_group = AGE_MAP.get(case.get('age_group', ''), 'adult')

    # Collect image paths (up to 3 per case)
    case_images = []
    for img_idx in range(1, 4):
        gcs_path = case.get(f'image_{img_idx}_path', '')
        if gcs_path:
            local_name = f'{case_id}_{img_idx}.jpg'
            case_images.append((gcs_path, local_name))

    if not case_images:
        continue

    primary_gcs_path, primary_local = case_images[0]

    # Build tags from symptoms
    tags = []
    for col in case:
        if col.startswith('condition_symptoms_') and case[col].lower() in ('true', '1', 'yes'):
            tag = col.replace('condition_symptoms_', '').lower()
            if tag != 'no_relevant_experience':
                tags.append(tag)

    record = {
        'record_id': f'SCIN-{case_id}',
        'image_path': f'images/{primary_local}',
        'diagnosis': diagnosis or 'Unspecified skin condition',
        'icd_code': icd_code,
        'fitzpatrick_type': fst,
        'body_location': body_location,
        'age_group': age_group,
        'severity': 'unknown',
        'description': f'{diagnosis or \"Skin condition\"} on {body_location or \"unspecified location\"}',
        'tags': tags,
    }
    records.append(record)

    for gcs_path, local_name in case_images:
        dest = DATA_DIR / 'images' / local_name
        if not dest.exists():
            # gcs_path is "dataset/images/..." but GCS_BASE already ends with /dataset
            clean_path = gcs_path.removeprefix('dataset/')
            url = f'{GCS_BASE}/{clean_path}'
            image_downloads.append((url, str(dest)))

    count += 1

# Save metadata.json
metadata = {'records': records}
metadata_path = DATA_DIR / 'metadata.json'
metadata_path.write_text(json.dumps(metadata, indent=2))
print(f'Converted {len(records)} records -> {metadata_path}')
print(f'Images to download: {len(image_downloads)} (skipping already downloaded)')

# ---- Download images via curl ----
if SKIP_IMAGES:
    print('')
    print('Skipping image download (--skip-images)')
else:
    print('')
    total = len(image_downloads)
    if total == 0:
        print('All images already downloaded.')
    else:
        print(f'Downloading {total} images...')
        downloaded = 0
        failed = 0
        for url, dest in image_downloads:
            try:
                result = subprocess.run(
                    ['curl', '-fsSL', '-o', dest, url],
                    capture_output=True, timeout=30,
                )
                if result.returncode == 0:
                    downloaded += 1
                else:
                    failed += 1
                    if failed <= 5:
                        print(f'  Failed: {url}')
                    elif failed == 6:
                        print('  (suppressing further error messages)')
            except subprocess.TimeoutExpired:
                failed += 1

            if (downloaded + failed) % 200 == 0:
                print(f'  Progress: {downloaded + failed}/{total} ({downloaded} ok, {failed} failed)')

        print(f'')
        print(f'Images: {downloaded} downloaded, {failed} failed')

print('')
print('=== SCIN download complete ===')
"

echo ""
echo "=== Done ==="
echo ""
echo "Dataset stored locally at: $DATA_DIR"
echo ""
echo "Next steps:"
echo "  1. Index embeddings:  bash scripts/index_embeddings.sh"
echo "  2. Train embeddings:  bash scripts/train_embeddings.sh --data-dir $DATA_DIR"
echo "  3. Start server:      bash scripts/start_server.sh"
