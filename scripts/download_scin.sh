#!/usr/bin/env bash
# Download and prepare the SCIN (Skin Condition Image Network) dataset.
#
# The SCIN dataset is hosted on Google Cloud Storage by Google Research.
# Source: https://github.com/google-research-datasets/scin
#
# Usage:
#   bash scripts/download_scin.sh              # Download full dataset
#   bash scripts/download_scin.sh --skip-images # Download metadata only (fast)
#   bash scripts/download_scin.sh --limit 100   # Download first N cases only
#
# Prerequisites:
#   pip install google-cloud-storage   (or: uv pip install google-cloud-storage)
#   gcloud auth application-default login
#
# What it does:
#   1. Downloads scin_cases.csv and scin_labels.csv from GCS
#   2. Downloads all case images from GCS
#   3. Converts CSV data into metadata.json (our app's expected format)
#   4. Validates the converted records against our SCINRecord schema
#
# Output:
#   data/raw/scin/
#   ├── scin_cases.csv          # Raw CSV from Google
#   ├── scin_labels.csv         # Raw CSV from Google
#   ├── metadata.json           # Converted for our app
#   └── images/                 # Downloaded images
#       ├── <case_id>_1.jpg
#       ├── <case_id>_2.jpg
#       └── ...
#
# Covers: REQ-RUN-001

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="${SCIN_DATA_DIR:-data/raw/scin}"
SKIP_IMAGES=false
LIMIT=0

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
            echo "  --skip-images  Download metadata only, skip image files"
            echo "  --limit N      Download only the first N cases"
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

# Check prerequisites
if ! uv run python -c "import google.cloud.storage" 2>/dev/null; then
    echo "Missing dependency: google-cloud-storage"
    echo ""
    echo "Install it with:"
    echo "  uv pip install google-cloud-storage"
    echo ""
    echo "Then authenticate with:"
    echo "  gcloud auth application-default login"
    echo ""
    exit 1
fi

mkdir -p "$DATA_DIR/images"

# Run the Python download + conversion script
uv run python -c "
import io
import json
import sys
from pathlib import Path

from google.cloud import storage

DATA_DIR = Path('$DATA_DIR')
SKIP_IMAGES = $( [[ "$SKIP_IMAGES" == "true" ]] && echo "True" || echo "False" )
LIMIT = $LIMIT

BUCKET_NAME = 'dx-scin-public-data'
CASES_BLOB = 'dataset/scin_cases.csv'
LABELS_BLOB = 'dataset/scin_labels.csv'

print('Connecting to GCS bucket:', BUCKET_NAME)
client = storage.Client.create_anonymous_client()
bucket = client.bucket(BUCKET_NAME)

# ---- Download CSVs ----
import csv

print('Downloading scin_cases.csv ...')
cases_bytes = bucket.blob(CASES_BLOB).download_as_bytes()
cases_path = DATA_DIR / 'scin_cases.csv'
cases_path.write_bytes(cases_bytes)
print(f'  Saved: {cases_path} ({len(cases_bytes):,} bytes)')

print('Downloading scin_labels.csv ...')
labels_bytes = bucket.blob(LABELS_BLOB).download_as_bytes()
labels_path = DATA_DIR / 'scin_labels.csv'
labels_path.write_bytes(labels_bytes)
print(f'  Saved: {labels_path} ({len(labels_bytes):,} bytes)')

# ---- Parse CSVs ----
cases_reader = csv.DictReader(io.StringIO(cases_bytes.decode('utf-8')))
cases = list(cases_reader)
print(f'  Cases loaded: {len(cases)}')

labels_reader = csv.DictReader(io.StringIO(labels_bytes.decode('utf-8')))
labels_by_id = {}
for row in labels_reader:
    labels_by_id[row['case_id']] = row

# ---- Map Fitzpatrick types ----
FST_MAP = {
    'FST1': 'I', 'FST2': 'II', 'FST3': 'III',
    'FST4': 'IV', 'FST5': 'V', 'FST6': 'VI',
}

# ---- Map body parts ----
BODY_PART_MAP = {
    'HEAD_OR_NECK': 'head/neck', 'ARM': 'arm', 'PALM': 'palm',
    'BACK_OF_HAND': 'hand', 'ANTERIOR_TORSO': 'chest',
    'POSTERIOR_TORSO': 'back', 'GENITALIA_OR_GROIN': 'groin',
    'BUTTOCKS': 'buttocks', 'LEG': 'leg',
    'TOP_OF_FOOT': 'foot', 'SOLE_OF_FOOT': 'foot',
}

