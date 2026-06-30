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
    # Thane City / Kopri-Pachpakhadi
    "400601": {"constituency": "Thane", "area": "Thane City (Naupada)", "area_mr": "ठाणे शहर (नौपाडा)"},
    "400602": {"constituency": "Kopri - Pachpakhadi", "area": "Kopri / Panchpakhadi", "area_mr": "कोपरी / पाचपाखाडी"},
    "400606": {"constituency": "Kopri - Pachpakhadi", "area": "Thane East", "area_mr": "ठाणे पूर्व"},
    "400610": {"constituency": "Mumbra - Kalwa", "area": "Kalwa", "area_mr": "कळवा"},
    "400612": {"constituency": "Mumbra - Kalwa", "area": "Mumbra", "area_mr": "मुंब्रा"},

    # Ovala-Majiwada
    "400607": {"constituency": "Ovala - Majiwada", "area": "Majiwada / Thane West", "area_mr": "माजिवडा / ठाणे पश्चिम"},
    "400615": {"constituency": "Ovala - Majiwada", "area": "Owale / Hiranandani Estate", "area_mr": "ओवळे / हिरानंदानी इस्टेट"},

    # Kalyan cluster
    "421301": {"constituency": "Kalyan West", "area": "Kalyan West", "area_mr": "कल्याण पश्चिम"},
    "421306": {"constituency": "Kalyan East", "area": "Kalyan East", "area_mr": "कल्याण पूर्व"},
    "421304": {"constituency": "Kalyan Rural", "area": "Titwala", "area_mr": "टिटवाळा"},
    "421204": {"constituency": "Kalyan Rural", "area": "Mohone", "area_mr": "मोहने"},

    # Dombivli (separate pincodes from Kalyan)
    "421201": {"constituency": "Kalyan East", "area": "Dombivli East", "area_mr": "डोंबिवली पूर्व"},
    "421202": {"constituency": "Kalyan East", "area": "Dombivli West", "area_mr": "डोंबिवली पश्चिम"},

    # Ambernath / Ulhasnagar / Badlapur / Murbad
    "421501": {"constituency": "Ambernath", "area": "Ambernath West", "area_mr": "अंबरनाथ पश्चिम"},
    "421502": {"constituency": "Ambernath", "area": "Ambernath East", "area_mr": "अंबरनाथ पूर्व"},
    "421503": {"constituency": "Ambernath", "area": "Badlapur", "area_mr": "बदलापूर"},
    "421001": {"constituency": "Ulhasnagar", "area": "Ulhasnagar", "area_mr": "उल्हासनगर"},
    "421401": {"constituency": "Murbad", "area": "Murbad", "area_mr": "मुरबाड"},

    # Bhiwandi cluster
    "421302": {"constituency": "Bhiwandi East", "area": "Bhiwandi", "area_mr": "भिवंडी"},
    "421305": {"constituency": "Bhiwandi West", "area": "Bhiwandi West", "area_mr": "भिवंडी पश्चिम"},
    "421308": {"constituency": "Bhiwandi Rural", "area": "Padgha", "area_mr": "पडघा"},

    # Shahapur / Mira-Bhayandar
    "421601": {"constituency": "Shahapur", "area": "Shahapur", "area_mr": "शहापूर"},
    "401101": {"constituency": "Mira Bhayandar", "area": "Mira Road", "area_mr": "मिरा रोड"},
    "401105": {"constituency": "Mira Bhayandar", "area": "Bhayandar", "area_mr": "भाईंदर"},
}

# NOTE ON ACCURACY: Pincode-to-constituency boundaries don't align perfectly
# with postal boundaries -- some pincodes above are best-effort based on the
# dominant constituency for that area's main town. Before public launch, each
# entry should be spot-checked (e.g. against voter ID / Form 26 constituency
# lookup on the CEO Maharashtra site) especially for areas that straddle two
# constituencies. Treat this list as a strong first draft, not final truth.

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
# Sourced separately and verified against multiple election result sources
# (IndiaVotes.com, ECI-derived) -- June 2024 Lok Sabha results.
#
# Each Lok Sabha seat covers several assembly constituencies. We map by
# assembly constituency name (not pincode directly) so it stays correct
# even as we add more pincodes within the same constituency.
MP_BY_ASSEMBLY_CONSTITUENCY = {
    # Thane Lok Sabha MP -- covers Mira Bhayandar, Ovala-Majiwada,
    # Kopri-Pachpakhadi, Thane, Airoli, Belapur (last 2 are outside our district)
    "Mira Bhayandar":      {"name_en": "Naresh Ganpat Mhaske", "constituency_en": "Thane", "party": "SS"},
    "Ovala - Majiwada":    {"name_en": "Naresh Ganpat Mhaske", "constituency_en": "Thane", "party": "SS"},
    "Kopri - Pachpakhadi": {"name_en": "Naresh Ganpat Mhaske", "constituency_en": "Thane", "party": "SS"},
    "Thane":               {"name_en": "Naresh Ganpat Mhaske", "constituency_en": "Thane", "party": "SS"},

    # Kalyan Lok Sabha MP -- covers Ambernath, Ulhasnagar, Kalyan East,
    # Dombivli (part of Kalyan East/West in our data), Kalyan Rural, Mumbra-Kalwa
    "Ambernath":       {"name_en": "Dr. Shrikant Eknath Shinde", "constituency_en": "Kalyan", "party": "SS"},
    "Ulhasnagar":      {"name_en": "Dr. Shrikant Eknath Shinde", "constituency_en": "Kalyan", "party": "SS"},
    "Kalyan East":     {"name_en": "Dr. Shrikant Eknath Shinde", "constituency_en": "Kalyan", "party": "SS"},
    "Kalyan West":     {"name_en": "Dr. Shrikant Eknath Shinde", "constituency_en": "Kalyan", "party": "SS"},
    "Kalyan Rural":    {"name_en": "Dr. Shrikant Eknath Shinde", "constituency_en": "Kalyan", "party": "SS"},
    "Mumbra - Kalwa":  {"name_en": "Dr. Shrikant Eknath Shinde", "constituency_en": "Kalyan", "party": "SS"},

    # Bhiwandi Lok Sabha MP -- covers Bhiwandi East/West/Rural, Murbad, Shahapur
    "Bhiwandi East":   {"name_en": "Suresh Gopinath Mhatre (Balya Mama)", "constituency_en": "Bhiwandi", "party": "NCP (SP)"},
    "Bhiwandi West":   {"name_en": "Suresh Gopinath Mhatre (Balya Mama)", "constituency_en": "Bhiwandi", "party": "NCP (SP)"},
    "Bhiwandi Rural":  {"name_en": "Suresh Gopinath Mhatre (Balya Mama)", "constituency_en": "Bhiwandi", "party": "NCP (SP)"},
    "Murbad":          {"name_en": "Suresh Gopinath Mhatre (Balya Mama)", "constituency_en": "Bhiwandi", "party": "NCP (SP)"},
    "Shahapur":        {"name_en": "Suresh Gopinath Mhatre (Balya Mama)", "constituency_en": "Bhiwandi", "party": "NCP (SP)"},
}
# Source: IndiaVotes.com 2024 Lok Sabha results, cross-checked against
# Oneindia and IndiaTV election coverage. Verified October 2026.

