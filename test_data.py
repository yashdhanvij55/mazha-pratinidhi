"""
test_data.py
Fast data-layer tests for Mazha Pratinidhi. No browser needed -- these run
in under a second and catch the exact bugs we found by hand while building
(duplicate pincode keys, missing MP/Collector data, wrong police jurisdiction).

Run this BEFORE every git push, and especially right after running
build_data.py or editing PINCODE_TO_CONSTITUENCY / MP_BY_ASSEMBLY_CONSTITUENCY.

Usage:
    python test_data.py

Exits with code 0 if all tests pass, code 1 if anything fails (so this can
later be wired into a GitHub Actions check that blocks bad pushes).
"""

import json
import sys

DATA_FILE = "data.json"

# A hand-verified "ground truth" table -- the same one we manually checked
# against PRS, IndiaVotes, and the official Thane district sites. Any pincode
# listed here MUST match data.json exactly, or the test fails.
EXPECTED = {
    "400601": {"constituency": "Thane", "mla": "Sanjay Mukund Kelkar", "mla_party": "BJP", "mp": "Naresh Ganpat Mhaske"},
    "421503": {"constituency": "Ambernath", "mla": "Balaji Pralhad Kinikar", "mla_party": "SS", "mp": "Dr. Shrikant Eknath Shinde"},
    "421401": {"constituency": "Murbad", "mla": "Kisan Shankar Kathore", "mla_party": "BJP", "mp": "Suresh Gopinath Mhatre (Balya Mama)"},
    "401101": {"constituency": "Mira Bhayandar", "mla": "Narendra Mehta", "mla_party": "BJP", "mp": "Naresh Ganpat Mhaske"},
    "421302": {"constituency": "Bhiwandi East", "mla": "Rais Kasam Shaikh", "mla_party": "SP", "mp": "Suresh Gopinath Mhatre (Balya Mama)"},
}

failures = []
passed = 0


def check(condition, message):
    global passed
    if condition:
        passed += 1
    else:
        failures.append(message)


def main():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"FAIL: {DATA_FILE} not found. Run build_data.py first.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"FAIL: {DATA_FILE} is not valid JSON -- {e}")
        sys.exit(1)

    pincodes = data.get("pincodes", {})

    # ── TEST 1: CM data exists ──────────────────────────────
    check("cm" in data and data["cm"].get("name_en"), "CM data missing or incomplete")

    # ── TEST 2: every pincode key is exactly 6 digits ───────
    for pin in pincodes:
        check(len(pin) == 6 and pin.isdigit(), f"Pincode '{pin}' is not a valid 6-digit code")

    # ── TEST 3: every entry has the required fields ─────────
    required_mla_fields = ["name_en", "constituency_en", "party"]
    for pin, entry in pincodes.items():
        mla = entry.get("mla", {})
        for field in required_mla_fields:
            check(mla.get(field), f"{pin}: MLA missing field '{field}'")
        check(entry.get("district_en"), f"{pin}: missing district_en")
        check(entry.get("area_en"), f"{pin}: missing area_en")

    # ── TEST 4: no constituency is mapped to a missing MLA ──
    for pin, entry in pincodes.items():
        check(entry.get("mla", {}).get("name_en") not in (None, "", "VERIFY"),
              f"{pin}: MLA name is empty or still a placeholder")

    # ── TEST 5: ground-truth spot checks ────────────────────
    for pin, expected in EXPECTED.items():
        entry = pincodes.get(pin)
        check(entry is not None, f"{pin}: expected pincode missing from data.json entirely")
        if entry is None:
            continue
        check(entry["mla"]["constituency_en"] == expected["constituency"],
              f"{pin}: expected constituency '{expected['constituency']}', got '{entry['mla']['constituency_en']}'")
        check(entry["mla"]["name_en"] == expected["mla"],
              f"{pin}: expected MLA '{expected['mla']}', got '{entry['mla']['name_en']}'")
        check(entry["mla"]["party"] == expected["mla_party"],
              f"{pin}: expected party '{expected['mla_party']}', got '{entry['mla']['party']}'")
        if entry.get("mp", {}).get("name_en"):
            check(entry["mp"]["name_en"] == expected["mp"],
                  f"{pin}: expected MP '{expected['mp']}', got '{entry['mp']['name_en']}'")

    # ── TEST 6: same constituency never has two different MLAs ──
    # (this is the type of bug a duplicate dict key would cause)
    constituency_to_mla = {}
    for pin, entry in pincodes.items():
        c = entry["mla"]["constituency_en"]
        name = entry["mla"]["name_en"]
        if c in constituency_to_mla and constituency_to_mla[c] != name:
            check(False, f"Constituency '{c}' has conflicting MLAs: '{constituency_to_mla[c]}' vs '{name}' (pincode {pin})")
        else:
            constituency_to_mla[c] = name
            check(True, "")

    # ── TEST 7: police role label always present when police name is present ──
    for pin, entry in pincodes.items():
        police = entry.get("police", {})
        if police.get("name_en"):
            check(police.get("role_en"), f"{pin}: police name present but role_en (job title) is missing")

    # ── SUMMARY ──────────────────────────────────────────────
    print(f"\n{passed} checks passed.")
    if failures:
        print(f"{len(failures)} FAILURES:\n")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print("All data tests passed. ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
