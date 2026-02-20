# t4-fixer

Fix CRA T4 XML files for Internet File Transfer submission.

Canada Revenue Agency **rejects** T4 XML submissions containing optional fields with zero or empty values. Most payroll software exports every field regardless — this script strips the invalid ones so your upload passes validation.

## The Problem

Your payroll software generates XML like this:

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

CRA's validation rule (since October 2025): **"remove all optional fields without values"**.

## The Fix

```bash
python3 fix_t4_xml.py YourT4File.xml
```

After:

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

## Usage

```bash
# Fix one file (creates .bak backup automatically)
python3 fix_t4_xml.py T4_2025.xml

# Fix multiple files
python3 fix_t4_xml.py company1.xml company2.xml company3.xml

# Dry run — see what would change without modifying anything
python3 fix_t4_xml.py --check T4_2025.xml

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

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## CRA Spec Reference

- [T4 2026 XML Specification](https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/t619-2026/t4-2026.html)
- [XML Specifications Overview](https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/xml-specs.html)

## License

MIT
