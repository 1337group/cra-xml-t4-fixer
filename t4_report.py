#!/usr/bin/env python3
"""
t4_report.py — Convert CRA T4 XML files into human-readable T4 reports.

Parses the XML structure and outputs a clean, formatted document showing
each T4 slip with proper box labels — ready to send to a government agency.

Also supports CSV export for spreadsheet use.
"""

import csv
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
# T4 Box number mappings — XML field names → human-readable labels
# ──────────────────────────────────────────────────────────────────────

T4_AMOUNT_BOXES = {
    "empt_incamt":       ("14", "Employment Income"),
    "cpp_cntrb_amt":     ("16", "CPP Contributions"),
    "cppe_cntrb_amt":    ("16A", "CPP2/Enhanced Contributions"),
    "qpp_cntrb_amt":     ("17", "QPP Contributions"),
    "qppe_cntrb_amt":    ("17A", "QPP2/Enhanced Contributions"),
    "empe_eip_amt":      ("18", "EI Premiums"),
    "rpp_cntrb_amt":     ("20", "RPP Contributions"),
    "itx_ddct_amt":      ("22", "Income Tax Deducted"),
    "ei_insu_ern_amt":   ("24", "EI Insurable Earnings"),
    "cpp_qpp_ern_amt":   ("26", "CPP/QPP Pensionable Earnings"),
    "unn_dues_amt":      ("44", "Union Dues"),
    "chrty_dons_amt":    ("46", "Charitable Donations"),
    "padj_amt":          ("52", "Pension Adjustment"),
    "prov_pip_amt":      ("55", "PPIP Premiums"),
    "prov_insu_ern_amt": ("56", "PPIP Insurable Earnings"),
}

OTH_INFO_BOXES = {
    "hm_brd_lodg_amt":                    ("30", "Board and Lodging"),
    "spcl_wrk_site_amt":                  ("31", "Special Work Site"),
    "prscb_zn_trvl_amt":                  ("32", "Travel in Prescribed Zone"),
    "med_trvl_amt":                       ("33", "Medical Travel"),
    "prsnl_vhcl_amt":                     ("34", "Personal Vehicle Use"),
    "rsn_per_km_amt":                     ("35", "Reasonable Per-Km Allowance"),
    "low_int_loan_amt":                   ("36", "Low-Interest Loan Benefit"),
    "empe_hm_loan_amt":                   ("37", "Employee Home Loan"),
    "stok_opt_ben_amt":                   ("38", "Stock Option Benefit"),
    "sob_a00_feb_amt":                    ("38", "Security Options Benefits (pre-Jul 2024)"),
    "shr_opt_d_ben_amt":                  ("39", "Stock Option Deduction (110(1)(d))"),
    "sod_d_a00_feb_amt":                  ("39", "Sec Options Deduction 110(1)(d) (pre-Jul 2024)"),
    "oth_tx_ben_amt":                     ("40", "Other Taxable Benefits"),
    "shr_opt_d1_ben_amt":                 ("41", "Stock Option Deduction (110(1)(d.1))"),
    "sod_d1_a00_feb_amt":                 ("41", "Sec Options Deduction 110(1)(d.1) (pre-Jul 2024)"),
    "empt_cmsn_amt":                      ("42", "Employment Commissions"),
    "cfppa_amt":                          ("43", "CFPPA"),
    "dfr_sob_amt":                        ("53", "Deferred Security Options Benefit"),
    "elg_rtir_amt":                       ("66", "Eligible Retiring Allowance"),
    "nelg_rtir_amt":                      ("67", "Non-Eligible Retiring Allowance"),
    "indn_elg_rtir_amt":                  ("68", "Indian — Eligible Retiring Allowance"),
    "indn_nelg_rtir_amt":                 ("69", "Indian — Non-Eligible Retiring Allowance"),
    "indn_empe_amt":                      ("71", "Indian — Employment Income"),
    "oc_incamt":                          ("72", "Offshore/Contract Income"),
    "oc_dy_cnt":                          ("73", "Offshore/Contract Days"),
    "pr_90_cntrbr_amt":                   ("74", "Pre-1990 Contributory"),
    "pr_90_ncntrbr_amt":                  ("75", "Pre-1990 Non-Contributory"),
    "cmpn_rpay_empr_amt":                 ("77", "Workers' Compensation Employer Repay"),
    "fish_gro_ern_amt":                   ("78", "Fishing — Gross Earnings"),
    "fish_net_ptnr_amt":                  ("79", "Fishing — Net Partnership"),
    "fish_shr_prsn_amt":                  ("80", "Fishing — Shareperson"),
    "plcmt_emp_agcy_amt":                 ("81", "Placement/Employment Agency"),
    "drvr_taxis_oth_amt":                 ("82", "Driver/Taxi/Other Transport"),
    "brbr_hrdrssr_amt":                   ("83", "Barber/Hairdresser"),
    "pub_trnst_pass_amt":                 ("84", "Public Transit Pass"),
    "epaid_hlth_pln_amt":                 ("85", "Employee-Paid Health Plan"),
    "stok_opt_csh_out_eamt":              ("86", "Stock Option Cash-Out Election"),
    "vlntr_emergencyworker_xmpt_amt":     ("87", "Volunteer Emergency Worker Exemption"),
    "indn_txmpt_sei_amt":                 ("88", "Indian — Tax-Exempt Self-Employment"),
    "mun_ofcr_examt":                     ("89", "Municipal Officer Expense Allowance"),
    "sob_after_jun2024_amt":              ("90", "Security Options Benefits (post-Jun 2024)"),
    "sod_d_after_jun2024_amt":            ("91", "Sec Options Deduction 110(1)(d) (post-Jun 2024)"),
    "sod_d1_after_jun2024_amt":           ("92", "Sec Options Deduction 110(1)(d.1) (post-Jun 2024)"),
    "indn_xmpt_rpp_amt":                 ("94", "Indian — Exempt RPP Contributions"),
    "indn_xmpt_unn_amt":                 ("95", "Indian — Exempt Union Dues"),
    "lv_supp_top_up_amt":                 ("96", "Leave Support Top-Up"),
}

