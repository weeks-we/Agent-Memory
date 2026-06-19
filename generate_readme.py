#!/usr/bin/env python3
"""
Parse references.bib and generate a comprehensive paper-list README.md
organized by the taxonomy from the survey:
"From Historical Signals to Action Utility: A Survey of Memory Mechanisms for LLM-based Agents"
"""

import re
import os
from collections import defaultdict

BIB_PATH = r"D:\科研\智能体记忆机制\references.bib"
OUTPUT_PATH = r"D:\科研\agent-memory-survey-paper-list\README.md"

# ---------------------------------------------------------------------------
# BibTeX parser with balanced-brace handling
# ---------------------------------------------------------------------------

def parse_balanced_braces(text, start):
    """Given text and position of opening '{', return (content, end_pos)."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start+1:i], i+1
        i += 1
    return text[start+1:], len(text)

def parse_bib(bib_path):
    """Parse a .bib file into a list of entry dicts."""
    with open(bib_path, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    pos = 0
    while True:
        m = re.search(r'@(\w+)\s*\{\s*([^,]+)\s*,', content[pos:])
        if not m:
            break
        entry_type = m.group(1)
        key = m.group(2).strip()

        field_start = pos + m.end()
        entry = {'type': entry_type, 'key': key}
        pos2 = field_start

        while pos2 < len(content):
            # Skip whitespace and commas
            m2 = re.match(r'\s*,?\s*', content[pos2:])
            if m2:
                pos2 += m2.end()

            # Check for closing '}' of the entry
            if pos2 < len(content) and content[pos2] == '}':
                pos = pos2 + 1
                break

            # Match field_name =
            m3 = re.match(r'(\w+)\s*=\s*', content[pos2:])
            if not m3:
                pos2 += 1
                continue
            fname = m3.group(1).strip().lower()
            pos2 += m3.end()

            if pos2 >= len(content):
                break

            # Value: {balanced} or "quoted"
            if content[pos2] == '{':
                fval, next_pos = parse_balanced_braces(content, pos2)
                pos2 = next_pos
            elif content[pos2] == '"':
                end_quote = content.find('"', pos2+1)
                if end_quote == -1:
                    break
                fval = content[pos2+1:end_quote]
                pos2 = end_quote + 1
            else:
                m4 = re.match(r'(\S+)', content[pos2:])
                if m4:
                    fval = m4.group(1)
                    pos2 += m4.end()
                else:
                    pos2 += 1
                    continue

            fval = re.sub(r'\s+', ' ', fval.strip())
            entry[fname] = fval

        entries.append(entry)

    return entries

# ---------------------------------------------------------------------------
# URL / ID extraction
# ---------------------------------------------------------------------------

def clean_arxiv_id(raw_id):
    if not raw_id:
        return None
    raw_id = re.sub(r'^arXiv\.', '', raw_id, flags=re.IGNORECASE)
    raw_id = re.sub(r'^arxiv\.', '', raw_id, flags=re.IGNORECASE)
    return raw_id.strip()

def extract_arxiv_id(entry):
    eprint = entry.get('eprint', '')
    if eprint:
        return clean_arxiv_id(eprint)
    url = entry.get('url', '')
    if 'arxiv.org/abs/' in url:
        return clean_arxiv_id(url.split('arxiv.org/abs/')[-1].strip())
    doi = entry.get('doi', '')
    if doi and ('arXiv' in doi or 'arxiv' in doi):
        return clean_arxiv_id(doi.split('/')[-1])
    return None

def get_paper_url(entry):
    arxiv_id = extract_arxiv_id(entry)
    if arxiv_id and arxiv_id != 'arxiv':
        return f"https://arxiv.org/abs/{arxiv_id}"
    url = entry.get('url', '')
    if url and url.startswith('http'):
        return url
    doi = entry.get('doi', '')
    if doi:
        return f"https://doi.org/{doi}"
    return None

# ---------------------------------------------------------------------------
# LaTeX title cleaning
# ---------------------------------------------------------------------------

def clean_latex_title(title):
    """Clean LaTeX artifacts from title for markdown display."""
    title = title.strip('{}')

    # --- Math-mode superscript: $^{2}$ -> 2 (then convert digits) ---
    sup_map = {'1': '¹','2': '²','3': '³','4': '⁴','5': '⁵','6': '⁶','7': '⁷','8': '⁸','9': '⁹','0': '⁰'}
    def _sup(m):
        inner = m.group(1)
        for d, s in sup_map.items():
            inner = inner.replace(d, s)
        return inner
    title = re.sub(r'\$\^\{([^}]+)\}\$', _sup, title)

    # Math-mode subscript: $_{text}$ -> _text
    title = re.sub(r'\$_\{([^}]+)\}\$', r'_\1', title)

    # Remaining simple math: $X$ -> X
    title = re.sub(r'\$([^$]+)\$', r'\1', title)
    title = re.sub(r'\$', '', title)

    # LaTeX commands (textsc, textit, emph, textbf, texttt)
    title = re.sub(r'\\textsc\{([^}]+)\}', r'\1', title)
    title = re.sub(r'\\textit\{([^}]+)\}', r'*\1*', title)
    title = re.sub(r'\\emph\{([^}]+)\}', r'*\1*', title)
    title = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', title)
    title = re.sub(r'\\texttt\{([^}]+)\}', r'`\1`', title)

    # Greek letters
    greek = {'\\alpha':'α','\\beta':'β','\\gamma':'γ','\\delta':'δ',
             '\\epsilon':'ε','\\theta':'θ','\\lambda':'λ','\\mu':'μ',
             '\\sigma':'σ','\\omega':'ω'}
    for latex, uni in greek.items():
        title = title.replace(latex, uni)

    # Remove remaining \cmd{arg} commands
    title = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', title)
    title = re.sub(r'\\[a-zA-Z]+', '', title)

    # --- Brace cleanup: remove LaTeX protective braces like {LLM} ---
    for _ in range(5):
        title = re.sub(r'\{([^{}]*)\}', r'\1', title)

    # --- Final fixes for any surviving patterns ---
    # Superscript digits surviving as ^{X}
    for d, s in sup_map.items():
        title = title.replace('^{'+d+'}', s)
    title = re.sub(r'\^\{([^}]+)\}', r'^\1', title)  # any remaining → ^text

    title = re.sub(r'\s+', ' ', title).strip()
    return title

def get_year(entry):
    y = entry.get('year', '')
    return y if y else '????'

def format_entry(entry):
    title = clean_latex_title(entry.get('title', 'Unknown Title'))
    year = get_year(entry)
    url = get_paper_url(entry)
    if url:
        return f"- [{year}] {title}. [[paper]({url})]"
    return f"- [{year}] {title}."

# ---------------------------------------------------------------------------
# Taxonomy (categorized by the survey's own structure)
# ---------------------------------------------------------------------------

TAXONOMY = {
    "Memory Objects": {
        "Factual Memory": [
            "zhong2024memorybank", "packer2023memgpt", "chhikara2025mem0",
            "rasmussen2025zep", "xu2025amem", "pan2025secom", "wang2023longmem",
            "lu2023memochat", "zhou2023recurrentgpt",
        ],
        "Situational Memory": [
            "park2023generative", "yao2023react", "shinn2023reflexion",
            "hu2025hiagent", "song2024moviechat", "yeo2025worldmm",
            "fan2025embodied", "fan2025embodiedvideoagent", "luo2024videorag", "luo2026video",
            "zhang2025mem2ego", "zhang2025ufo2", "kontonis2026memento",
            "maharana2024locomo", "wu2024longmemeval",
        ],
        "Constraint Memory": [
            "zhong2024memorybank", "chhikara2025mem0", "rasmussen2025zep",
            "xu2025amem", "wang2025privacy", "wang2025privacy_memory",
        ],
        "Experiential Memory": [
            "shinn2023reflexion", "park2023generative", "yan2025memoryr1",
            "wang2025memagent", "zhao2024expel", "liang2024sage",
            "suzgun2025dynamiccheatsheet", "ye2025h2r", "agentkb_2025",
            "ouyang2025reasoningbank", "cai2025flex", "zhang2026memrl",
            "zhang2025memevolve", "yu2026agenticmemory",
        ],
        "Procedural / Skill Memory": [
            "voyager_2023", "qian2023creator", "toolformer_2023",
            "toollLM_2023", "qin2023toolllm", "wang2025jarvis1", "jarvis1_2024",
            "zheng2025skillweaver", "skillweaver_2025", "wang2024agentworkflow",
            "agent_workflow_memory_2025", "legomem_2025", "memp_2025",
            "xiao2025toolmem", "toolmem_2025", "programmatic_skills_2025",
            "qu2024colt", "shi2025toolret", "wang2024toolgen",
            "creator_2023",
        ],
        "Meta-Memory": [
            "rasmussen2025zep", "chhikara2025mem0", "xu2025amem",
            "wang2025privacy", "wang2025privacy_memory",
        ],
    },
    "Memory Representations": {
        "Raw Record Memories": [
            "park2023generative", "lu2023memochat", "song2024moviechat",
            "yeo2025worldmm", "fan2025embodied", "fan2025embodiedvideoagent",
            "zhang2025mem2ego", "zhang2025ufo2", "luo2024videorag", "luo2026video",
            "kontonis2026memento", "zhou2023recurrentgpt",
        ],
        "Summary Memories": [
            "recursive_summarization_2023", "lu2023memochat", "zhou2023recurrentgpt",
            "chen2024comedy", "fang2025lightmem", "wang2025r3mem",
            "context_to_edus_2025", "kang2025acon", "wu2025resum",
            "jiang2023longllmlingua",
        ],
        "Itemized Memories": [
            "zhong2024memorybank", "chhikara2025mem0", "pan2025secom",
            "agentkb_2025", "du2026memguide", "memguide_2025", "xu2025amem",
            "secom_2025",
        ],
        "Structured Memories": [
            "rasmussen2025zep", "edge2024graphrag", "gutierrez2024hipporag",
            "gutierrez2025hipporag2", "anokhin2024arigraph", "anokhin2025arigraph",
            "rezazadeh2025memtree", "memtree_2025", "aadhithya2024hat",
            "hat_2025", "jiang2026magma", "magma_2025", "sgmem_2025",
            "zhang2025gmemory", "wang2025mirix", "mirix_2025",
            "intrinsic_memory_agents_2025", "lei2025dsmart", "guo2024lightrag",
            "tian2025rgmem", "hu2026evermemos",
        ],
        "Executable Memories": [
            "voyager_2023", "wang2025jarvis1", "jarvis1_2024",
            "zheng2025skillweaver", "skillweaver_2025", "wang2024agentworkflow",
            "agent_workflow_memory_2025", "toolformer_2023", "toollLM_2023",
            "qin2023toolllm", "qian2023creator", "creator_2023", "legomem_2025",
            "memp_2025", "xiao2025toolmem", "toolmem_2025", "programmatic_skills_2025",
        ],
        "Implicit Memories": [
            "kadapter_2021", "rome_2022", "memit_2023", "wise_2024",
            "memlora_2025", "memory3_2024", "mplus_2025", "titans_2025",
            "memory_decoder_2025", "li2024snapkv", "zhang2023h2o",
            "scissorhands_2023", "gist_tokens_2023", "in_context_autoencoder_2024",
            "xiao2024streamingllm",
        ],
    },
    "Memory Operations": {
        "Formation": [
            "kim2025prestorage", "yang2026promem", "chhikara2025mem0",
            "pan2025secom", "secom_2025", "xu2025amem", "nan2025nemori",
            "yan2025memoryr1", "wang2025memalpha",
        ],
        "Organization & Consolidation": [
            "rasmussen2025zep", "edge2024graphrag", "gutierrez2024hipporag",
            "gutierrez2025hipporag2", "rezazadeh2025memtree", "memtree_2025",
            "aadhithya2024hat", "hat_2025", "tian2025rgmem", "hu2026evermemos",
            "lei2025dsmart",
        ],
        "Retrieval": [
            "du2026memguide", "memguide_2025", "gutierrez2024hipporag",
            "gutierrez2025hipporag2", "xu2025memq", "qu2024colt",
            "shi2025toolret", "xiao2025toolmem", "toolmem_2025",
            "gao2023rag", "asai2023selfrag", "jin2024flashrag",
            "qian2024memorag", "lee2024planrag",
        ],
        "Injection & Utilization": [
            "zhang2025memoryasaction", "kang2025acon", "wu2025resum",
            "zhou2025mem1", "modarressi2023retllm",
        ],
        "Updating, Forgetting & Governance": [
            "zhong2024memorybank", "wei2026fademem", "tian2025rgmem",
            "yan2025memoryr1", "wang2025memalpha", "rasmussen2025zep",
            "hu2026evermemos", "wang2025privacy", "wang2025privacy_memory",
        ],
    },
    "Control Policies": {
        "Rule-Based Control": [
            "recursive_summarization_2023", "zhong2024memorybank",
            "packer2023memgpt", "fang2025lightmem", "wang2023scm",
        ],
        "LLM Self-Control": [
            "park2023generative", "packer2023memgpt", "xu2025amem",
            "chhikara2025mem0", "shinn2023reflexion", "latimer2025hindsight",
            "nan2025nemori",
        ],
        "Feedback-Driven Control": [
            "shinn2023reflexion", "zhao2024expel", "liang2024sage",
            "suzgun2025dynamiccheatsheet", "ye2025h2r", "agentkb_2025",
            "ouyang2025reasoningbank", "cai2025flex", "kontonis2026memento",
        ],
        "Learning-Based Control": [
            "yan2025memoryr1", "wang2025memalpha", "yuan2025memsearcher",
            "wang2025memagent", "yu2026agenticmemory", "yao2023retroformer",
            "zhang2026memrl", "zhang2025memevolve", "qian2024memorag",
            "wang2024toolgen",
        ],
    },
    "Memory Utility & Applications": {
        "Personalization": [
            "zhong2024memorybank", "chhikara2025mem0", "rasmussen2025zep",
        ],
        "Task Continuity": [
            "packer2023memgpt", "hu2025hiagent", "wu2025resum",
            "kang2025acon", "zhang2025memoryasaction",
        ],
        "Experience Reuse & Self-Improvement": [
            "shinn2023reflexion", "park2023generative", "voyager_2023",
            "qian2023creator", "yan2025memoryr1", "wang2025memagent",
        ],
        "Decision Constraints": [
            "chhikara2025mem0", "rasmussen2025zep", "xu2025amem",
            "zhang2025memoryasaction",
        ],
        "Multi-Agent Collaboration": [
            "zhang2025gmemory", "anokhin2024arigraph", "rasmussen2025zep",
            "xu2025amem", "wang2025mirix", "mirix_2025",
            "intrinsic_memory_agents_2025",
        ],
        "Trustworthy Deployment": [
            "rasmussen2025zep", "chhikara2025mem0", "xu2025amem",
            "wang2025privacy", "wang2025privacy_memory",
        ],
    },
    "Evaluation & Benchmarks": {
        "Evaluation Paradigms & Metrics": [
            "maharana2024locomo", "wu2024longmemeval",
            "zhao2026amabench", "yan2025memoryr1", "wang2025memagent",
            "wang2025privacy", "wang2025privacy_memory",
        ],
    },
}

# ---------------------------------------------------------------------------
# Duplicate resolution: deprecated key -> canonical key
# ---------------------------------------------------------------------------
DUPLICATE_MAP = {
    'fan2025embodiedvideoagent': 'fan2025embodied',
    'qin2023toolllm': 'toollLM_2023',
    'anokhin2025arigraph': 'anokhin2024arigraph',
    'wang2025privacy_memory': 'wang2025privacy',
    'luo2026video': 'luo2024videorag',
    'du2026memguide': 'memguide_2025',
    'secom_2025': 'pan2025secom',
    'jarvis1_2024': 'wang2025jarvis1',
    'skillweaver_2025': 'zheng2025skillweaver',
    'agent_workflow_memory_2025': 'wang2024agentworkflow',
    'toolmem_2025': 'xiao2025toolmem',
    'creator_2023': 'qian2023creator',
    'magma_2025': 'jiang2026magma',
    'mirix_2025': 'wang2025mirix',
    'memtree_2025': 'rezazadeh2025memtree',
    'hat_2025': 'aadhithya2024hat',
}

def resolve_key(key):
    return DUPLICATE_MAP.get(key, key)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    entries = parse_bib(BIB_PATH)
    print(f"Parsed {len(entries)} entries from {BIB_PATH}")

    # Build lookup preferring canonical keys
    raw_entries = {e['key']: e for e in entries}
    entry_by_key = {}
    for e in entries:
        canonical = resolve_key(e['key'])
        if canonical not in entry_by_key:
            if canonical in raw_entries:
                entry_by_key[canonical] = raw_entries[canonical]
            else:
                e['key'] = canonical
                entry_by_key[canonical] = e

    # Resolve taxonomy keys
    resolved_taxonomy = {}
    for section_name, subsections in TAXONOMY.items():
        resolved_subs = {}
        for sub_name, keys in subsections.items():
            seen = set()
            rkeys = []
            for k in keys:
                c = resolve_key(k)
                if c not in seen:
                    rkeys.append(c)
                    seen.add(c)
            resolved_subs[sub_name] = rkeys
        resolved_taxonomy[section_name] = resolved_subs

    used_keys = set()
    for section in resolved_taxonomy.values():
        for keys in section.values():
            used_keys.update(keys)

    missing = used_keys - set(entry_by_key.keys())
    if missing:
        print(f"\nWARNING: {len(missing)} keys not found in .bib:")
        for k in sorted(missing):
            print(f"  - {k}")

    # ---- Build README ----
    L = []
    def add(s=''):
        L.append(s)

    add('<h1 align="center">')
    add('  <strong>From Historical Signals to Action Utility:<br>A Survey of Memory Mechanisms for LLM-based Agents</strong>')
    add('</h1>')
    add('')
    add('<div align="center">')
    add('')
    add('[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)')
    add('[![Contribution Welcome](https://img.shields.io/badge/Contributions-welcome-Green?logo=mercadopago&logoColor=white)](https://github.com/README.md)')
    add('')
    add('</div>')
    add('')
    add('## News')
    add('- [2026/06/18] This repository is created to maintain a paper list accompanying the survey "From Historical Signals to Action Utility: A Survey of Memory Mechanisms for LLM-based Agents".')
    add('- [2026/06/18] The survey paper and accompanying bibliography are now available.')
    add('')
    add('## Introduction')
    add('')
    add('Large language model (LLM)-based agents are increasingly expected to operate across long interaction histories, repeated user sessions, tool calls, changing environments, and multi-step tasks. These settings require agents to preserve and reuse information beyond a single context window.')
    add('')
    add('This survey studies agent memory as an **action-oriented state-management mechanism** that transforms historical signals into future action utility. We organize the literature through a unified chain:')
    add('')
    add('```')
    add('Historical Signals -> Memory Objects -> Memory Representations -> Memory Operations -> Control Policies -> Action Utility')
    add('```')
    add('')
    add('### Key Taxonomy Dimensions')
    add('')
    add('- **Memory Objects** (What should agents remember?): Factual, Situational, Constraint, Experiential, Procedural, Meta-memory')
    add('- **Memory Representations** (How are memories carried?): Raw Record, Summary, Itemized, Structured, Executable, Implicit')
    add('- **Memory Operations** (How are memories managed?): Formation, Organization, Retrieval, Utilization, Updating/Forgetting, Governance')
    add('- **Control Policies** (Who decides memory operations?): Rule-Based, LLM Self-Control, Feedback-Driven, Learning-Based')
    add('- **Memory Utility** (What does memory enable?): Personalization, Task Continuity, Experience Reuse, Decision Constraints, Multi-Agent Collaboration, Trustworthy Deployment')
    add('')
    add('---')
    add('')
    add('## Paper List')
    add('')
    add(f'*Total: {len(used_keys)} papers organized by the survey taxonomy.*')
    add('')

    for section_name, subsections in resolved_taxonomy.items():
        add(f'### {section_name}')
        add('')
        for sub_name, keys in subsections.items():
            add(f'#### {sub_name}')
            add('')
            count = 0
            for key in keys:
                if key in entry_by_key:
                    add(format_entry(entry_by_key[key]))
                    count += 1
            if count == 0:
                add('*(No entries found)*')
            add('')

    # Cross-category papers
    add('---')
    add('')
    add('## Cross-Category Papers')
    add('')
    add('Many papers contribute to multiple dimensions of the taxonomy. Key cross-category papers include:')
    add('')

    key_categories = defaultdict(list)
    for section_name, subsections in resolved_taxonomy.items():
        for sub_name, keys in subsections.items():
            for key in keys:
                key_categories[key].append(f"{section_name} -> {sub_name}")

    multi = [(k, v) for k, v in key_categories.items() if len(v) >= 3]
    multi.sort(key=lambda x: -len(x[1]))

    for key, cats in multi[:20]:
        if key in entry_by_key:
            title = clean_latex_title(entry_by_key[key].get('title', key))
            title_short = title[:100] + '...' if len(title) > 100 else title
            add(f'- **[{key}]** *{title_short}* -- Appears in: {", ".join(cats[:5])}')

    add('')
    add('---')
    add('')
    add('## Citation')
    add('')
    add('If you find this survey or paper list helpful, please cite:')
    add('')
    add('```bibtex')
    add('@article{anonymous2026memory,')
    add('  title     = {From Historical Signals to Action Utility: A Survey of Memory Mechanisms for LLM-based Agents},')
    add('  author    = {Anonymous Author(s)},')
    add('  year      = {2026},')
    add('  note      = {Working paper}')
    add('}')
    add('```')
    add('')
    add('---')
    add('')
    add('## Paper Statistics')
    add('')
    add(f'- **Total unique papers in bibliography**: {len(entry_by_key)}')
    add(f'- **Papers in taxonomy**: {len(used_keys)}')
    year_counts = defaultdict(int)
    for e in entry_by_key.values():
        y = get_year(e)
        if y.isdigit():
            year_counts[int(y)] += 1
    for y in sorted(year_counts.keys()):
        add(f'- **{y}**: {year_counts[y]} papers')
    add('')
    add('---')
    add('')
    add('## Contributing')
    add('')
    add('We welcome contributions! If you have suggestions for additional papers or corrections to the taxonomy, please open an issue or pull request.')
    add('')
    add('---')
    add('')
    add('## License')
    add('')
    add('This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    print(f"\nREADME.md written to {OUTPUT_PATH}")
    print(f"Total papers categorized: {len(used_keys)}")

if __name__ == '__main__':
    main()
