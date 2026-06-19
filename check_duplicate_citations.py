#!/usr/bin/env python3
"""
Check if the .tex file cites the same paper using two different citation keys.
This is a real problem if the same paper appears under two different \citep{key1} and \citep{key2}.
"""

import re
import os

TEX_PATH = r"D:\科研\智能体记忆机制\sample-acmsmall-submission.tex"
BIB_PATH = r"D:\科研\智能体记忆机制\references.bib"

def parse_bib(bib_path):
    """Parse .bib file into entries keyed by citation key."""
    with open(bib_path, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = {}
    pattern = r'@(\w+)\s*\{\s*([^,]+)\s*,\s*(.+?)\n\}'
    for m in re.finditer(pattern, content, re.DOTALL):
        key = m.group(2).strip()
        fields_str = m.group(3)

        entry = {'type': m.group(1), 'key': key}

        # Parse fields
        field_pattern = r'(\w+)\s*=\s*[{"]([^}"]*(?:{[^}]*}[^}"]*)*)[}"]'
        for fm in re.finditer(field_pattern, fields_str):
            fname = fm.group(1).strip()
            fval = fm.group(2).strip()
            fval = re.sub(r'\s+', ' ', fval)
            entry[fname] = fval

        entries[key] = entry
    return entries

def extract_cited_keys(tex_path):
    """Extract all citation keys from a .tex file."""
    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    keys = set()
    # Match \citep{key1,key2,...} and \citet{key1,key2,...}
    for m in re.finditer(r'\\citep\{([^}]+)\}', content):
        for k in m.group(1).split(','):
            keys.add(k.strip())
    for m in re.finditer(r'\\citet\{([^}]+)\}', content):
        for k in m.group(1).split(','):
            keys.add(k.strip())
    return keys

def title_similarity(t1, t2):
    """Compute a simple similarity score between two titles."""
    if not t1 or not t2:
        return 0
    # Normalize
    def norm(t):
        t = t.lower()
        t = re.sub(r'[^a-z0-9\s]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t
    n1, n2 = norm(t1), norm(t2)
    # Check if one contains the other
    if n1 in n2 or n2 in n1:
        return 1.0
    # Word overlap
    w1 = set(n1.split())
    w2 = set(n2.split())
    if not w1 or not w2:
        return 0
    overlap = len(w1 & w2)
    return overlap / min(len(w1), len(w2))

def main():
    bib = parse_bib(BIB_PATH)
    cited = extract_cited_keys(TEX_PATH)

    print(f"=== Summary ===")
    print(f"Total entries in .bib: {len(bib)}")
    print(f"Unique citation keys in .tex: {len(cited)}")

    # Check which cited keys exist in bib
    missing = cited - set(bib.keys())
    uncited = set(bib.keys()) - cited

    print(f"Keys cited in .tex but NOT in .bib: {len(missing)}")
    if missing:
        for k in sorted(missing):
            print(f"  MISSING: {k}")

    print(f"Keys in .bib but NOT cited in .tex: {len(uncited)}")
    print()

    # Now: find pairs of DIFFERENT keys in .bib that map to the SAME paper
    # Group by arxiv ID or DOI, and by title similarity
    print("=== Searching for duplicate papers (same paper, different keys) ===")

    # Method 1: Same arXiv eprint
    by_eprint = {}
    for key, entry in bib.items():
        eprint = entry.get('eprint', '')
        if eprint:
            eprint = re.sub(r'^arXiv\.', '', eprint, flags=re.IGNORECASE)
            if eprint not in by_eprint:
                by_eprint[eprint] = []
            by_eprint[eprint].append(key)

    # Method 2: Same DOI
    by_doi = {}
    for key, entry in bib.items():
        doi = entry.get('doi', '')
        if doi:
            if doi not in by_doi:
                by_doi[doi] = []
            by_doi[doi].append(key)

    # Method 3: Title similarity (>80%)
    keys_list = list(bib.keys())
    title_pairs = []
    for i in range(len(keys_list)):
        for j in range(i+1, len(keys_list)):
            k1, k2 = keys_list[i], keys_list[j]
            t1 = bib[k1].get('title', '')
            t2 = bib[k2].get('title', '')
            sim = title_similarity(t1, t2)
            if sim > 0.8:
                title_pairs.append((k1, k2, sim))

    # Collect all duplicate pairs
    all_dup_pairs = set()

    for eprint, keys in by_eprint.items():
        if len(keys) > 1:
            for i in range(len(keys)):
                for j in range(i+1, len(keys)):
                    all_dup_pairs.add(tuple(sorted([keys[i], keys[j]])))

    for doi, keys in by_doi.items():
        if len(keys) > 1:
            for i in range(len(keys)):
                for j in range(i+1, len(keys)):
                    all_dup_pairs.add(tuple(sorted([keys[i], keys[j]])))

    for k1, k2, sim in title_pairs:
        all_dup_pairs.add(tuple(sorted([k1, k2])))

    print(f"\nTotal duplicate pairs found: {len(all_dup_pairs)}")
    print()

    # CRITICAL CHECK: Are BOTH keys of a duplicate pair cited in the .tex?
    problematic_pairs = []
    harmless_pairs = []

    for k1, k2 in sorted(all_dup_pairs):
        both_cited = (k1 in cited) and (k2 in cited)
        one_cited = (k1 in cited) or (k2 in cited)
        none_cited = not one_cited

        t1 = bib[k1].get('title', '???')
        t2 = bib[k2].get('title', '???')

        if both_cited:
            problematic_pairs.append((k1, k2, t1))
            print(f"!! PROBLEM: Both keys CITED in .tex!")
            print(f"   key1: {k1} → \"{t1[:100]}\"")
            print(f"   key2: {k2} → \"{t2[:100]}\"")
            print()
        elif one_cited:
            harmless_pairs.append((k1, k2))
            cited_key = k1 if k1 in cited else k2
            uncited_key = k2 if k1 in cited else k1
            print(f"[OK] Only '{cited_key}' is cited (not '{uncited_key}')")
            print(f"   {cited_key} → \"{bib[cited_key].get('title', '???')[:100]}\"")
            print()
        else:
            print(f"[info] NEITHER cited: {k1} / {k2} (both unused in .tex)")
            print()

    print("=" * 60)
    print(f"FINAL VERDICT:")
    print(f"  !! Problematic (both keys cited): {len(problematic_pairs)}")
    print(f"  [OK] Harmless (only one key cited): {len(harmless_pairs)}")

    if problematic_pairs:
        print(f"\n  !! THESE NEED FIXING - the .tex cites the same paper under two different keys:")
        for k1, k2, title in problematic_pairs:
            print(f"     - '{k1}' and '{k2}' both cite: \"{title[:120]}\"")
    else:
        print(f"\n  [OK] All clear! No paper is cited under two different keys.")

if __name__ == '__main__':
    main()