PROVINCE_NAMES = {
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
    "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia", "NT": "Northwest Territories", "NU": "Nunavut",
    "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
    "SK": "Saskatchewan", "YT": "Yukon",
}

EMPLOYMENT_CODES = {
    "11": "Placement/employment agency",
    "12": "Driver of taxi/other passenger vehicle",
    "13": "Barber/hairdresser",
    "14": "Seasonal agricultural worker",
    "15": "Member of religious order with vow of poverty",
    "16": "Indian (exempt income)",
    "17": "Caregiver",
}

DENTAL_CODES = {
    "1": "Offered dental — employee enrolled",
    "2": "Offered dental — employee not enrolled",
    "3": "Offered dental — enrolled in another plan",
    "4": "No dental offered",
    "5": "No dental — enrolled in another plan",
}


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class T4Employee:
    """Parsed data for a single T4 slip."""
    surname: str = ""
    given_name: str = ""
    initial: str = ""
    sin: str = ""
    employee_number: str = ""
    bn: str = ""
    addr_line1: str = ""
    addr_line2: str = ""
    city: str = ""
    province: str = ""
    country: str = ""
    postal_code: str = ""
    empt_prov_cd: str = ""
    cpp_qpp_exempt: str = "0"
    ei_exempt: str = "0"
    pip_exempt: str = ""
    employment_code: str = ""
    report_type: str = ""
    dental_code: str = ""
    rpp_dpsp_nbr: str = ""
    amounts: dict = field(default_factory=dict)      # field_name → value
    oth_info: dict = field(default_factory=dict)      # field_name → value


@dataclass
class T4Summary:
    """Parsed data for the T4 summary."""
    bn: str = ""
    employer_name: str = ""
    employer_name2: str = ""
    employer_name3: str = ""
    employer_addr_line1: str = ""
    employer_addr_line2: str = ""
    employer_city: str = ""
    employer_province: str = ""
    employer_country: str = ""
    employer_postal: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    tax_year: str = ""
    slip_count: str = ""
    report_type: str = ""
    totals: dict = field(default_factory=dict)


@dataclass
class T4Transmitter:
    """Parsed data for the T619 transmitter record."""
    account_bn: str = ""
    name: str = ""
    country: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    language: str = ""


