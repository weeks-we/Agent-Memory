import re

TEX = r"D:\科研\智能体记忆机制\sample-acmsmall-submission.tex"

with open(TEX, 'r', encoding='utf-8') as f:
    content = f.read()

patterns = [
    "anokhin",
    "wang2025privacy",
    "wang2023longmem",
    "zhong2024memorybank",
    "ye2025h2r",
    "zhang2023h2o",
]

for p in patterns:
    print(f"=== Citations containing '{p}': ===")
    for m in re.finditer(r'\\citep\{([^}]*' + re.escape(p) + r'[^}]*)\}', content):
        ln = content[:m.start()].count('\n') + 1
        print(f"  Line {ln}: \\citep{{{m.group(1)}}}")
    for m in re.finditer(r'\\citet\{([^}]*' + re.escape(p) + r'[^}]*)\}', content):
        ln = content[:m.start()].count('\n') + 1
        print(f"  Line {ln}: \\citet{{{m.group(1)}}}")
    print()
