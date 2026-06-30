"""
build_data.py
Converts PRS India MLA CSV export into data.json format for Mazha Pratinidhi.

Usage:
    python build_data.py

Reads:  prs_raw_mla_data.csv  (downloaded from prsindia.org/mlatrack)
Writes: data.json

NOTE: This script currently builds MLA data only (name, constituency, party).
Attendance and "questions asked" are blank in the current 15th Assembly CSV
because the assembly is newly elected (Nov 2024) and PRS hasn't published
session data yet. We'll re-run this script periodically as PRS updates it.

MP data, District Collector, and SP are NOT in this file -- they come from
separate sources (sansad.in for MPs, state govt sites for officials) and
are added manually for now in the MANUAL_OVERRIDES section below.
"""

import csv
import json

# ── CONFIG ──────────────────────────────────────────────
CSV_FILE = "prs_raw_mla_data.csv"
OUTPUT_FILE = "data.json"

# Map of pincode -> which constituency it falls under.
# This is the piece that needs the most manual care -- pincode boundaries
# don't perfectly match constituency boundaries. Start small, expand carefully.
PINCODE_TO_CONSTITUENCY = {
    "421503": {"constituency": "Murbad", "area": "Badlapur", "area_mr": "बदलापूर"},
    "400601": {"constituency": "Ovala - Majiwada", "area": "Thane City", "area_mr": "ठाणे शहर"},
    "421201": {"constituency": "Kalyan East", "area": "Kalyan", "area_mr": "कल्याण"},
}

# Party short codes for display (PRS gives full names, we want short tags)
PARTY_SHORT = {
    "Bharatiya Janata Party": "BJP",
    "Shiv Sena": "SS",
    "Shiv Sena (UBT)": "SS (UBT)",
    "Nationalist Congress Party": "NCP",
    "Nationalist Congress Party-Sharadchandra Pawar": "NCP (SP)",
    "Indian National Congress": "INC",
    "Samajwadi Party": "SP",
}

# MP and district official data -- not available in the PRS MLA CSV.
# Filled in manually after separate verification (sansad.in, state sites).
# IMPORTANT: Replace placeholder fields below with verified facts before publishing.
MANUAL_MP_AND_OFFICIALS = {
    "421503": {
        "mp": {"name_en": "VERIFY", "constituency_en": "Kalyan", "party": "VERIFY"},
        "collector": {"name_en": "VERIFY", "title": "IAS"},
        "sp": {"name_en": "VERIFY", "title": "IPS"},
    },
    "400601": {
        "mp": {"name_en": "VERIFY", "constituency_en": "Thane", "party": "VERIFY"},
        "collector": {"name_en": "VERIFY", "title": "IAS"},
        "sp": {"name_en": "VERIFY", "title": "IPS"},
    },
    "421201": {
        "mp": {"name_en": "VERIFY", "constituency_en": "Kalyan", "party": "VERIFY"},
        "collector": {"name_en": "VERIFY", "title": "IAS"},
        "sp": {"name_en": "VERIFY", "title": "IPS"},
    },
}


def load_mla_lookup():
    """Build a dict of constituency name -> MLA info from the PRS CSV."""
    lookup = {}
    with open(CSV_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            constituency = row["Constituency"].strip()
            lookup[constituency] = {
                "name_en": row["MLA Name"].strip(),
                "party_full": row["Party"].strip(),
                "party": PARTY_SHORT.get(row["Party"].strip(), row["Party"].strip()),
                "elected_since": row["Start of term"].strip()[:4],  # just the year
                "attendance": row["Attendance"].strip() or None,
                "questions_asked": row["No. of Questions Asked"].strip() or None,
            }
    return lookup


def build_data_json():
    mla_lookup = load_mla_lookup()

    output = {
        "cm": {
            "name": "देवेंद्र फडणवीस",
            "name_en": "Devendra Fadnavis",
            "party": "BJP",
            "since": "Dec 2024"
        },
        "pincodes": {}
    }

    for pincode, meta in PINCODE_TO_CONSTITUENCY.items():
        constituency = meta["constituency"]
        mla = mla_lookup.get(constituency)

        if not mla:
            print(f"WARNING: No MLA found for constituency '{constituency}' (pincode {pincode}). Skipping.")
            continue

        extra = MANUAL_MP_AND_OFFICIALS.get(pincode, {})

        output["pincodes"][pincode] = {
            "district": "ठाणे",
            "district_en": "Thane",
            "area": meta["area_mr"],
            "area_en": meta["area"],
            "mla": {
                "name": mla["name_en"],          # TODO: add Marathi name separately
                "name_en": mla["name_en"],
                "constituency": constituency,
                "constituency_en": constituency,
                "party": mla["party"],
                "attendance": mla["attendance"],       # will be None until PRS publishes data
                "questions_asked": mla["questions_asked"],
                "elected_since": mla["elected_since"],
            },
            "mp": extra.get("mp", {}),
            "collector": extra.get("collector", {}),
            "sp": extra.get("sp", {}),
        }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Wrote {len(output['pincodes'])} pincode entries to {OUTPUT_FILE}")
    print("Remember: MP, Collector, and SP fields still say 'VERIFY' -- replace with real verified data.")


if __name__ == "__main__":
    build_data_json()