# ──────────────────────────────────────────────────────────────────────
# XML Parsing
# ──────────────────────────────────────────────────────────────────────

def _get_text(element: ET.Element, tag: str) -> str:
    """Get text content of a child element, or empty string."""
    el = element.find(tag)
    return (el.text or "").strip() if el is not None else ""


def parse_t4_xml(xml_content: str) -> tuple[T4Transmitter | None, list[T4Employee], T4Summary | None]:
    """
    Parse a CRA T4 XML file and return structured data.
    Returns (transmitter, list_of_employees, summary).
    """
    root = ET.fromstring(xml_content)

    # ── Parse T619 transmitter ───────────────────────────────
    transmitter = None
    t619 = root.find("T619")
    if t619 is not None:
        transmitter = T4Transmitter()
        acct = t619.find("TransmitterAccountNumber")
        if acct is not None:
            transmitter.account_bn = _get_text(acct, "bn15") or _get_text(acct, "bn9")
        name_el = t619.find("TransmitterName")
        if name_el is not None:
            transmitter.name = _get_text(name_el, "l1_nm")
        transmitter.country = _get_text(t619, "TransmitterCountryCode")
        transmitter.language = _get_text(t619, "lang_cd")
        cntc = t619.find("CNTC")
        if cntc is not None:
            transmitter.contact_name = _get_text(cntc, "cntc_nm")
            area = _get_text(cntc, "cntc_area_cd")
            phone = _get_text(cntc, "cntc_phn_nbr")
            if area and phone:
                transmitter.contact_phone = f"({area}) {phone[:3]}-{phone[3:]}" if len(phone) >= 7 else f"({area}) {phone}"
            transmitter.contact_email = _get_text(cntc, "cntc_email_area")

    # ── Find T4 return ───────────────────────────────────────
    employees = []
    summary = None

    # Navigate: Submission > Return > T4
    t4_return = None
    for ret in root.findall("Return"):
        t4 = ret.find("T4")
        if t4 is not None:
            t4_return = t4
            break

    if t4_return is None:
        return transmitter, employees, summary

    # ── Parse T4Slips ────────────────────────────────────────
    for slip in t4_return.findall("T4Slip"):
        emp = T4Employee()

        # Name
        name_el = slip.find("EMPE_NM")
        if name_el is not None:
            emp.surname = _get_text(name_el, "snm")
            emp.given_name = _get_text(name_el, "gvn_nm")
            emp.initial = _get_text(name_el, "init")

        # Address
        addr_el = slip.find("EMPE_ADDR")
        if addr_el is not None:
            emp.addr_line1 = _get_text(addr_el, "addr_l1_txt")
            emp.addr_line2 = _get_text(addr_el, "addr_l2_txt")
            emp.city = _get_text(addr_el, "cty_nm")
            emp.province = _get_text(addr_el, "prov_cd")
            emp.country = _get_text(addr_el, "cntry_cd")
            emp.postal_code = _get_text(addr_el, "pstl_cd")

        # Core fields
        emp.sin = _get_text(slip, "sin")
        emp.employee_number = _get_text(slip, "empe_nbr")
        emp.bn = _get_text(slip, "bn")
        emp.empt_prov_cd = _get_text(slip, "empt_prov_cd")
        emp.cpp_qpp_exempt = _get_text(slip, "cpp_qpp_xmpt_cd")
        emp.ei_exempt = _get_text(slip, "ei_xmpt_cd")
        emp.pip_exempt = _get_text(slip, "prov_pip_xmpt_cd")
        emp.employment_code = _get_text(slip, "empt_cd")
        emp.report_type = _get_text(slip, "rpt_tcd")
        emp.dental_code = _get_text(slip, "empr_dntl_ben_rpt_cd")
        emp.rpp_dpsp_nbr = _get_text(slip, "rpp_dpsp_rgst_nbr")

        # T4 Amounts
        amt_el = slip.find("T4_AMT")
        if amt_el is not None:
            for child in amt_el:
                tag = child.tag
                val = (child.text or "").strip()
                if val:
                    emp.amounts[tag] = val

        # Other Information
        oth_el = slip.find("OTH_INFO")
        if oth_el is not None:
            for child in oth_el:
                tag = child.tag
                val = (child.text or "").strip()
                if val:
                    emp.oth_info[tag] = val

        employees.append(emp)

    # ── Parse T4Summary ──────────────────────────────────────
    summ_el = t4_return.find("T4Summary")
    if summ_el is not None:
        summary = T4Summary()
        summary.bn = _get_text(summ_el, "bn")
        summary.tax_year = _get_text(summ_el, "tx_yr")
        summary.slip_count = _get_text(summ_el, "slp_cnt")
        summary.report_type = _get_text(summ_el, "rpt_tcd")

        name_el = summ_el.find("EMPR_NM")
        if name_el is not None:
            summary.employer_name = _get_text(name_el, "l1_nm")
            summary.employer_name2 = _get_text(name_el, "l2_nm")
            summary.employer_name3 = _get_text(name_el, "l3_nm")

        addr_el = summ_el.find("EMPR_ADDR")
        if addr_el is not None:
            summary.employer_addr_line1 = _get_text(addr_el, "addr_l1_txt")
            summary.employer_addr_line2 = _get_text(addr_el, "addr_l2_txt")
            summary.employer_city = _get_text(addr_el, "cty_nm")
            summary.employer_province = _get_text(addr_el, "prov_cd")
            summary.employer_country = _get_text(addr_el, "cntry_cd")
            summary.employer_postal = _get_text(addr_el, "pstl_cd")

        cntc = summ_el.find("CNTC")
        if cntc is not None:
            summary.contact_name = _get_text(cntc, "cntc_nm")
            area = _get_text(cntc, "cntc_area_cd")
            phone = _get_text(cntc, "cntc_phn_nbr")
            if area and phone:
                summary.contact_phone = f"({area}) {phone[:3]}-{phone[3:]}" if len(phone) >= 7 else f"({area}) {phone}"
            summary.contact_email = _get_text(cntc, "cntc_email_area")

        totals_el = summ_el.find("T4_TAMT")
        if totals_el is not None:
            for child in totals_el:
                tag = child.tag
                val = (child.text or "").strip()
                if val:
                    summary.totals[tag] = val

    return transmitter, employees, summary


