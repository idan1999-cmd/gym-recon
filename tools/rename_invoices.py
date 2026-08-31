#!/usr/bin/env python3
"""
tools/rename_invoices.py — Standardizes invoice filenames.
Renames invoices in a given directory to:
  'החשבונית של <שם המאמן/ספק> <מספר חשבונית>.pdf'
"""
import os
import sys
import json
import argparse
import re

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'core'))
from common import load_aliases, resolve_trainer

def sanitize_filename(name):
    return re.sub(r'[/\:*?"<>|]', '-', name).strip()

def normalize_invoices(invoices_dir, aliases=None):
    if not os.path.isdir(invoices_dir):
        return []
    if aliases is None:
        aliases = load_aliases()

    import pypdf
    results = []
    for fname in sorted(os.listdir(invoices_dir)):
        if fname.startswith('.') or not fname.lower().endswith('.pdf'):
            continue
        path = os.path.join(invoices_dir, fname)
        try:
            reader = pypdf.PdfReader(path)
            text = ''
            for page in reader.pages[:2]:
                text += (page.extract_text() or '') + '
'
        except Exception:
            text = ''

        detected_name = None
        for t in aliases.get('trainers', []):
            cname = t['canonical_name']
            if cname in text or cname in fname:
                detected_name = cname
                break
            for a in t.get('aliases', []):
                if a in text or a in fname:
                    detected_name = cname
                    break
            if detected_name:
                break

        doc_num = None
        m_doc = re.search(r'(?:חשבונית מס|חשבון עסקה|קבלה|דרישת תשלום|חשבון)\s*(?:מס['״]?)?\s*#?([0-9\-_/]+)', text)
        if m_doc:
            doc_num = sanitize_filename(m_doc.group(1))
        if not doc_num:
            m_f = re.search(r'([0-9\-_]+)', fname)
            if m_f:
                doc_num = sanitize_filename(m_f.group(1))

        if detected_name and doc_num:
            new_name = f'החשבונית של {detected_name} {doc_num}.pdf'
            new_path = os.path.join(invoices_dir, new_name)
            if new_path != path:
                os.rename(path, new_path)
                results.append({'old': fname, 'new': new_name, 'trainer': detected_name, 'doc': doc_num})
    return results

def main():
    parser = argparse.ArgumentParser(description='Rename invoice PDFs to standard format')
    parser.add_argument('--invoices', required=True, help='Path to invoices directory')
    args = parser.parse_args()
    aliases = load_aliases()
    res = normalize_invoices(args.invoices, aliases)
    print(json.dumps({'ok': True, 'renamed': res}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
