#!/usr/bin/env python3
"""
fix_t4_xml.py — Fix CRA T4 XML files for Internet File Transfer

Canada Revenue Agency rejects T4 XML submissions that contain optional fields
with zero or empty values. Most payroll software exports ALL fields regardless,
causing validation failures on upload.

This script removes those invalid optional fields while preserving all required
fields and real data, bringing the XML into compliance with the CRA T4 spec.

Spec: https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/t619-2026/t4-2026.html

Usage:
    python3 fix_t4_xml.py T4FILE.xml [T4FILE2.xml ...]
    python3 fix_t4_xml.py *.xml
    python3 fix_t4_xml.py --check T4FILE.xml    # dry-run, no changes

Author: https://github.com/1337group/cra-xml-t4-fixer
License: MIT
"""

import argparse
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

__version__ = "1.1.0"

# ──────────────────────────────────────────────────────────────────────
# CRA T4 Spec: Optional fields that MUST be removed when zero/empty
# Reference: T4 2026 XML spec (version 2026V4, updated 2026-01-30)
# ──────────────────────────────────────────────────────────────────────

# Optional T4Slip amount fields — remove when "0.00"
OPTIONAL_SLIP_AMOUNTS = [
    "empt_incamt",         # Box 14 — Employment income
    "cpp_cntrb_amt",       # Box 16 — CPP contributions
    "cppe_cntrb_amt",      # Box 16A — CPP2/enhanced contributions
    "qpp_cntrb_amt",       # Box 17 — QPP contributions
    "qppe_cntrb_amt",      # Box 17A — QPP2/enhanced contributions
    "empe_eip_amt",        # Box 18 — EI premiums
    "rpp_cntrb_amt",       # Box 20 — RPP contributions
    "itx_ddct_amt",        # Box 22 — Income tax deducted
    "unn_dues_amt",        # Box 44 — Union dues
    "chrty_dons_amt",      # Box 46 — Charitable donations
    "padj_amt",            # Box 52 — Pension adjustment
    "prov_pip_amt",        # Box 55 — PPIP premiums (QC only)
    "prov_insu_ern_amt",   # Box 56 — PPIP insurable earnings (QC only)
]

# Optional T4Summary total fields — remove when "0.00"
OPTIONAL_SUMMARY_AMOUNTS = [
    "tot_empt_incamt",
    "tot_empe_cpp_amt",
    "tot_empe_cppe_amt",
    "tot_empe_eip_amt",
    "tot_rpp_cntrb_amt",
    "tot_itx_ddct_amt",
    "tot_padj_amt",
    "tot_empr_cpp_amt",
    "tot_empr_cppe_amt",
    "tot_empr_eip_amt",
]

# OTH_INFO optional amount fields — remove when "0.00"
# These appear inside <OTH_INFO> blocks on individual slips
OPTIONAL_OTH_INFO_AMOUNTS = [
    "hm_brd_lodg_amt",               # Code 30
    "spcl_wrk_site_amt",             # Code 31
    "prscb_zn_trvl_amt",             # Code 32
    "med_trvl_amt",                   # Code 33
    "prsnl_vhcl_amt",                # Code 34
    "low_int_loan_amt",              # Code 36
    "empe_hm_loan_amt",              # Code 37
    "sob_a00_feb_amt",               # Code 38
    "sod_d_a00_feb_amt",             # Code 39
    "oth_tx_ben_amt",                # Code 40
    "sod_d1_a00_feb_amt",            # Code 41
    "empt_cmsn_amt",                 # Code 42
    "cfppa_amt",                      # Code 43
    "dfr_sob_amt",                    # Code 53
    "elg_rtir_amt",                  # Code 66
    "nelg_rtir_amt",                 # Code 67
    "indn_nelg_rtir_amt",            # Code 69
    "indn_empe_amt",                 # Code 71
    "oc_incamt",                      # Code 72
    "plcmt_emp_agcy_amt",            # Code 81
    "drvr_taxis_oth_amt",            # Code 82
    "brbr_hrdrssr_amt",              # Code 83
    "pub_trnst_pass_amt",            # Code 84
    "epaid_hlth_pln_amt",            # Code 85
    "stok_opt_csh_out_eamt",         # Code 86
    "vlntr_emergencyworker_xmpt_amt",# Code 87
    "indn_txmpt_sei_amt",           # Code 88
    "sob_after_jun2024_amt",         # Code 90
    "sod_d_after_jun2024_amt",       # Code 91
    "sod_d1_after_jun2024_amt",      # Code 92
    "indn_xmpt_rpp_amt",            # Code 94
    "indn_xmpt_unn_amt",            # Code 95
    "cmpn_rpay_empr_amt",           # Code 77
]