# ──────────────────────────────────────────────────────────────────────
# Report Formatting
# ──────────────────────────────────────────────────────────────────────

def _fmt_money(value: str) -> str:
    """Format a numeric string as currency."""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return value


def _fmt_sin(sin: str) -> str:
    """Format SIN as XXX-XXX-XXX."""
    if len(sin) == 9 and sin.isdigit():
        return f"{sin[:3]}-{sin[3:6]}-{sin[6:]}"
    return sin


def generate_text_report(
    transmitter: T4Transmitter | None,
    employees: list[T4Employee],
    summary: T4Summary | None,
) -> str:
    """Generate a formatted text report from parsed T4 data."""
    lines = []
    w = 70  # report width

    # ── Header ───────────────────────────────────────────────
    lines.append("=" * w)
    lines.append("T4 STATEMENT OF REMUNERATION PAID")

    if summary:
        if summary.tax_year:
            lines.append(f"Tax Year: {summary.tax_year}")
        employer = summary.employer_name
        if summary.employer_name2:
            employer += f" {summary.employer_name2}"
        if summary.employer_name3:
            employer += f" {summary.employer_name3}"
        lines.append(f"Employer: {employer}")
        lines.append(f"Business Number: {summary.bn}")
        if summary.contact_name:
            contact_line = f"Contact: {summary.contact_name}"
            if summary.contact_phone:
                contact_line += f"  |  {summary.contact_phone}"
            lines.append(contact_line)
        if summary.contact_email:
            lines.append(f"Email: {summary.contact_email}")

    lines.append(f"Total Employees: {len(employees)}")
    lines.append("=" * w)

    # ── Individual T4 Slips ──────────────────────────────────
    for i, emp in enumerate(employees, 1):
        lines.append("")
        lines.append(f"T4 #{i}")
        lines.append("-" * w)

        # Name
        name_parts = [emp.surname]
        if emp.given_name:
            name_parts.append(emp.given_name)
        if emp.initial:
            name_parts[0] = emp.surname + ","
            name_parts.append(emp.initial + ".")
        else:
            name_parts[0] = emp.surname + ","
        lines.append(f"  Employee:       {' '.join(name_parts)}")

        # SIN
        lines.append(f"  SIN:            {_fmt_sin(emp.sin)}")

        # Employee number
        if emp.employee_number:
            lines.append(f"  Employee #:     {emp.employee_number}")

        # Address
        addr_parts = []
        if emp.addr_line1:
            addr_parts.append(emp.addr_line1)
        if emp.addr_line2:
            addr_parts.append(emp.addr_line2)
        city_line = ""
        if emp.city:
            city_line = emp.city
        if emp.province:
            city_line += f", {emp.province}" if city_line else emp.province
        if emp.postal_code:
            city_line += f"  {emp.postal_code}" if city_line else emp.postal_code
        if addr_parts:
            lines.append(f"  Address:        {addr_parts[0]}")
            for extra in addr_parts[1:]:
                lines.append(f"                  {extra}")
            if city_line:
                lines.append(f"                  {city_line}")
        elif city_line:
            lines.append(f"  Address:        {city_line}")

        lines.append("")

        # Status fields
        prov_name = PROVINCE_NAMES.get(emp.empt_prov_cd, emp.empt_prov_cd)
        lines.append(f"  Prov. of Employment:  {emp.empt_prov_cd} ({prov_name})")

        exempt_line = f"  CPP/QPP Exempt: {'Yes' if emp.cpp_qpp_exempt == '1' else 'No'}"
        exempt_line += f"  |  EI Exempt: {'Yes' if emp.ei_exempt == '1' else 'No'}"
        if emp.pip_exempt:
            exempt_line += f"  |  PPIP Exempt: {'Yes' if emp.pip_exempt == '1' else 'No'}"
        lines.append(exempt_line)

        if emp.employment_code:
            code_desc = EMPLOYMENT_CODES.get(emp.employment_code, "")
            lines.append(f"  Employment Code:      {emp.employment_code}" +
                         (f" — {code_desc}" if code_desc else ""))

        if emp.dental_code:
            dental_desc = DENTAL_CODES.get(emp.dental_code, "")
            lines.append(f"  Dental Benefits:      Code {emp.dental_code}" +
                         (f" — {dental_desc}" if dental_desc else ""))

        if emp.rpp_dpsp_nbr:
            lines.append(f"  RPP/DPSP Reg #:       {emp.rpp_dpsp_nbr}")

        # Amount boxes
        if emp.amounts:
            lines.append("")
            for field_name, value in emp.amounts.items():
                if field_name in T4_AMOUNT_BOXES:
                    box_num, label = T4_AMOUNT_BOXES[field_name]
                    lines.append(f"  Box {box_num:<4}  {label:<32}  {_fmt_money(value):>12}")
                else:
                    lines.append(f"  {field_name:<38}  {_fmt_money(value):>12}")

        # Other information
        if emp.oth_info:
            lines.append("")
            lines.append("  Other Information:")
            for field_name, value in emp.oth_info.items():
                if field_name in OTH_INFO_BOXES:
                    code, label = OTH_INFO_BOXES[field_name]
                    lines.append(f"    Code {code:<4}  {label:<30}  {_fmt_money(value):>12}")
                else:
                    lines.append(f"    {field_name:<36}  {_fmt_money(value):>12}")

        lines.append("-" * w)

    # ── Summary Totals ───────────────────────────────────────
    if summary and summary.totals:
        lines.append("")
        lines.append("=" * w)
        lines.append("T4 SUMMARY TOTALS")
        lines.append("=" * w)

        total_labels = {
            "tot_empt_incamt":    "Total Employment Income",
            "tot_empe_cpp_amt":   "Total Employee CPP",
            "tot_empe_cppe_amt":  "Total Employee CPP2",
            "tot_empe_eip_amt":   "Total Employee EI",
            "tot_rpp_cntrb_amt":  "Total RPP Contributions",
            "tot_itx_ddct_amt":   "Total Income Tax Deducted",
            "tot_padj_amt":       "Total Pension Adjustments",
            "tot_empr_cpp_amt":   "Total Employer CPP",
            "tot_empr_cppe_amt":  "Total Employer CPP2",
            "tot_empr_eip_amt":   "Total Employer EI",
        }
        for field_name, value in summary.totals.items():
            label = total_labels.get(field_name, field_name)
            lines.append(f"  {label:<40}  {_fmt_money(value):>14}")

        lines.append("=" * w)

    # ── Footer ───────────────────────────────────────────────
    lines.append("")
    lines.append(f"Report generated from CRA T4 XML — {len(employees)} slip(s)")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# CSV Export
