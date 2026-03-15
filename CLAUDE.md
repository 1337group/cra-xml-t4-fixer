# CRA T4 XML Fixer

Tool for Canadian payroll staff to fix T4 XML files so CRA Internet File Transfer accepts them. Strips invalid zero-value optional fields that most payroll software (Jonas, Sage, ADP, etc.) incorrectly exports.

## Tech Stack

- **Python 3.10+** (stdlib only, no external dependencies)
- **tkinter** for GUI (packaged as Windows .exe via PyInstaller)
- **CRA XSD schemas** bundled for validation

## Key Files

```
fix_t4_xml.py        # Core CLI — fix and validate T4 XML files
t4_fixer_gui.py      # Tkinter GUI wrapper (also builds to .exe)
t4_report.py         # Convert T4 XML to human-readable reports / CSV
schemas/             # Official CRA XSD schemas for validation
```

## Build & Run

```bash
# CLI usage
python3 fix_t4_xml.py T4FILE.xml
python3 fix_t4_xml.py --check T4FILE.xml       # dry-run
python3 fix_t4_xml.py --validate T4FILE.xml     # validate against CRA XSD

# GUI
python3 t4_fixer_gui.py

# Build Windows .exe (PyInstaller)
pyinstaller --onefile --windowed t4_fixer_gui.py
```

## Related

- GitHub: `1337group/cra-xml-t4-fixer`
- CRA T4 2026 XML Spec: https://www.canada.ca/en/revenue-agency/services/e-services/filing-information-returns-electronically-t4-t5-other-types-returns-overview/t619-2026/t4-2026.html