def fix_t4_xml(content: str) -> tuple[str, dict[str, int], list[str]]:
    """
    Fix a T4 XML string. Returns (fixed_content, changes_dict, warnings).

    Removes optional fields with zero/empty values per CRA spec.
    Removes negative amounts (not allowed by CRA schema).
    Preserves all required fields and non-zero optional data.
    """
    changes: dict[str, int] = {}
    warnings: list[str] = []

    def remove_zero_field(text: str, field: str, zero_val: str, prefix: str = "") -> str:
        """Remove a field line when it contains the given zero value."""
        # Negative lookbehind prevents matching tot_ variants when processing slip fields
        if prefix == "slip " and not field.startswith("tot_"):
            pattern = rf"(?<!tot_)<{field}>{re.escape(zero_val)}</{field}>\n"
        else:
            pattern = rf"<{field}>{re.escape(zero_val)}</{field}>\n"
        count = len(re.findall(pattern, text))
        if count:
            text = re.sub(pattern, "", text)
            changes[f"{prefix}{field}" if prefix else field] = count
        return text

    # ── 1. Remove negative amounts ─────────────────────────────────
    # CRA schema uses patterns like \d{0,5}\.\d{2} — no minus sign allowed.
    # Negative pension adjustments should be filed as a T10 (PAR), not on T4.
    neg_pattern = r"<(\w+)>(-\d+\.\d{2})</\1>\n"
    neg_matches = re.findall(neg_pattern, content)
    if neg_matches:
        for field, value in neg_matches:
            warnings.append(f"Removed negative value {value} from <{field}> — "
                            "CRA does not accept negatives. If this is a Pension "
                            "Adjustment Reversal, it should be filed on a T10 slip.")
        count = len(neg_matches)
        content = re.sub(neg_pattern, "", content)
        changes["negative_amounts_removed"] = count

    # ── 2. Slip-level optional amounts with 0.00 ────────────────────
    for field in OPTIONAL_SLIP_AMOUNTS:
        content = remove_zero_field(content, field, "0.00", "slip ")

    # ── 3. Summary-level optional totals with 0.00 ──────────────────
    for field in OPTIONAL_SUMMARY_AMOUNTS:
        content = remove_zero_field(content, field, "0.00", "summary ")

    # ── 4. OTH_INFO optional amounts with 0.00 ──────────────────────
    for field in OPTIONAL_OTH_INFO_AMOUNTS:
        content = remove_zero_field(content, field, "0.00", "oth_info ")

    # ── 5. Empty <OTH_INFO> blocks ──────────────────────────────────
    pattern = r"<OTH_INFO>\n</OTH_INFO>\n"
    count = len(re.findall(pattern, content))
    if count:
        content = re.sub(pattern, "", content)
        changes["empty_oth_info_blocks"] = count

    # ── 6. Optional non-amount fields with zero values ──────────────

    # RPP/DPSP registration number — optional, remove when all zeros
    content = remove_zero_field(content, "rpp_dpsp_rgst_nbr", "0000000")

    # Employment code — optional, "00" is not valid (valid: 11-17)
    content = remove_zero_field(content, "empt_cd", "00")

    # Provincial PIP exemption — optional, remove when 0
    content = remove_zero_field(content, "prov_pip_xmpt_cd", "0")

    # Contact extension — optional, remove when all zeros
    content = remove_zero_field(content, "cntc_extn_nbr", "00000")

    # Second proprietor SIN — optional, remove when all zeros
    content = remove_zero_field(content, "pprtr_2_sin", "000000000")

    return content, changes, warnings


def validate_xml(content: str, filename: str) -> bool:
    """Check that the XML is well-formed after modifications."""
    try:
        ET.fromstring(content)
        return True
    except ET.ParseError as e:
        print(f"  ERROR: {filename} is not valid XML after fixing: {e}", file=sys.stderr)
        return False


def process_file(filepath: Path, *, dry_run: bool = False, no_backup: bool = False) -> bool:
    """
    Process a single T4 XML file. Returns True if successful.
    """
    if not filepath.exists():
        print(f"SKIP: {filepath} not found", file=sys.stderr)
        return False

    if not filepath.suffix.lower() == ".xml":
        print(f"SKIP: {filepath} is not an XML file", file=sys.stderr)
        return False

    content = filepath.read_text(encoding="utf-8")
    original_lines = content.count("\n")

    # Sanity check: is this actually a T4 XML?
    if "<T4Slip>" not in content and "<T4Summary>" not in content:
        print(f"SKIP: {filepath.name} does not appear to be a T4 XML file", file=sys.stderr)
        return False

    # Apply fixes
    fixed, changes, warnings = fix_t4_xml(content)

    if not changes:
        print(f"\n{filepath.name}: No changes needed — already compliant")
        return True

    new_lines = fixed.count("\n")

    # Validate
    if not validate_xml(fixed, filepath.name):
        print(f"  Aborting changes to {filepath.name}", file=sys.stderr)
        return False

    # Print report
    mode = "DRY RUN" if dry_run else "FIXED"
    print(f"\n{'─'*60}")
    print(f"{mode}: {filepath.name}")
    print(f"  Lines: {original_lines} → {new_lines} (removed {original_lines - new_lines})")
    print(f"  Changes:")
    for desc, count in sorted(changes.items()):
        print(f"    ✓ {desc}: {count}")

    if warnings:
        print(f"  Warnings:")
        for w in warnings:
            print(f"    ⚠ {w}")

    if dry_run:
        return True

    # Backup original
    if not no_backup:
        backup = filepath.with_suffix(".xml.bak")
        shutil.copy2(filepath, backup)
        print(f"  Backup: {backup.name}")

    # Write fixed file
    filepath.write_text(fixed, encoding="utf-8")
    print(f"  ✓ Saved")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fix CRA T4 XML files for Internet File Transfer submission. "
                    "Removes optional fields with zero/empty values that cause CRA rejection.",
        epilog="Spec: https://www.canada.ca/en/revenue-agency/services/e-services/"
               "filing-information-returns-electronically-t4-t5-other-types-returns-overview/"
               "t619-2026/t4-2026.html",
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        metavar="FILE",
        help="T4 XML file(s) to fix",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run — show what would change without modifying files",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating .bak backup files",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    success = 0
    failed = 0

    for filepath in args.files:
        if process_file(filepath, dry_run=args.check, no_backup=args.no_backup):
            success += 1
        else:
            failed += 1

    print(f"\n{'─'*60}")
    print(f"Done: {success} file(s) processed", end="")
    if failed:
        print(f", {failed} failed", end="")
    print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
