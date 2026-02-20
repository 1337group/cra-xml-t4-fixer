#!/usr/bin/env python3
"""
CRA T4 XML Fixer — GUI
Drag-and-drop or browse for T4 XML files, fix them with one click.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from pathlib import Path

# Ensure we can import the core logic regardless of how we're launched
if getattr(sys, "frozen", False):
    _SCRIPT_DIR = Path(sys._MEIPASS)
else:
    _SCRIPT_DIR = Path(__file__).parent

sys.path.insert(0, str(_SCRIPT_DIR))
from fix_t4_xml import fix_t4_xml, validate_xml_wellformed, validate_xsd, find_xmllint, __version__

SCHEMA_DIR = _SCRIPT_DIR / "schemas"
T4_SCHEMA = SCHEMA_DIR / "T619_T4.xsd"


class T4FixerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"CRA T4 XML Fixer v{__version__}")
        self.root.geometry("720x560")
        self.root.minsize(600, 400)
        self.root.configure(bg="#f5f5f5")

        self.files: list[Path] = []

        self._build_ui()

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────
        header = tk.Frame(self.root, bg="#1a1a2e", pady=12)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="CRA T4 XML Fixer",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg="#1a1a2e",
        ).pack()
        tk.Label(
            header,
            text="Fix optional zero-value fields that cause CRA rejection",
            font=("Segoe UI", 9),
            fg="#aaaaaa",
            bg="#1a1a2e",
        ).pack()

        # ── File selection ──────────────────────────────────────
        file_frame = tk.Frame(self.root, bg="#f5f5f5", pady=8, padx=16)
        file_frame.pack(fill=tk.X)

        btn_frame = tk.Frame(file_frame, bg="#f5f5f5")
        btn_frame.pack(fill=tk.X)

        self.browse_btn = ttk.Button(
            btn_frame, text="Browse XML Files...", command=self._browse_files
        )
        self.browse_btn.pack(side=tk.LEFT)

        self.clear_btn = ttk.Button(
            btn_frame, text="Clear", command=self._clear_files
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.file_label = tk.Label(
            file_frame,
            text="No files selected",
            font=("Segoe UI", 9),
            fg="#666666",
            bg="#f5f5f5",
            anchor="w",
        )
        self.file_label.pack(fill=tk.X, pady=(6, 0))

        # ── Options ─────────────────────────────────────────────
        opt_frame = tk.Frame(self.root, bg="#f5f5f5", padx=16)
        opt_frame.pack(fill=tk.X)

        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opt_frame, text="Create .bak backup files", variable=self.backup_var
        ).pack(side=tk.LEFT)

        self.validate_var = tk.BooleanVar(value=False)
        has_schema = T4_SCHEMA.exists()
        has_xmllint = find_xmllint() is not None
        can_validate = has_schema and has_xmllint
        cb = ttk.Checkbutton(
            opt_frame,
            text="Validate against CRA XSD schema",
            variable=self.validate_var,
            state="normal" if can_validate else "disabled",
        )
        cb.pack(side=tk.LEFT, padx=(16, 0))
        if not can_validate:
            reason = "(schema not found)" if not has_schema else "(xmllint not installed)"
            tk.Label(
                opt_frame,
                text=reason,
                font=("Segoe UI", 8),
                fg="#999999",
                bg="#f5f5f5",
            ).pack(side=tk.LEFT, padx=(4, 0))

        # ── Action buttons ──────────────────────────────────────
        action_frame = tk.Frame(self.root, bg="#f5f5f5", pady=8, padx=16)
        action_frame.pack(fill=tk.X)

        self.fix_btn = ttk.Button(
            action_frame, text="Fix Files", command=self._run_fix, state="disabled"
        )
        self.fix_btn.pack(side=tk.LEFT)

        self.check_btn = ttk.Button(
            action_frame,
            text="Dry Run (Preview)",
            command=self._run_check,
            state="disabled",
        )
        self.check_btn.pack(side=tk.LEFT, padx=(8, 0))

        # ── Log output ──────────────────────────────────────────
        log_frame = tk.Frame(self.root, bg="#f5f5f5")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 16))

        self.log = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            relief=tk.FLAT,
            state="disabled",
            wrap=tk.WORD,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

        # Tag styles for colored output
        self.log.tag_configure("success", foreground="#4ec9b0")
        self.log.tag_configure("warning", foreground="#dcdcaa")
        self.log.tag_configure("error", foreground="#f44747")
        self.log.tag_configure("info", foreground="#569cd6")
        self.log.tag_configure("dim", foreground="#808080")

    # ── File handling ───────────────────────────────────────────

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Select T4 XML files",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if paths:
            self.files = [Path(p) for p in paths]
            names = ", ".join(p.name for p in self.files)
            self.file_label.config(
                text=f"{len(self.files)} file(s): {names}", fg="#333333"
            )
            self.fix_btn.config(state="normal")
            self.check_btn.config(state="normal")

    def _clear_files(self):
        self.files = []
        self.file_label.config(text="No files selected", fg="#666666")
        self.fix_btn.config(state="disabled")
        self.check_btn.config(state="disabled")

    # ── Logging ─────────────────────────────────────────────────

    def _log(self, text: str, tag: str = ""):
        self.log.config(state="normal")
        if tag:
            self.log.insert(tk.END, text + "\n", tag)
        else:
            self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def _log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.config(state="disabled")

    # ── Processing ──────────────────────────────────────────────

    def _set_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.fix_btn.config(state=state)
        self.check_btn.config(state=state)
        self.browse_btn.config(state=state)

    def _run_fix(self):
        self._process(dry_run=False)

    def _run_check(self):
        self._process(dry_run=True)

    def _process(self, dry_run: bool):
        if not self.files:
            return

        self._set_buttons(False)
        self._log_clear()

        mode = "DRY RUN" if dry_run else "FIX"
        self._log(f"{'─' * 50}", "dim")
        self._log(f"  {mode} — {len(self.files)} file(s)", "info")
        self._log(f"{'─' * 50}", "dim")

        # Run in a thread so the UI doesn't freeze
        thread = threading.Thread(
            target=self._process_files, args=(dry_run,), daemon=True
        )
        thread.start()

    def _process_files(self, dry_run: bool):
        import shutil

        success = 0
        failed = 0
        do_validate = self.validate_var.get()
        do_backup = self.backup_var.get()

        for filepath in self.files:
            self.root.after(0, self._log, f"\n{'─' * 50}", "dim")
            self.root.after(0, self._log, f"  {filepath.name}", "info")

            if not filepath.exists():
                self.root.after(0, self._log, "  File not found", "error")
                failed += 1
                continue

            if filepath.suffix.lower() != ".xml":
                self.root.after(0, self._log, "  Not an XML file", "error")
                failed += 1
                continue

            try:
                content = filepath.read_text(encoding="utf-8")
            except Exception as e:
                self.root.after(0, self._log, f"  Read error: {e}", "error")
                failed += 1
                continue

            if "<T4Slip>" not in content and "<T4Summary>" not in content:
                self.root.after(
                    0, self._log, "  Not a T4 XML file — skipped", "warning"
                )
                failed += 1
                continue

            # Validate-only mode
            if do_validate and dry_run:
                valid, msg = validate_xsd(
                    filepath, T4_SCHEMA if T4_SCHEMA.exists() else None
                )
                if valid:
                    self.root.after(
                        0, self._log, f"  XSD validation passed", "success"
                    )
                    success += 1
                else:
                    self.root.after(
                        0, self._log, f"  XSD validation FAILED", "error"
                    )
                    for line in msg.split("\n"):
                        self.root.after(0, self._log, f"    {line}", "error")
                    failed += 1
                continue

            original_lines = content.count("\n")
            fixed, changes, warnings = fix_t4_xml(content)

            if not changes:
                self.root.after(
                    0, self._log, "  Already compliant — no changes needed", "success"
                )
                if do_validate:
                    valid, msg = validate_xsd(
                        filepath, T4_SCHEMA if T4_SCHEMA.exists() else None
                    )
                    if valid:
                        self.root.after(
                            0, self._log, "  XSD validation passed", "success"
                        )
                    else:
                        self.root.after(
                            0, self._log, "  XSD validation FAILED", "error"
                        )
                        for line in msg.split("\n"):
                            self.root.after(0, self._log, f"    {line}", "error")
                        failed += 1
                        continue
                success += 1
                continue

            new_lines = fixed.count("\n")

            if not validate_xml_wellformed(fixed, filepath.name):
                self.root.after(
                    0,
                    self._log,
                    "  XML broken after fix — aborting this file",
                    "error",
                )
                failed += 1
                continue

            removed = original_lines - new_lines
            self.root.after(
                0,
                self._log,
                f"  Lines: {original_lines} → {new_lines} (removed {removed})",
                "dim",
            )

            for desc, count in sorted(changes.items()):
                self.root.after(
                    0, self._log, f"    {desc}: {count} removed", "success"
                )

            for w in warnings:
                self.root.after(0, self._log, f"    {w}", "warning")

            if dry_run:
                self.root.after(0, self._log, "  (dry run — no changes written)", "dim")
                success += 1
                continue

            # Backup
            if do_backup:
                backup = filepath.with_suffix(".xml.bak")
                shutil.copy2(filepath, backup)
                self.root.after(0, self._log, f"  Backup: {backup.name}", "dim")

            # Write
            filepath.write_text(fixed, encoding="utf-8")
            self.root.after(0, self._log, "  Saved", "success")

            # Post-fix XSD validation
            if do_validate:
                valid, msg = validate_xsd(
                    filepath, T4_SCHEMA if T4_SCHEMA.exists() else None
                )
                if valid:
                    self.root.after(
                        0, self._log, "  XSD validation passed", "success"
                    )
                else:
                    self.root.after(
                        0, self._log, "  XSD validation FAILED after fix", "error"
                    )
                    for line in msg.split("\n"):
                        self.root.after(0, self._log, f"    {line}", "error")
                    failed += 1
                    continue

            success += 1

        # Summary
        self.root.after(0, self._log, f"\n{'─' * 50}", "dim")
        summary = f"  Done: {success} file(s) processed"
        if failed:
            summary += f", {failed} failed"
        tag = "success" if not failed else "warning"
        self.root.after(0, self._log, summary, tag)
        self.root.after(0, self._log, f"{'─' * 50}", "dim")
        self.root.after(0, self._set_buttons, True)


def main():
    root = tk.Tk()

    # Set DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = T4FixerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
