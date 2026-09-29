import re, sys, pathlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
base = pathlib.Path(__file__).resolve().parent.parent
root = base / ".claude" / "skills" / "sunzi"

# 原文段落: 編號 -> 原文
src = (root / "references" / "sunzi.md").read_text(encoding="utf-8")
paras = {}
cur = None
for line in src.splitlines():
    m = re.match(r"^#### (\S+)$", line)
    if m:
        cur = m.group(1)
        continue
    if cur and line.startswith("> ") and cur not in paras:
        paras[cur] = line[2:]
alltext = "\n".join(paras.values())

errors = []
FW = "，。：；？！、「」（）"


def check(q, pid, where):
    q = q.rstrip(".")
    if pid:
        if pid not in paras:
            errors.append(f"{where}: unknown paragraph {pid}")
        elif q not in paras[pid]:
            errors.append(f"{where}: not in {pid}: {q}")
    elif q not in alltext:
        errors.append(f"{where}: not in source: {q}")


def is_cjk_quote(q):
    return len(q) >= 4 and sum("一" <= c <= "鿿" for c in q) >= 3


# 1. 參考原文副本必須和專案根目錄的 references/sunzi.md 十三篇一致
root_src = (base / "references" / "sunzi.md").read_text(encoding="utf-8")
root_paras = dict(re.findall(r"^#### (\S+)\n\n> (.+)$", root_src, re.M))
if root_paras != paras:
    diff = [k for k in set(root_paras) | set(paras) if root_paras.get(k) != paras.get(k)]
    errors.append(f"sunzi.md copy differs from references/sunzi.md at: {sorted(diff)}")

# 2. 檢查 skill 內所有檔案的引文與格式
files = ["SKILL.md", "references/mental-models.md", "references/situations.md", "references/examples.md"]
quotes = 0
for f in files:
    lines = (root / f).read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        where = f"{f}:{i + 1}"
        if line.startswith("> "):
            pid = None
            for nxt in lines[i + 1:i + 4]:
                mm = re.search(r"出處: \S+ \((\S+?)\)", nxt)
                if mm:
                    pid = mm.group(1)
                    break
            check(line[2:], pid, where)
            quotes += 1
            continue
        # 篇名 (編號) 說 "原文"
        for pid, q in re.findall(r'\((\d+\.\d+)\)[^"\n]{0,6}"([^"]+)"', line):
            check(q, pid, where)
            quotes += 1
        if not line.startswith("description:"):
            stripped = re.sub(r'"[^"]*"', "", line)
            stripped = re.sub(r"`[^`]*`", "", stripped)
            bad = [c for c in stripped if c in FW]
            if "**" in stripped:
                bad.append("**")
            if "——" in stripped:
                bad.append("——")
            if bad:
                errors.append(f"{where}: style {bad}: {line}")

# 3. 每則回應最多引一句
ex = (root / "references" / "examples.md").read_text(encoding="utf-8")
for block in re.split(r"^### 回應.*$", ex, flags=re.M)[1:]:
    body = re.split(r"^##", block, flags=re.M)[0]
    n = len(re.findall(r'\(\d+\.\d+\)[^"\n]{0,6}"', body))
    if n > 1:
        errors.append(f"examples.md: a response cites {n} quotes: {body.strip()[:40]}")

sit = (root / "references" / "situations.md").read_text(encoding="utf-8")
cats = re.findall(r"^### (\S+)-\d+$", sit, re.M)
print("paragraphs:", len(paras))
print("quotes checked:", quotes)
print("situations:", len(cats), dict(Counter(cats)))
print("\n".join(errors) if errors else "no errors")
sys.exit(1 if errors else 0)