# ──────────────────────────────────────────────────────────────────────

def generate_csv_report(
    employees: list[T4Employee],
    summary: T4Summary | None,
) -> str:
    """Generate a CSV with one row per employee and all T4 box values as columns."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Build header — fixed columns + all amount boxes + all oth_info codes found
    fixed_cols = [
        "Slip #", "Surname", "Given Name", "Initial", "SIN",
        "Employee #", "BN", "Address Line 1", "Address Line 2",
        "City", "Province", "Postal Code",
        "Employment Province", "CPP/QPP Exempt", "EI Exempt",
        "Employment Code", "Dental Code", "RPP/DPSP Reg #",
        "Report Type",
    ]

    # Collect all amount and oth_info fields across all employees
    all_amount_fields = []
    all_oth_fields = []
    seen_amounts = set()
    seen_oth = set()
    for emp in employees:
        for f in emp.amounts:
            if f not in seen_amounts:
                seen_amounts.add(f)
                all_amount_fields.append(f)
        for f in emp.oth_info:
            if f not in seen_oth:
                seen_oth.add(f)
                all_oth_fields.append(f)

    # Amount column headers with box numbers
    amount_headers = []
    for f in all_amount_fields:
        if f in T4_AMOUNT_BOXES:
            box, label = T4_AMOUNT_BOXES[f]
            amount_headers.append(f"Box {box} - {label}")
        else:
            amount_headers.append(f)

    # Oth info column headers with codes
    oth_headers = []
    for f in all_oth_fields:
        if f in OTH_INFO_BOXES:
            code, label = OTH_INFO_BOXES[f]
            oth_headers.append(f"Code {code} - {label}")
        else:
            oth_headers.append(f)

    # Write header
    writer.writerow(fixed_cols + amount_headers + oth_headers)

    # Write rows
    for i, emp in enumerate(employees, 1):
        row = [
            i,
            emp.surname,
            emp.given_name,
            emp.initial,
            emp.sin,
            emp.employee_number,
            emp.bn,
            emp.addr_line1,
            emp.addr_line2,
            emp.city,
            emp.province,
            emp.postal_code,
            emp.empt_prov_cd,
            "Yes" if emp.cpp_qpp_exempt == "1" else "No",
            "Yes" if emp.ei_exempt == "1" else "No",
            emp.employment_code,
            emp.dental_code,
            emp.rpp_dpsp_nbr,
            emp.report_type,
        ]

        # Amount values
        for f in all_amount_fields:
            row.append(emp.amounts.get(f, ""))

        # Oth info values
        for f in all_oth_fields:
            row.append(emp.oth_info.get(f, ""))

        writer.writerow(row)

    return output.getvalue()


# ──────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────

def generate_report_from_file(
    filepath: Path,
    output_format: str = "text",
) -> tuple[str, str, int]:
    """
    Read a T4 XML file and generate a report.

    Args:
        filepath: Path to T4 XML file
        output_format: "text" or "csv"

    Returns:
        (report_content, output_filename, employee_count)
    """
    content = filepath.read_text(encoding="utf-8")

    if "<T4Slip>" not in content and "<T4Summary>" not in content:
        raise ValueError(f"{filepath.name} does not appear to be a T4 XML file")

    transmitter, employees, summary = parse_t4_xml(content)

    if not employees:
        raise ValueError(f"No T4 slips found in {filepath.name}")

    if output_format == "csv":
        report = generate_csv_report(employees, summary)
        ext = ".csv"
    else:
        report = generate_text_report(transmitter, employees, summary)
        ext = "_report.txt"

    output_name = filepath.stem + ext
    return report, output_name, len(employees)
