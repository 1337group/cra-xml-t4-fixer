# CRA T4 XML Fixer

**Free tool for Canadian payroll staff** — fix T4 XML files so CRA Internet File Transfer actually accepts them.

Canada Revenue Agency rejects T4 XML submissions that contain optional fields with zero or empty values. Most payroll software (Jonas, Ceridian, ADP, Sage, QuickBooks, etc.) exports every field regardless — this tool strips the invalid ones so your upload passes validation on the first try.

> **No technical knowledge required.** Download, open your XML file, click Fix. That's it.

---

## [![Download CRA T4 XML Fixer](https://img.shields.io/badge/DOWNLOAD-CRA--T4--Fixer.exe-blue?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/1337group/cra-xml-t4-fixer/releases/latest/download/CRA-T4-Fixer.exe)

**Windows:** Click the button above to download. No installation needed — just double-click and run.

**Mac/Linux:** Use the command-line version below (Python 3.10+ required).

---

## The Problem

Your payroll software generates T4 XML like this for CRA Internet File Transfer:

```xml
<T4_AMT>
<empt_incamt>61344.05</empt_incamt>
<cpp_cntrb_amt>3441.87</cpp_cntrb_amt>
<cppe_cntrb_amt>0.00</cppe_cntrb_amt>     ← CRA rejects this
<qpp_cntrb_amt>0.00</qpp_cntrb_amt>       ← and this
<qppe_cntrb_amt>0.00</qppe_cntrb_amt>     ← and this
<empe_eip_amt>1005.96</empe_eip_amt>
<rpp_cntrb_amt>0.00</rpp_cntrb_amt>       ← and this
<itx_ddct_amt>9283.69</itx_ddct_amt>
<ei_insu_ern_amt>61344.05</ei_insu_ern_amt>
<cpp_qpp_ern_amt>61344.05</cpp_qpp_ern_amt>
<unn_dues_amt>0.00</unn_dues_amt>         ← and this
<chrty_dons_amt>0.00</chrty_dons_amt>      ← and this
<padj_amt>0.00</padj_amt>                 ← and this
<prov_pip_amt>0.00</prov_pip_amt>          ← and this
<prov_insu_ern_amt>0.00</prov_insu_ern_amt> ← and this
</T4_AMT>
```

CRA's validation rule (since October 2025): **"remove all optional fields without values"**. Your payroll software doesn't do this — so CRA rejects your file.

## The Fix

### Windows (GUI) — For Payroll Staff

1. Download `CRA-T4-Fixer.exe` (button above)
2. Double-click to open
3. Click **Browse XML Files** and select your T4 XML file(s)
4. Click **Fix Files**
5. Upload the fixed file to CRA Internet File Transfer

A backup of your original file is created automatically (`.bak`).

### Command Line — For IT Staff

```bash
python3 fix_t4_xml.py YourT4File.xml
```

After fixing:

```xml
<T4_AMT>
<empt_incamt>61344.05</empt_incamt>
<cpp_cntrb_amt>3441.87</cpp_cntrb_amt>
<empe_eip_amt>1005.96</empe_eip_amt>
<itx_ddct_amt>9283.69</itx_ddct_amt>
<ei_insu_ern_amt>61344.05</ei_insu_ern_amt>
<cpp_qpp_ern_amt>61344.05</cpp_qpp_ern_amt>
</T4_AMT>
```

All required fields preserved. All zero optional fields removed. CRA accepts the upload.

## Command Line Usage

```bash
# Fix one file (creates .bak backup automatically)
python3 fix_t4_xml.py T4_2025.xml

# Fix multiple files
python3 fix_t4_xml.py company1.xml company2.xml company3.xml

# Dry run — see what would change without modifying anything
python3 fix_t4_xml.py --check T4_2025.xml

# Validate against official CRA XSD schema (no changes)
python3 fix_t4_xml.py --validate --check T4_2025.xml

# Fix AND validate against CRA schema
python3 fix_t4_xml.py --validate T4_2025.xml

# Point to your own schema download
python3 fix_t4_xml.py --validate --schema /path/to/T619_T4.xsd T4_2025.xml

# Skip backup creation
python3 fix_t4_xml.py --no-backup T4_2025.xml
```

## What It Fixes

| Issue | Details |
|-------|---------|
| **Negative amounts** | Removes values like `-622.88` — CRA schema rejects negatives entirely. Warns that Pension Adjustment Reversals belong on a T10, not T4. |
| Optional amounts = `0.00` | Removes `cppe_cntrb_amt`, `qpp_cntrb_amt`, `qppe_cntrb_amt`, `rpp_cntrb_amt`, `unn_dues_amt`, `chrty_dons_amt`, `padj_amt`, `prov_pip_amt`, `prov_insu_ern_amt`, and others when zero |
| Empty `<OTH_INFO>` blocks | Removes empty Other Information sections |
| `rpp_dpsp_rgst_nbr=0000000` | Optional registration number, all zeros |
| `empt_cd=00` | Invalid employment code (valid: 11–17) |
| `prov_pip_xmpt_cd=0` | Optional provincial PIP exemption |
| `cntc_extn_nbr=00000` | Optional contact extension, all zeros |
| `pprtr_2_sin=000000000` | Optional second proprietor SIN, all zeros |
| Summary totals = `0.00` | Removes zero-value summary total fields |

**Required fields are never removed:** `sin`, `bn`, `cpp_qpp_xmpt_cd`, `ei_xmpt_cd`, `rpt_tcd`, `empt_prov_cd`, `empr_dntl_ben_rpt_cd`, `ei_insu_ern_amt`, `cpp_qpp_ern_amt`, `tx_yr`, `slp_cnt`, etc.

## Common Payroll Software Affected

This issue affects XML exports from most Canadian payroll systems including:

- **Jonas Software** (Jonas Construction, Jonas Premier)
- **Sage 50 / Sage 300** (Simply Accounting)
- **Ceridian Dayforce / Powerpay**
- **ADP WFN / ADP Run**
- **QuickBooks Desktop / Online**
- **PaymentEvolution**
- **Payworks**
- **Wagepoint**
- **Rise People**

If your payroll software generates T4 XML with zero-value optional fields, this tool will fix it.

## Frequently Asked Questions

**Is this safe to use?**
Yes. The tool only removes invalid zero-value optional fields. It never modifies your actual employee data (names, SINs, income amounts, tax deductions). A backup of the original file is always created.

**Why does CRA reject my T4 XML?**
Since October 2025, CRA's Internet File Transfer validation requires that optional XML fields with no value be completely removed from the file. Most payroll software still includes these empty fields, causing upload failures.

**Do I need to install anything?**
No. The Windows `.exe` is fully portable — just download and run. No Python, no install, no admin rights needed.

**Can I preview changes before fixing?**
Yes. Use the **Dry Run (Preview)** button in the GUI, or `--check` on the command line, to see exactly what would change without modifying your file.

## Requirements

**Windows exe:** None — fully portable, no install needed.

**Command line:** Python 3.10+, no external dependencies (stdlib only).

## CRA Spec Reference

- [T4 2026 XML Specification](https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/t619-2026/t4-2026.html)
- [XML Specifications Overview](https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/xml-specs.html)

## License

MIT
