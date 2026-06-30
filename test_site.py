"""
test_site.py
Playwright UI tests for Mazha Pratinidhi -- checks the LIVE site (not local
files) actually renders the right data when a user types in a pincode.
This catches bugs the data tests can't: JS errors, broken fetch() calls,
GitHub Pages deploy lag, HTML rendering issues.

Setup (one-time):
    pip install playwright
    playwright install chromium

Run:
    python test_site.py

Edit SITE_URL below to match your actual GitHub Pages URL.
"""

from playwright.sync_api import sync_playwright
import sys

# ── CONFIG ──────────────────────────────────────────────
SITE_URL = "https://yashdhanvij55.github.io/mazha-pratinidhi/"  # <-- EDIT THIS

# Same ground-truth pincodes used in test_data.py, kept in sync manually.
# (If we expand to more districts, add a couple of new pincodes here too.)
TEST_CASES = [
    {"pincode": "400601", "expect_mla": "Sanjay Mukund Kelkar", "expect_mp": "Naresh Ganpat Mhaske"},
    {"pincode": "421503", "expect_mla": "Balaji Pralhad Kinikar", "expect_mp": "Dr. Shrikant Eknath Shinde"},
    {"pincode": "421401", "expect_mla": "Kisan Shankar Kathore", "expect_mp": "Suresh Gopinath Mhatre"},
    {"pincode": "401101", "expect_mla": "Narendra Mehta", "expect_mp": "Naresh Ganpat Mhaske"},
]

# Invalid input that should be rejected gracefully, not crash the page
INVALID_INPUTS = ["123", "abcdef", "999999"]


def run_tests():
    failures = []
    passed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"Opening {SITE_URL} ...")
        page.goto(SITE_URL, wait_until="networkidle")

        # ── TEST: page loads with expected title text ──────
        try:
            page.wait_for_selector("h1", timeout=5000)
            passed += 1
        except Exception:
            failures.append("Homepage h1 did not load within 5s")

        # ── TEST: each known pincode shows correct MLA + MP ──
        for case in TEST_CASES:
            page.fill("#pincode", "")
            page.fill("#pincode", case["pincode"])
            page.click("text=शोधा")
            page.wait_for_timeout(500)  # let fetch()+render settle

            content = page.inner_text("#results")

            if case["expect_mla"] in content:
                passed += 1
            else:
                failures.append(f"{case['pincode']}: expected MLA '{case['expect_mla']}' not found on page")

            if case["expect_mp"] in content:
                passed += 1
            else:
                failures.append(f"{case['pincode']}: expected MP '{case['expect_mp']}' not found on page")

        # ── TEST: invalid pincodes show an error, not a crash ──
        for bad_input in INVALID_INPUTS:
            page.fill("#pincode", "")
            page.fill("#pincode", bad_input)
            page.click("text=शोधा")
            page.wait_for_timeout(300)

            status_text = page.inner_text("#status")
            results_visible = page.is_visible("#results") and page.inner_text("#results").strip() != ""

            if status_text.strip() != "" and not results_visible:
                passed += 1
            else:
                failures.append(f"Invalid input '{bad_input}' did not show a clean error message")

        # ── TEST: no JS console errors during the whole flow ──
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.reload(wait_until="networkidle")
        page.fill("#pincode", "400601")
        page.click("text=शोधा")
        page.wait_for_timeout(500)

        if not console_errors:
            passed += 1
        else:
            failures.append(f"Console errors detected: {console_errors}")

        browser.close()

    print(f"\n{passed} checks passed.")
    if failures:
        print(f"{len(failures)} FAILURES:\n")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print("All site tests passed. ✓")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