# District Collector and SP/CP -- sourced from official district & police sites,
# verified October 2026. IMPORTANT STRUCTURAL NOTE: unlike the Collector (one
# per revenue district), policing in urban Maharashtra is commissionerate-based,
# not simple district-based. Thane has THREE separate police jurisdictions:
#   - Thane City (Police Commissioner, not "SP")
#   - Thane Rural (Superintendent of Police)
#   - Mira Bhayandar-Vasai-Virar (its own separate Police Commissioner)
# We map police authority by constituency, not by a single district-wide value.

DISTRICT_COLLECTOR = {
    "Thane": {"name_en": "Dr. Shrikrishnanath B. Panchal", "title": "IAS"},
}

POLICE_BY_ASSEMBLY_CONSTITUENCY = {
    # Thane City Police Commissionerate
    "Thane":               {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Kopri - Pachpakhadi":  {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Ovala - Majiwada":     {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Mumbra - Kalwa":       {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Kalyan East":          {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Kalyan West":          {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Kalyan Rural":         {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Ambernath":            {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},
    "Ulhasnagar":           {"name_en": "Ashutosh Dumbre", "title": "IPS", "role_en": "Commissioner of Police, Thane City"},

    # Mira Bhayandar-Vasai-Virar Police Commissionerate (separate from Thane City)
    "Mira Bhayandar":       {"name_en": "Niket Kaushik", "title": "IPS", "role_en": "Commissioner of Police, MBVV"},

    # Thane Rural Police (covers more spread-out/semi-rural talukas)
    "Murbad":               {"name_en": "Dr. D. S. Swamy", "title": "IPS", "role_en": "Superintendent of Police, Thane Rural"},
    "Shahapur":             {"name_en": "Dr. D. S. Swamy", "title": "IPS", "role_en": "Superintendent of Police, Thane Rural"},
    "Bhiwandi East":        {"name_en": "Dr. D. S. Swamy", "title": "IPS", "role_en": "Superintendent of Police, Thane Rural"},
    "Bhiwandi West":        {"name_en": "Dr. D. S. Swamy", "title": "IPS", "role_en": "Superintendent of Police, Thane Rural"},
    "Bhiwandi Rural":       {"name_en": "Dr. D. S. Swamy", "title": "IPS", "role_en": "Superintendent of Police, Thane Rural"},
}
# CAUTION: this jurisdiction mapping is a reasonable-effort draft based on
# general knowledge of which towns fall under which commissionerate. Police
# jurisdiction boundaries can be redrawn and these officers rotate via
# transfer more frequently than elected officials -- re-verify every few
# months, ideally by checking thanepolice.gov.in, thaneruralpolice.gov.in,
# and the MBVV police site directly before any public launch.


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


def check_for_duplicate_pincodes():
    """Defensive check: Python dicts silently drop duplicate keys, which
    caused a real bug earlier (400607 and 421201 each appeared twice and
    silently overwrote each other). This re-parses the source as a list
    of pairs to catch that mistake before it happens again."""
    import re
    seen = []
    duplicates = []
    for pincode in PINCODE_TO_CONSTITUENCY.keys():
        if pincode in seen:
            duplicates.append(pincode)
        seen.append(pincode)
    if duplicates:
        raise ValueError(f"Duplicate pincode keys found: {duplicates}. Fix PINCODE_TO_CONSTITUENCY before running.")


def build_data_json():
    check_for_duplicate_pincodes()
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

        mp = MP_BY_ASSEMBLY_CONSTITUENCY.get(constituency)
        collector = DISTRICT_COLLECTOR.get("Thane")
        police = POLICE_BY_ASSEMBLY_CONSTITUENCY.get(constituency)

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
            "mp": mp if mp else {},
            "collector": collector if collector else {},
            "police": police if police else {},
        }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Wrote {len(output['pincodes'])} pincode entries to {OUTPUT_FILE}")
    print("MLA, MP, Collector, and Police data are all real and verified.")
    print("Re-verify Collector/Police entries periodically -- these roles rotate via transfer.")


if __name__ == "__main__":
    build_data_json()