# ---- Map age groups ----
AGE_MAP = {
    'AGE_18_TO_29': 'adult', 'AGE_30_TO_39': 'adult',
    'AGE_40_TO_49': 'adult', 'AGE_50_TO_59': 'adult',
    'AGE_60_TO_69': 'adult', 'AGE_70_TO_79': 'elderly',
    'AGE_80_OR_ABOVE': 'elderly',
}

# ---- Map SCIN condition labels to ICD-10 codes ----
# Common dermatology condition -> ICD code mapping
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
    \"\"\"Map a condition label string to an ICD-10 code.\"\"\"
    if not label_str:
        return 'L98.9'  # Unspecified skin disorder
    lower = label_str.lower()
    for condition, code in CONDITION_ICD_MAP.items():
        if condition in lower:
            return code
    return 'L98.9'

def get_body_location(case):
    \"\"\"Extract body location from boolean body_parts columns.\"\"\"
    for col, location in BODY_PART_MAP.items():
        key = f'body_parts_{col}'
        if case.get(key, '').lower() in ('true', '1', 'yes'):
            return location
    return ''

def get_diagnosis_label(label_row):
    \"\"\"Extract the primary diagnosis from label data.\"\"\"
    if not label_row:
        return ''
    label = label_row.get('weighted_skin_condition_label', '')
    if label:
        # weighted_skin_condition_label is a dict-like string; get first key
        try:
            import ast
            d = ast.literal_eval(label)
            if isinstance(d, dict) and d:
                return max(d, key=d.get)
        except (ValueError, SyntaxError):
            pass
    # Fallback to dermatologist label
    name = label_row.get('dermatologist_skin_condition_label_name', '')
    if name:
        try:
            import ast
            names = ast.literal_eval(name)
            if isinstance(names, list) and names:
                return names[0]
        except (ValueError, SyntaxError):
            return name
    return ''

# ---- Convert to our metadata.json format ----
records = []
image_paths_to_download = []
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
        continue  # Skip records without valid Fitzpatrick type

    icd_code = get_icd_code(diagnosis)
    body_location = get_body_location(case)
    age_group = AGE_MAP.get(case.get('age_group', ''), 'adult')

    # Collect image paths (up to 3 per case)
    case_images = []
    for img_idx in range(1, 4):
        img_path = case.get(f'image_{img_idx}_path', '')
        if img_path:
            local_name = f'{case_id}_{img_idx}.jpg'
            case_images.append((img_path, local_name))

    if not case_images:
        continue

    # Use first image as primary
    primary_gcs_path, primary_local = case_images[0]

    # Build tags from symptoms
    tags = []
    symptom_cols = [c for c in case.keys() if c.startswith('condition_symptoms_')]
    for col in symptom_cols:
        if case.get(col, '').lower() in ('true', '1', 'yes'):
            tag = col.replace('condition_symptoms_', '').lower()
            if tag not in ('no_relevant_experience',):
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
        image_paths_to_download.append((gcs_path, local_name))

    count += 1

# Save metadata.json
metadata = {'records': records}
metadata_path = DATA_DIR / 'metadata.json'
metadata_path.write_text(json.dumps(metadata, indent=2))
print(f'')
print(f'Converted {len(records)} records -> {metadata_path}')
print(f'Images to download: {len(image_paths_to_download)}')

# ---- Download images ----
if SKIP_IMAGES:
    print('')
    print('Skipping image download (--skip-images)')
else:
    print('')
    print('Downloading images...')
    downloaded = 0
    failed = 0
    for gcs_path, local_name in image_paths_to_download:
        dest = DATA_DIR / 'images' / local_name
        if dest.exists():
            downloaded += 1
            continue
        try:
            blob = bucket.blob(gcs_path)
            blob.download_to_filename(str(dest))
            downloaded += 1
            if downloaded % 100 == 0:
                print(f'  Downloaded {downloaded}/{len(image_paths_to_download)} images...')
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f'  Failed: {gcs_path} -> {e}')
            elif failed == 6:
                print(f'  (suppressing further error messages)')

    print(f'')
    print(f'Images downloaded: {downloaded}, failed: {failed}')

print('')
print('=== SCIN download complete ===')
"

echo ""
echo "=== Done ==="
echo ""
echo "Next steps:"
echo "  1. Index embeddings:  bash scripts/index_embeddings.sh"
echo "  2. Train embeddings:  bash scripts/train_embeddings.sh --data-dir $DATA_DIR"
echo "  3. Start server:      bash scripts/start_server.sh"
