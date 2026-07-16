"""
Multi-Language Display Translator GUI Tool  — Secure Meters Ltd

Requirements:
    pip install deep-translator
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import re, os, shutil, threading, queue, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

# ─────────────────────────── LANGUAGES ──────────────────────────────────────

# Latin-1 safe languages
LATIN1_LANGUAGES = {
    "Czech":      "cs", "Danish":     "da", "Dutch":      "nl",
    "Finnish":    "fi", "French":     "fr", "German":     "de",
    "Hungarian":  "hu", "Indonesian": "id", "Italian":    "it",
    "Norwegian":  "no", "Polish":     "pl", "Portuguese": "pt",
    "Romanian":   "ro", "Russian":    "ru", "Spanish":    "es", "Swedish":    "sv",
    "Turkish":    "tr", "Vietnamese": "vi",
}

# Unicode escape languages (new in v2.0)
UNICODE_ESC_LANGUAGES = {
    "Arabic": "ar",
    "Hindi":  "hi",
}

LANGUAGES = {**LATIN1_LANGUAGES, **UNICODE_ESC_LANGUAGES}

# DeepL target-language codes (Tier 1)
DEEPL_LANG_MAP = {
    "Czech":      "CS",
    "Danish":     "DA",
    "Dutch":      "NL",
    "Finnish":    "FI",
    "French":     "FR",
    "German":     "DE",
    "Hungarian":  "HU",
    "Italian":    "IT",
    "Norwegian":  "NB",
    "Polish":     "PL",
    "Portuguese": "PT-PT",
    "Romanian":   "RO",
    "Russian":    "RU",
    "Spanish":    "ES",
    "Swedish":    "SV",
    "Turkish":    "TR",
}
DEEPL_UNSUPPORTED = {"Arabic", "Hindi", "Vietnamese", "Indonesian"}

KNOWN_LANG_NAMES = {k.lower() for k in LANGUAGES}

CONFIG_PATH = Path.home() / ".defstr_translator_config.json"

NAV_SKIP_ENTRIES = {
    'english',
    'english without import/export text',
}

BACKTICK        = '`'

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {"deepl_api_key": "", "preferred_tier": "auto"}


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATION ENGINE (NEW: Multi-tier support)
# ─────────────────────────────────────────────────────────────────────────────

_deepl_translator = None   # cached deepl.Translator instance

def _get_deepl_translator():
    global _deepl_translator
    if _deepl_translator is not None:
        return _deepl_translator
    cfg = load_config()
    key = cfg.get("deepl_api_key", "").strip()
    if not key:
        return None
    try:
        import deepl
        _deepl_translator = deepl.Translator(key)
        return _deepl_translator
    except Exception:
        return None


def _try_deepl(text: str, lang_name: str):
    """Tier 1 — DeepL. Returns (translated_str, 'DeepL') or None."""
    if lang_name in DEEPL_UNSUPPORTED:
        return None
    dl_code = DEEPL_LANG_MAP.get(lang_name)
    if not dl_code:
        return None
    translator = _get_deepl_translator()
    if translator is None:
        return None
    try:
        result = translator.translate_text(text, target_lang=dl_code)
        out = result.text.strip()
        if out:
            return (out, "DeepL")
    except Exception:
        pass
    return None


def _try_google(text: str, lang_code: str):
    """Tier 2 — Google Translate via deep-translator."""
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source='auto', target=lang_code).translate(text)
        if out and out.strip():
            return (out.strip(), "Google")
    except Exception:
        pass
    return None


def _try_mymemory(text: str, lang_name: str, lang_code: str):
    """Tier 3 — MyMemory via deep-translator."""
    try:
        from deep_translator import MyMemoryTranslator
        target = f"en-{lang_code.upper()}" if len(lang_code) == 2 else lang_code
        out = MyMemoryTranslator(source='en-US', target=target).translate(text)
        if out and out.strip():
            return (out.strip(), "MyMemory")
    except Exception:
        pass
    return None


def encode_for_file(text: str, lang_name: str) -> str:
    """
    Return a string safe for display in the output file.
    NOTE: Backtick padding is intentionally preserved — do NOT strip it here.
    Padding is applied by pad_or_trim() before this function is called.
    All languages are written as-is (UTF-8). Character length is measured
    in Unicode code points, consistent with standard word-counter tools.
    """
    # Do NOT strip backticks — they are intentional padding added by pad_or_trim()
    return text
MAX_WORKERS     = 10
AUTO_FREE_SLOTS = 4

DEFSTR_PAT     = re.compile(r"#pragma\s+DEFSTR\s+'([^']*)'")
DEFNSTR_PAT    = re.compile(r"#pragma\s+DEFNSTR\s+'([^']*)'")
COMMENT_PAT    = re.compile(r'//\s*([\w][\w\s\(\)\-\.]*)')
NAV_DEFSTR_PAT = re.compile(r"DEFSTR\s+'([^']*)'")

PREFIX_PATTERNS = [
    re.compile(r'^([A-Z0-9]{1,8}:)(.+)$'),
    re.compile(r'^(L[123N]\s+)(.+)$'),
    re.compile(r'^([A-Z][a-z]{0,3}\.\s*)([A-Z].+)$'),
]


# ─────────────────────────── HELPERS ────────────────────────────────────────

def pad_or_trim(text, length):
    """
    Pad or trim text to specified length.
    For text that's shorter, add backticks.
    """
    if len(text) >= length:
        return text[:length]
    else:
        return text + BACKTICK * (length - len(text))

def strip_padding_backticks(text):
    """Strip trailing backtick padding characters from text."""
    return text.rstrip(BACKTICK)

def is_placeholder(raw):
    return raw.strip(BACKTICK) == ''

def has_content(raw):
    return not is_placeholder(raw) and bool(raw.rstrip(BACKTICK).strip())

def is_latin1_safe(text):
    return all(ord(c) <= 255 for c in text)

def safe_encode(text):
    return text if is_latin1_safe(text) else text.encode('latin-1', errors='replace').decode('latin-1')

def _do_translate(text: str, lang_name: str) -> tuple:
    """
    Translate text into lang_name with multi-tier fallback.
    Returns (translated_str, tier_label).
    Handles prefix-aware translation.
    """
    text = text.strip()
    if not text or all(c == BACKTICK for c in text):
        return ("", "skip")

    # Prefix-aware: split and translate only body
    prefix = ""
    body = text
    for pat in PREFIX_PATTERNS:
        m = pat.match(text)
        if m:
            prefix = m.group(1)
            body   = m.group(2)
            break

    lang_code = LANGUAGES.get(lang_name, "en")

    # Tier 1: DeepL
    result = _try_deepl(body, lang_name)
    if result is None:
        # Tier 2: Google Translate
        result = _try_google(body, lang_code)
    if result is None:
        # Tier 3: MyMemory
        result = _try_mymemory(body, lang_name, lang_code)
    if result is None:
        return (text, "failed")

    translated, tier = result
    return (prefix + translated, tier)

def build_line(pragma_type, content, comment=""):
    base = f"#pragma {pragma_type}  '{content}'"
    return base + f"  // {comment}" if comment else base

def is_known_lang(comment_text):
    return comment_text.strip().lower() in KNOWN_LANG_NAMES

def norm_lang(raw):
    return raw.strip().title()

def count_trailing_free_slots(group):
    count = 0
    for _, raw in reversed(group):
        if is_placeholder(raw): count += 1
        else: break
    return count

def block_has_any_known_lang(group, lines_text):
    """Returns True if block has at least one known language comment."""
    for li, raw in group:
        cm = COMMENT_PAT.search(lines_text[li])
        if cm and is_known_lang(cm.group(1)):
            return True
    return False


# ─────────────────────────── NAVIGATION PARSER ──────────────────────────────

def parse_nav_languages(lines_text):
    nav_start = nav_end = None
    for i, line in enumerate(lines_text):
        l = line.rstrip()
        if l.startswith('/*') or l.strip().startswith('/*'):
            for j in range(i, min(i + 60, len(lines_text))):
                if 'Order of languages' in lines_text[j]:
                    nav_start = i
                    for k in range(j, min(j + 60, len(lines_text))):
                        s = lines_text[k].rstrip()
                        if s.endswith('*/') or s.strip() == '*/':
                            nav_end = k; break
                    break
            if nav_start is not None: break
    if nav_start is None or nav_end is None:
        return []
    result = []
    for i in range(nav_start, nav_end + 1):
        m = NAV_DEFSTR_PAT.search(lines_text[i])
        if not m: continue
        raw_name  = m.group(1).strip()
        name_low  = raw_name.lower().strip()
        norm_name = raw_name.title()
        if name_low in NAV_SKIP_ENTRIES:
            result.append({'name': raw_name, 'code': None, 'translatable': False})
        else:
            lang_code = LANGUAGES.get(norm_name)
            if lang_code:
                result.append({'name': norm_name, 'code': lang_code, 'translatable': True})
            else:
                result.append({'name': raw_name, 'code': None, 'translatable': False})
    return result

def get_nav_order(lines_text):
    return [e['name'] for e in parse_nav_languages(lines_text) if e['translatable']]


# ─────────────────────────── BLOCK DETECTION ────────────────────────────────

def find_all_blocks(lines):
    blocks = []
    n = len(lines)
    i = 0
    while i < n:
        l = lines[i].rstrip()
        m_str  = DEFSTR_PAT.match(l)
        m_nstr = DEFNSTR_PAT.match(l)
        if not (m_str or m_nstr): i += 1; continue
        pragma_type = 'DEFNSTR' if m_nstr else 'DEFSTR'
        pat = DEFNSTR_PAT if m_nstr else DEFSTR_PAT
        first_raw = pat.match(l).group(1)
        if is_placeholder(first_raw): i += 1; continue
        group = []; j = i
        english_raw = first_raw; str_len = len(first_raw)
        while j < n:
            ll  = lines[j].rstrip()
            mm2 = pat.match(ll)
            if mm2:
                raw = mm2.group(1)
                group.append((j, raw))
                if is_placeholder(raw):
                    k = j + 1
                    while k < n:
                        lk = lines[k].rstrip(); mk = pat.match(lk)
                        if mk:
                            if not is_placeholder(mk.group(1)): j += 1; break
                            else: group.append((k, mk.group(1))); k += 1; j = k
                        elif lk == '' or lk.startswith('//') or lk.startswith('/*') or lk.startswith('*'): k += 1
                        else: j = k; break
                    else: j = k
                    break
                else: j += 1
            elif ll == '' or ll.startswith('//') or ll.startswith('/*') or ll.startswith('*'): j += 1
            else: break
        if group:
            indices = [li for li, _ in group]
            insert_idx = indices[-1] + 1
            for li, raw in reversed(group):
                if has_content(raw): insert_idx = li + 1; break
            blocks.append({
                'pragma_type': pragma_type, 'group': group,
                'defstr_lines': indices, 'english_raw': english_raw,
                'str_len': str_len, 'insert_before': insert_idx,
            })
        i = j
    return blocks


# ─────────────────────────── SKIP LOGIC ─────────────────────────────────────

def block_has_language(group, lang_name, lines_text):
    """Returns True if this block already has the target language comment."""
    lang_lower = lang_name.lower().strip()
    for li, raw in group:
        cm = COMMENT_PAT.search(lines_text[li])
        if cm and cm.group(1).strip().lower() == lang_lower:
            return True
    return False

def block_needs_translation(group, lang_name, lines_text):
    if block_has_language(group, lang_name, lines_text):
        return False, "already_translated"
    return True, ""


# ─────────────────────────── PRE-CHECK (runs on main thread, instant) ────────

def check_already_translated(filepath, lang_name, specific_english=None):
    """
    Synchronous check run BEFORE spawning worker thread.

    KEY FIX (v5.3):
      'real_blocks' = only blocks that already have at least one known language
      comment (// Swedish, // German, etc.). This excludes standalone translation
      lines that find_all_blocks() incorrectly treats as block starts.

      Example of the bug this fixes:
        'Exibição segura``'  // Portuguese  ← this line starts a fake block
        find_all_blocks() sees it as a new block with english_raw='Exibição segura'
        That fake block has NO '// Portuguese' comment → already_count < total
        → popup never showed

      With this fix: we only count blocks that have at least one '// LangName'
      comment already. Fake blocks (translation lines) have no such comment
      so they're excluded from the check.
      
    KEY FIX (v5.4):
      When checking if a specific English string is already translated in a language,
      use 'any()' instead of 'all()' to catch duplicate translation attempts.
      If ANY matching block already has the target language translation,
      it should be flagged as an error to prevent duplicate translations.
    """
    # Try UTF-8 first, fall back to Latin-1 for existing files
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines_text = [l.rstrip('\r\n') for l in f.read().splitlines()]
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            lines_text = [l.rstrip('\r\n') for l in f.read().splitlines()]

    all_blocks = find_all_blocks(lines_text)
    if not all_blocks:
        return False, 0

    if specific_english:
        eng_low  = specific_english.strip().lower()
        # Only real blocks matching the English string
        matching = [b for b in all_blocks
                    if b['english_raw'].rstrip(BACKTICK).strip().lower() == eng_low
                    and block_has_any_known_lang(b['group'], lines_text)]
        if not matching:
            return False, 0
        # Fixed: use 'any()' instead of 'all()' to catch ANY existing translation
        if any(block_has_language(b['group'], lang_name, lines_text) for b in matching):
            return True, len(matching)
        return False, 0
    else:
        # Real blocks = blocks that have at least one known language comment
        # This correctly excludes standalone translation lines mistaken as blocks
        real_blocks = [b for b in all_blocks
                       if block_has_any_known_lang(b['group'], lines_text)]
        if not real_blocks:
            return False, 0
        already_count = sum(1 for b in real_blocks
                            if block_has_language(b['group'], lang_name, lines_text))
        if already_count == len(real_blocks):
            return True, already_count
        return False, 0


# ─────────────────────────── NAV-ORDER INSERT POSITION ──────────────────────

def get_nav_insert_position(block, lang_name, lines_text, nav_order):
    if not nav_order or lang_name not in nav_order:
        return block['insert_before']
    lang_idx = nav_order.index(lang_name)
    preceding_lower = {p.lower() for p in nav_order[:lang_idx]}
    last_preceding_line = None
    for li, raw in block['group']:
        cm = COMMENT_PAT.search(lines_text[li])
        if cm and cm.group(1).strip().lower() in preceding_lower:
            last_preceding_line = li
    if last_preceding_line is not None:
        return last_preceding_line + 1
    else:
        for li, raw in block['group']:
            if has_content(raw):
                return li + 1
        return block['insert_before']


# ─────────────────────────── NAV COMMENT BLOCK UPDATER ──────────────────────

def update_nav_comment_block(lines, lang_name, eol):
    nav_start = nav_end = None
    for i, line in enumerate(lines):
        l = line.rstrip()
        if l.startswith('/*') or l.strip().startswith('/*'):
            for j in range(i, min(i + 60, len(lines))):
                if 'Order of languages' in lines[j]:
                    nav_start = i
                    for k in range(j, min(j + 60, len(lines))):
                        s = lines[k].rstrip()
                        if s.endswith('*/') or s.strip() == '*/':
                            nav_end = k; break
                    break
            if nav_start is not None: break
    if nav_start is None or nav_end is None: return lines
    block_text = ''.join(lines[nav_start:nav_end + 1]).lower()
    if lang_name.lower() in block_text: return lines
    last_defstr = None
    for i in range(nav_start, nav_end):
        if 'DEFSTR' in lines[i]: last_defstr = i
    insert_at = (last_defstr + 1) if last_defstr else nav_end
    lines.insert(insert_at, f"DEFSTR  '{lang_name}'" + eol)
    return lines


# ─────────────────────────── FIND INSERT POSITION FOR NEW BLOCK ─────────────

def find_last_translated_block_end(lines_text, all_blocks):
    last_end_idx = None
    for block in all_blocks:
        has_lang = any(
            is_known_lang(COMMENT_PAT.search(lines_text[li]).group(1))
            for li, _ in block['group']
            if COMMENT_PAT.search(lines_text[li])
        )
        if has_lang: last_end_idx = block['group'][-1][0]
    return last_end_idx


# ─────────────────────────── CHECK IF ENGLISH STRING EXISTS ──────────────────

def english_string_exists_in_file(lines_text, english_str):
    english_stripped = english_str.strip().lower()
    for line in lines_text:
        m = DEFSTR_PAT.match(line.rstrip()) or DEFNSTR_PAT.match(line.rstrip())
        if m:
            raw = m.group(1).rstrip(BACKTICK).strip().lower()
            if raw == english_stripped:
                cm = COMMENT_PAT.search(line)
                if not cm or not is_known_lang(cm.group(1)): return True
    return False


# ─────────────────────────── ADD NEW STRING BLOCK ────────────────────────────

def add_new_string_block(filepath, new_english, str_length, on_log=None, on_progress=None):
    def log(msg, tag='info'):
        if on_log: on_log(msg, tag)

    # Try UTF-8 first, fall back to Latin-1 for existing files
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
    lines      = content.splitlines(keepends=True)
    lines_text = [l.rstrip('\r\n') for l in lines]
    eol        = '\r\n' if '\r\n' in content else '\n'

    backup_path = filepath + '.bak'
    shutil.copy2(filepath, backup_path)
    log(f"Backup : {backup_path}", 'info')

    all_blocks = find_all_blocks(lines_text)
    if not all_blocks: raise ValueError("No existing blocks found in file.")

    nav_langs = parse_nav_languages(lines_text)

    if nav_langs:
        translatable = [e for e in nav_langs if e['translatable']]
        log(f"Navigation block: translating {len(translatable)} languages", 'info')
        for e in translatable:
            log(f"  → {e['name']}", 'info')

        unique_langs = {e['code']: e['name'] for e in translatable}
        translations = {}; total = len(unique_langs); done_count = [0]

        def _job(lc, ln):
            try: return lc, _do_translate(new_english, ln)
            except: return lc, None

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(_job, c, n): (c, n) for c, n in unique_langs.items()}
            for f in as_completed(futures):
                code, result = f.result()
                translations[code] = result; done_count[0] += 1
                if on_progress: on_progress(done_count[0], total, unique_langs.get(code, code))
                # Extract text from (text, tier) tuple if present
                if result:
                    translated_text = result[0] if isinstance(result, tuple) else result
                    log(f"  ✓ {unique_langs[code]:20} → '{translated_text}'", 'ok')

        fitted_english  = pad_or_trim(new_english, str_length)
        new_block_lines = [build_line('DEFSTR', fitted_english) + eol]
        for entry in translatable:
            lang_name = entry['name']; lang_code = entry['code']
            result = translations.get(lang_code)
            # Extract text from (text, tier) tuple if present
            if result:
                translated = result[0] if isinstance(result, tuple) else result
                new_block_lines.append(build_line('DEFSTR', pad_or_trim(translated, str_length), lang_name) + eol)
            else:
                new_block_lines.append(build_line('DEFSTR', BACKTICK * str_length, lang_name) + eol)
        for _ in range(AUTO_FREE_SLOTS):
            new_block_lines.append(build_line('DEFSTR', BACKTICK * str_length) + eol)
        log(f"  + {AUTO_FREE_SLOTS} free trailing slots added", 'info')
        lang_count = len(translatable)

    else:
        log("Navigation block not found — using existing block as template", 'warn')
        best_block = None; best_ct = -1
        for block in all_blocks:
            ct = sum(1 for li, _ in block['group']
                     if COMMENT_PAT.search(lines_text[li]) and
                     is_known_lang(COMMENT_PAT.search(lines_text[li]).group(1)))
            if ct > best_ct: best_ct = ct; best_block = block

        seen = set(); lang_slots = []
        if best_block:
            for idx, (li, raw) in enumerate(best_block['group']):
                if idx == 0: continue
                cm = COMMENT_PAT.search(lines_text[li])
                if cm and is_known_lang(cm.group(1)):
                    ln = norm_lang(cm.group(1)); lc = LANGUAGES.get(ln)
                    if lc and ln not in seen: seen.add(ln); lang_slots.append((ln, lc))

        unique_langs = {lc: ln for ln, lc in lang_slots}
        translations = {}; total = len(unique_langs); done_count = [0]

        def _job_fb(lc, ln):
            try: return lc, _do_translate(new_english, ln)
            except: return lc, None

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(_job_fb, c, n): (c, n) for c, n in unique_langs.items()}
            for f in as_completed(futures):
                code, result = f.result()
                translations[code] = result; done_count[0] += 1
                if on_progress: on_progress(done_count[0], total, unique_langs.get(code, code))
                # Extract text from (text, tier) tuple if present
                if result:
                    translated_text = result[0] if isinstance(result, tuple) else result
                    log(f"  ✓ {unique_langs[code]:20} → '{translated_text}'", 'ok')

        fitted_english  = pad_or_trim(new_english, str_length)
        new_block_lines = [build_line('DEFSTR', fitted_english) + eol]
        for ln, lc in lang_slots:
            result = translations.get(lc)
            # Extract text from (text, tier) tuple if present
            if result:
                translated = result[0] if isinstance(result, tuple) else result
                new_block_lines.append(build_line('DEFSTR', pad_or_trim(translated, str_length), ln) + eol)
            else:
                new_block_lines.append(build_line('DEFSTR', BACKTICK * str_length, ln) + eol)
        for _ in range(AUTO_FREE_SLOTS):
            new_block_lines.append(build_line('DEFSTR', BACKTICK * str_length) + eol)
        lang_count = len(lang_slots)

    insert_after_idx = find_last_translated_block_end(lines_text, all_blocks)
    if insert_after_idx is None:
        lines.append(eol); lines.extend(new_block_lines)
        log(f"  New block inserted at lines {len(lines) - len(new_block_lines) + 1}-{len(lines)}", 'info')
    else:
        insert_pos = insert_after_idx + 1
        log(f"  Inserting block after line {insert_after_idx + 1}", 'info')
        lines.insert(insert_pos, eol)
        for idx, bl in enumerate(new_block_lines):
            lines.insert(insert_pos + 1 + idx, bl)
        log(f"  Block committed at lines {insert_pos + 2}-{insert_pos + 1 + len(new_block_lines)}", 'ok')

    base, ext = os.path.splitext(filepath)
    out_path  = f"{base}_NewString{ext}"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    log(f"\n✅ New block inserted.", 'ok')
    log(f"   English  : '{new_english}'  (length={str_length})", 'ok')
    log(f"   Languages: {lang_count} translated  +  {AUTO_FREE_SLOTS} free slots", 'ok')
    log(f"   Changes committed at lines {len(lines) - len(new_block_lines)}-{len(lines)}", 'info')
    log(f"   Output   : {out_path}", 'ok')

    return out_path, {
        'new_english': new_english, 'str_length': str_length,
        'lang_count': lang_count, 'translations': translations,
        'output_file': out_path, 'backup_file': backup_path,
    }


# ─────────────────────────── TRANSLATE HELPERS ───────────────────────────────

def extra_string_already_added(lines_text, lang_name, translated_text):
    lang_lower       = lang_name.lower().strip()
    translated_strip = translated_text.rstrip(BACKTICK).strip().lower()
    for line in lines_text:
        m = DEFSTR_PAT.match(line.rstrip()) or DEFNSTR_PAT.match(line.rstrip())
        if m:
            raw = m.group(1).rstrip(BACKTICK).strip().lower()
            if raw == translated_strip:
                cm = COMMENT_PAT.search(line)
                if cm and cm.group(1).strip().lower() == lang_lower: return True
    return False

def find_extra_string_insert_position(lines_text, lang_name, nav_order):
    lang_lower = lang_name.lower().strip()
    last_insert = None; last_str_len = 20
    all_blocks = find_all_blocks(lines_text)
    for block in all_blocks:
        for li, raw in block['group']:
            cm = COMMENT_PAT.search(lines_text[li])
            if cm and cm.group(1).strip().lower() == lang_lower:
                last_insert  = get_nav_insert_position(block, lang_name, lines_text, nav_order)
                last_str_len = block['str_len']
                break
    return last_insert, last_str_len

def translate_parallel(unique_texts, lang_code, lang_name, stop_event, on_one_done=None):
    results = {}; total = len(unique_texts); done_count = [0]
    def _job(text):
        if stop_event.is_set(): return text, None
        try: return text, _do_translate(text, lang_name)
        except: return text, None
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_job, t): t for t in unique_texts}
        for f in as_completed(futures):
            text, translated = f.result()
            results[text] = translated; done_count[0] += 1
            if on_one_done: on_one_done(done_count[0], total, text)
            if stop_event.is_set():
                for p in futures: p.cancel(); break
    return results


# ─────────────────────────── MAIN PROCESS FILE ───────────────────────────────

def process_file(filepath, lang_name, lang_code, extra_english="",
                 stop_event=None, on_progress=None, on_log=None):
    if stop_event is None: stop_event = threading.Event()
    def log(msg, tag='info'):
        if on_log: on_log(msg, tag)

    # Try UTF-8 first, fall back to Latin-1 for existing files
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
    lines      = content.splitlines(keepends=True)
    lines_text = [l.rstrip('\r\n') for l in lines]
    eol        = '\r\n' if '\r\n' in content else '\n'
    backup_path = filepath + '.bak'
    shutil.copy2(filepath, backup_path)
    log(f"Backup : {backup_path}", 'info')

    nav_order  = get_nav_order(lines_text)
    all_blocks = find_all_blocks(lines_text)
    if not all_blocks: raise ValueError("No blocks found.")

    blocks_to_translate = []; already_done_count = 0
    for block in all_blocks:
        should, _ = block_needs_translation(block['group'], lang_name, lines_text)
        if should: blocks_to_translate.append(block)
        else: already_done_count += 1

    defstr_count  = sum(1 for b in all_blocks if b['pragma_type'] == 'DEFSTR')
    defnstr_count = sum(1 for b in all_blocks if b['pragma_type'] == 'DEFNSTR')
    lang_already_implemented = (already_done_count > 0)

    log(f"Total blocks found   : {len(all_blocks)}  (DEFSTR: {defstr_count}  DEFNSTR: {defnstr_count})", 'info')
    log(f"Already translated   : {already_done_count}  →  skipped", 'info')
    log(f"Need translation     : {len(blocks_to_translate)}", 'info')

    extra_eng = extra_english.strip()

    def _ret(**kw):
        base = {
            'total_blocks': len(all_blocks), 'defstr_blocks': defstr_count,
            'defnstr_blocks': defnstr_count, 'already_done': already_done_count,
            'translated': 0, 'skipped': 0,
            'output_file': None, 'backup_file': backup_path,
            'extra_result': None, 'extra_english': extra_eng,
            'already_complete': False, 'stopped': False,
            'extra_only': False, 'extra_already_added': False, 'extra_failed': False,
            'nav_updated': False, 'slots_added': 0,
        }
        base.update(kw)
        return (base['output_file'] or filepath), base

    if not blocks_to_translate and lang_already_implemented and extra_eng:
        log(f"Language '{lang_name}' already implemented. Processing extra string only.", 'info')
        trans_result = _do_translate(extra_eng, lang_name)
        if isinstance(trans_result, tuple):
            translated_extra, tier = trans_result
        else:
            translated_extra = trans_result
            tier = "Google"
        if not translated_extra: return _ret(extra_only=True, extra_failed=True)
        if extra_string_already_added(lines_text, lang_name, translated_extra):
            return _ret(extra_only=True, extra_already_added=True, extra_result=translated_extra)
        insert_pos, ref_len = find_extra_string_insert_position(lines_text, lang_name, nav_order)
        if insert_pos is None: return _ret(extra_only=True, extra_failed=True, extra_result=translated_extra)
        # pad_or_trim uses len() (Unicode code points) — same measure as word-counter tools.
        # Do NOT wrap with encode_for_file: it would strip the backtick padding.
        fitted = pad_or_trim(translated_extra, ref_len)
        lines.insert(insert_pos, build_line('DEFSTR', fitted, lang_name) + eol)
        log(f"  ✓ Extra: '{extra_eng}' → '{translated_extra}' [{tier}] — committed at line {insert_pos + 1}", 'ok')
        base_p, ext = os.path.splitext(filepath)
        out_path = f"{base_p}_{lang_name}{ext}"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return _ret(extra_only=True, translated=1, output_file=out_path, extra_result=translated_extra)

    if not blocks_to_translate and not extra_eng:
        return _ret(already_complete=True)

    unique_texts = list({b['english_raw'].rstrip(BACKTICK) for b in blocks_to_translate})
    if extra_eng: unique_texts.append(extra_eng)
    log(f"Unique strings       : {len(unique_texts)} — translating…", 'info')
    cache = translate_parallel(unique_texts, lang_code, lang_name, stop_event, on_progress)
    was_stopped = stop_event.is_set()

    insertions  = []; slot_adds = []
    translated_count = 0; skipped_count = 0; slots_added_count = 0

    for block in blocks_to_translate:
        eng_text   = block['english_raw'].rstrip(BACKTICK)
        trans_result = cache.get(eng_text)
        if not trans_result: skipped_count += 1; continue
        
        # Handle (text, tier) tuple from new translation engine
        if isinstance(trans_result, tuple):
            translated, tier = trans_result
        else:
            translated = trans_result
            tier = "Google"
            
        if not translated: skipped_count += 1; continue

        free_slots    = count_trailing_free_slots(block['group'])
        last_line_idx = block['group'][-1][0]
        if free_slots == 0:
            slot_adds.append((last_line_idx, block['str_len'], block['pragma_type']))
            slots_added_count += 1

        # pad_or_trim uses len() (Unicode code points) — same measure as word-counter tools.
        # Do NOT wrap with encode_for_file: it would strip the backtick padding.
        fitted     = pad_or_trim(translated, block['str_len'])
        new_line   = build_line(block['pragma_type'], fitted, lang_name)
        insert_pos = get_nav_insert_position(block, lang_name, lines_text, nav_order)
        insertions.append((insert_pos, new_line, last_line_idx if free_slots == 0 else None))
        log(f"  ✓ [{block['pragma_type']}] Line {insert_pos + 1}: '{eng_text}'  →  '{translated}' [{tier}]"
            + (f"  [+{AUTO_FREE_SLOTS} slots at lines {last_line_idx + 2}-{last_line_idx + 1 + AUTO_FREE_SLOTS}]" if free_slots == 0 else ""), 'ok')
        translated_count += 1

    extra_result = cache.get(extra_eng) if extra_eng else None
    if extra_result and isinstance(extra_result, tuple):
        extra_result = extra_result[0]  # Extract text from (text, tier) tuple

    slot_adds_sorted = sorted(set((li, sl, pt) for li, sl, pt in slot_adds),
                              key=lambda x: x[0], reverse=True)
    ops = []
    for li, sl, pt in slot_adds_sorted:
        ops.append(('slot', li, sl, pt))
    for ins_pos, new_line, _ in sorted(insertions, key=lambda x: x[0], reverse=True):
        ops.append(('trans', ins_pos, new_line))
    ops.sort(key=lambda x: x[1], reverse=True)

    for op in ops:
        if op[0] == 'slot':
            _, after_li, sl, pt = op
            for i in range(AUTO_FREE_SLOTS):
                lines.insert(after_li + 1 + i, build_line(pt, BACKTICK * sl) + eol)
                log(f"  ℹ️  Free slot {i+1}/{AUTO_FREE_SLOTS} added at line {after_li + 2 + i}", 'info')
        else:
            _, ins_idx, new_line = op
            lines.insert(ins_idx, new_line + eol)
            log(f"  ✓ Translation committed at line {ins_idx + 1}", 'ok')

    nav_updated = False
    if translated_count > 0 and not was_stopped:
        lines_before = len(lines)
        lines = update_nav_comment_block(lines, lang_name, eol)
        nav_updated = len(lines) != lines_before
        if nav_updated:
            new_nav_line = len(lines) - 1
            log(f"  ✓ Navigation comment block updated with '{lang_name}' at line {new_nav_line + 1}", 'ok')

    if slots_added_count > 0:
        log(f"  ℹ️  Auto-added {AUTO_FREE_SLOTS} free slots to {slots_added_count} full block(s)", 'info')

    base_p, ext = os.path.splitext(filepath)
    suffix    = f"_{lang_name}_partial" if was_stopped else f"_{lang_name}"
    out_path  = f"{base_p}{suffix}{ext}"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    if was_stopped: log(f"\n⛔ Stopped — partial saved.", 'warn')

    return _ret(stopped=was_stopped, translated=translated_count,
                skipped=skipped_count, output_file=out_path,
                extra_result=extra_result, nav_updated=nav_updated,
                slots_added=slots_added_count)


# ─────────────────────────── SETTINGS DIALOG ──────────────────────────────
# (NEW in v2.0)

class SettingsDialog(tk.Toplevel):
    COLORS = {
        'bg':      '#1e1e2e',
        'fg':      '#cdd6f4',
        'accent':  '#89b4fa',
        'entry_bg':'#313244',
        'btn_bg':  '#585b70',
        'green':   '#a6e3a1',
        'red':     '#f38ba8',
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Translation Engine Settings")
        self.configure(bg=self.COLORS['bg'])
        self.resizable(False, False)
        self.grab_set()
        self._cfg = load_config()
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        C = self.COLORS
        pad = dict(padx=12, pady=6)

        tk.Label(self, text="Translation Engine Settings",
                 bg=C['bg'], fg=C['accent'],
                 font=('Consolas', 13, 'bold')).grid(row=0, column=0, columnspan=3,
                                                      pady=(14, 4), padx=14)

        tk.Label(self, text="DeepL API Key:", bg=C['bg'], fg=C['fg'],
                 font=('Consolas', 10)).grid(row=1, column=0, sticky='e', **pad)

        self._key_var = tk.StringVar(value=self._cfg.get('deepl_api_key', ''))
        self._key_entry = tk.Entry(self, textvariable=self._key_var, show='*',
                                   bg=C['entry_bg'], fg=C['fg'], width=40,
                                   insertbackground=C['fg'],
                                   font=('Consolas', 10))
        self._key_entry.grid(row=1, column=1, **pad)

        self._show_btn = tk.Button(self, text='👁', bg=C['btn_bg'], fg=C['fg'],
                                   command=self._toggle_show,
                                   font=('Consolas', 10), relief='flat', cursor='hand2')
        self._show_btn.grid(row=1, column=2, **pad)

        # Buttons
        btn_frame = tk.Frame(self, bg=C['bg'])
        btn_frame.grid(row=2, column=0, columnspan=3, pady=8)

        tk.Button(btn_frame, text='Test Connection', bg=C['btn_bg'], fg=C['fg'],
                  command=self._test_key, font=('Consolas', 10), relief='flat',
                  cursor='hand2').pack(side='left', padx=6)

        tk.Button(btn_frame, text='Save Settings', bg=C['accent'], fg=C['bg'],
                  command=self._save, font=('Consolas', 10, 'bold'), relief='flat',
                  cursor='hand2').pack(side='left', padx=6)

        self._test_label = tk.Label(self, text="", bg=C['bg'], fg=C['green'],
                                    font=('Consolas', 9))
        self._test_label.grid(row=3, column=0, columnspan=3, pady=2)

        # Engine status per language
        tk.Label(self, text="Engine status per language:",
                 bg=C['bg'], fg=C['accent'],
                 font=('Consolas', 10, 'bold')).grid(row=4, column=0, columnspan=3,
                                                      pady=(10, 2), padx=14, sticky='w')

        self._status_text = scrolledtext.ScrolledText(self, height=12, width=52,
                                                       bg=C['entry_bg'], fg=C['fg'],
                                                       font=('Consolas', 9),
                                                       state='disabled')
        self._status_text.grid(row=5, column=0, columnspan=3, padx=14, pady=(0, 14))

    def _toggle_show(self):
        cur = self._key_entry.cget('show')
        self._key_entry.config(show='' if cur == '*' else '*')

    def _test_key(self):
        key = self._key_var.get().strip()
        if not key:
            self._test_label.config(text='✗ No key entered.', fg=self.COLORS['red'])
            return
        try:
            import deepl
            t = deepl.Translator(key)
            usage = t.get_usage()
            remaining = usage.character.limit - usage.character.count
            self._test_label.config(
                text=f'✓ DeepL active — {remaining:,} chars remaining',
                fg=self.COLORS['green'])
            global _deepl_translator
            _deepl_translator = t
        except Exception as e:
            self._test_label.config(text=f'✗ {e}', fg=self.COLORS['red'])

    def _save(self):
        self._cfg['deepl_api_key'] = self._key_var.get().strip()
        save_config(self._cfg)
        global _deepl_translator
        _deepl_translator = None   # force re-init with new key
        self._test_label.config(text='✓ Saved!', fg=self.COLORS['green'])
        self._refresh_status()

    def _refresh_status(self):
        has_key  = bool(self._key_var.get().strip())
        deepl_ok = has_key
        lines = []
        for lname in sorted(LANGUAGES):
            if lname in DEEPL_UNSUPPORTED or lname not in DEEPL_LANG_MAP:
                tier = "Google Translate (Tier 2) — DeepL not supported"
            elif deepl_ok:
                tier = "DeepL ✓ (Tier 1)"
            else:
                tier = "Google Translate (Tier 2) — no DeepL key"
            lines.append(f"  {lname:<14} → {tier}")

        self._status_text.config(state='normal')
        self._status_text.delete('1.0', 'end')
        self._status_text.insert('end', '\n'.join(lines))
        self._status_text.config(state='disabled')


# ─────────────────────────── GUI ────────────────────────────────────────────

class DefStrTranslatorApp:

    def __init__(self, root):
        self.root        = root
        self.root.title("Multi-Language Display Translator — Secure Meters Ltd.")
        self.root.geometry("760x700")
        self.root.resizable(True, True)
        self._q          : queue.Queue     = queue.Queue()
        self._stop_event : threading.Event = threading.Event()
        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        BG="#1e1e2e"; FG="#cdd6f4"; ACCENT="#89b4fa"; BTN_BG="#313244"; ENTRY_BG="#313244"
        self.root.configure(bg=BG)
        st = ttk.Style(); st.theme_use('clam')
        st.configure('TLabel',       background=BG,       foreground=FG,     font=('Segoe UI', 10))
        st.configure('TButton',      background=BTN_BG,   foreground=FG,     font=('Segoe UI', 10, 'bold'), padding=6)
        st.configure('Stop.TButton', background='#c0392b',foreground='white',font=('Segoe UI', 10, 'bold'), padding=6)
        st.configure('TCombobox',    fieldbackground=ENTRY_BG, background=BTN_BG, foreground=FG, font=('Segoe UI', 10))
        st.configure('TFrame',       background=BG)
        st.configure('TLabelframe',  background=BG, foreground=ACCENT)
        st.configure('TLabelframe.Label', background=BG, foreground=ACCENT, font=('Segoe UI', 10, 'bold'))
        st.configure('TProgressbar', troughcolor=BTN_BG, background=ACCENT)
        st.map('TButton',      background=[('active', ACCENT)],    foreground=[('active', '#1e1e2e')])
        st.map('Stop.TButton', background=[('active', '#e74c3c')], foreground=[('active', 'white')])
        pad = dict(padx=12, pady=6)

        tk.Label(self.root, text="Multi-Language Display Translator",
                 font=('Segoe UI', 15, 'bold'), bg=BG, fg=ACCENT).pack(pady=(16, 4))
        tk.Label(self.root, text="Secure Meters Ltd.",
                 font=('Segoe UI', 9), bg=BG, fg="#6c7086").pack(pady=(0, 12))

        frm = ttk.LabelFrame(self.root, text=" Inputs ", padding=12)
        frm.pack(fill='x', padx=16, pady=4)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Target Language *").grid(row=0, column=0, sticky='w', **pad)
        self.lang_var = tk.StringVar(value="Portuguese")
        ttk.Combobox(frm, textvariable=self.lang_var, values=sorted(LANGUAGES.keys()),
                     state='readonly', width=30).grid(row=0, column=1, sticky='ew', **pad)
        
        # NEW: Engine status indicator
        self.engine_label = tk.Label(frm, text="", bg=ENTRY_BG, fg="#89b4fa",
                                     font=('Segoe UI', 9))
        self.engine_label.grid(row=0, column=2, sticky='w', **pad)
        
        # Bind language change event to update engine status
        self.lang_var.trace('w', self._on_lang_change)

        ttk.Label(frm, text="Input .h File *").grid(row=1, column=0, sticky='w', **pad)
        ff = ttk.Frame(frm); ff.grid(row=1, column=1, sticky='ew', **pad); ff.columnconfigure(0, weight=1)
        self.file_var = tk.StringVar()
        tk.Entry(ff, textvariable=self.file_var, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                 font=('Segoe UI', 9), relief='flat').grid(row=0, column=0, sticky='ew', ipady=4)
        ttk.Button(ff, text="Browse…", command=self._browse).grid(row=0, column=1, padx=(6, 0))

        ttk.Label(frm, text="English String *").grid(row=2, column=0, sticky='nw', **pad)
        self.eng_var = tk.StringVar()
        tk.Entry(frm, textvariable=self.eng_var, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                 font=('Segoe UI', 10), relief='flat').grid(row=2, column=1, sticky='ew', **pad, ipady=4)

        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(self.root, variable=self.progress_var,
                        maximum=100, mode='determinate').pack(fill='x', padx=16, pady=6)
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.root, textvariable=self.status_var, bg=BG,
                 fg="#a6e3a1", font=('Segoe UI', 9)).pack()

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        self.btn_start = ttk.Button(btn_frame, text="⚡  Translate & Append", command=self._start)
        self.btn_start.grid(row=0, column=0, padx=(0, 8), ipadx=10)
        self.btn_stop = ttk.Button(btn_frame, text="⛔  Stop",
                                   style='Stop.TButton', command=self._stop, state='disabled')
        self.btn_stop.grid(row=0, column=1, padx=(0, 8), ipadx=10)
        ttk.Button(btn_frame, text="⚙  Settings", command=self._open_settings).grid(row=0, column=2, ipadx=10)

        lf = ttk.LabelFrame(self.root, text=" Output Log ", padding=8)
        lf.pack(fill='both', expand=True, padx=16, pady=(0, 16))
        self.log = scrolledtext.ScrolledText(lf, height=14, wrap='word', bg="#181825", fg=FG,
                                             font=('Consolas', 9), relief='flat', insertbackground=FG)
        self.log.pack(fill='both', expand=True)
        self.log.tag_config('ok',   foreground='#a6e3a1')
        self.log.tag_config('err',  foreground='#f38ba8')
        self.log.tag_config('info', foreground='#89dceb')
        self.log.tag_config('warn', foreground='#f9e2af')

    def _stop(self):
        self._stop_event.set()
        self.btn_stop.config(state='disabled')
        self.status_var.set("Stopping…")
        self._put('log', "⛔ Stop requested…", 'warn')

    def _open_settings(self):
        SettingsDialog(self.root)
        self._on_lang_change()
    
    def _on_lang_change(self, *args):
        """Update engine status indicator when language changes."""
        lang = self.lang_var.get()
        if not lang:
            self.engine_label.config(text="")
            return
        has_key = bool(load_config().get('deepl_api_key', '').strip())
        if lang in DEEPL_UNSUPPORTED or lang not in DEEPL_LANG_MAP:
            self.engine_label.config(text="Google (Tier 2)")
        elif has_key:
            self.engine_label.config(text="DeepL ✓ (T1)")
        else:
            self.engine_label.config(text="Google (Tier 2)")

    def _poll_queue(self):
        try:
            while True:
                cmd, *args = self._q.get_nowait()
                if cmd == 'log':
                    msg, tag = args
                    self.log.insert('end', msg + '\n', tag); self.log.see('end')
                elif cmd == 'progress':
                    done, total, text = args
                    self.progress_var.set((done / total * 100) if total else 0)
                    self.status_var.set(f"Translating {done}/{total}: {text[:40]}…")
                elif cmd == 'new_block_done':
                    out_path, stats = args
                    self.progress_var.set(100)
                    self.btn_start.config(state='normal')
                    self.btn_stop.config(state='disabled')
                    self.status_var.set("New string block added!")
                    self.log.insert('end', f"\n✅ New string block inserted!\n", 'ok')
                    self.log.insert('end', f"   English  : '{stats['new_english']}'\n", 'info')
                    self.log.insert('end', f"   Length   : {stats['str_length']}\n", 'info')
                    self.log.insert('end', f"   Languages: {stats['lang_count']} translated"
                                           f"  +  {AUTO_FREE_SLOTS} free slots\n", 'ok')
                    self.log.insert('end', f"   Output   : {stats['output_file']}\n", 'ok')
                    self.log.see('end')
                    messagebox.showinfo("New String Added",
                        f"New string block added!\n\n"
                        f"English  : '{stats['new_english']}'\n"
                        f"Length   : {stats['str_length']}\n"
                        f"Languages: {stats['lang_count']} translated\n"
                        f"Free slots: {AUTO_FREE_SLOTS} added at end\n\n"
                        f"Output: {stats['output_file']}")
                elif cmd == 'done':
                    out_path, stats = args
                    self.btn_start.config(state='normal')
                    self.btn_stop.config(state='disabled')
                    lang = self.lang_var.get()
                    if stats.get('extra_already_added'):
                        self.progress_var.set(100)
                        self.status_var.set("Extra string already exists!")
                        self.log.insert('end',
                            f"\n⚠️  Extra string already added previously.\n"
                            f"   English   : '{stats['extra_english']}'\n"
                            f"   Translated: '{stats['extra_result']}'\n"
                            f"   No changes were made.\n", 'warn')
                        self.log.see('end')
                        messagebox.showinfo("Already Added",
                            f"This extra string already exists in the file.\n\n"
                            f"English   : '{stats['extra_english']}'\n"
                            f"Translated: '{stats['extra_result']}'\n\n"
                            f"No changes were made.")
                    elif stats.get('extra_only') and not stats.get('extra_failed'):
                        self.progress_var.set(100)
                        self.status_var.set("Extra string added!")
                        self.log.insert('end',
                            f"\n✅ Extra string added!\n"
                            f"   '{stats['extra_english']}'  →  '{stats['extra_result']}'\n"
                            f"   Output : {stats['output_file']}\n", 'ok')
                        self.log.see('end')
                        messagebox.showinfo("Extra String Added",
                            f"Extra string added.\n\n"
                            f"English   : '{stats['extra_english']}'\n"
                            f"Translated: '{stats['extra_result']}'\n\n"
                            f"Output: {stats['output_file']}")
                    elif stats.get('extra_failed'):
                        self.status_var.set("Error.")
                        self.log.insert('end', f"\n❌ Could not add extra string.\n", 'err')
                        self.log.see('end')
                        messagebox.showerror("Error", f"Could not add: '{stats['extra_english']}'")
                    elif stats.get('already_complete'):
                        self.progress_var.set(100)
                        self.status_var.set(f"{lang} already translated!")
                        self.log.insert('end',
                            f"\n✅ '{lang}' translation already exists in this file.\n"
                            f"   Blocks already translated : {stats['already_done']}\n"
                            f"   No changes were made.\n", 'ok')
                        self.log.see('end')
                        messagebox.showinfo("Already Translated",
                            f"'{lang}' translation already exists in this file.\n\n"
                            f"Blocks already translated : {stats['already_done']}\n\n"
                            f"No changes were made.")
                    elif stats.get('stopped'):
                        self.status_var.set("Stopped.")
                        self.log.insert('end', "\n⛔ Stopped.\n", 'warn')
                        self.log.insert('end', f"   Translated so far : {stats['translated']}\n", 'ok')
                        self.log.insert('end', f"   Partial output    : {stats['output_file']}\n", 'warn')
                        self.log.see('end')
                        messagebox.showwarning("Stopped",
                            f"Translated so far : {stats['translated']}\n"
                            f"Partial output    : {stats['output_file']}")
                    else:
                        self.progress_var.set(100)
                        self.status_var.set("Done!")
                        self.log.insert('end', "\n✅ Complete!\n", 'ok')
                        self.log.insert('end',
                            f"   Total blocks    : {stats['total_blocks']}"
                            f"  (DEFSTR: {stats['defstr_blocks']}  DEFNSTR: {stats['defnstr_blocks']})\n", 'info')
                        self.log.insert('end', f"   Already done    : {stats['already_done']}  (skipped)\n", 'info')
                        self.log.insert('end', f"   Translated      : {stats['translated']}\n", 'ok')
                        if stats.get('slots_added', 0) > 0:
                            self.log.insert('end',
                                f"   Auto free slots : added to {stats['slots_added']} block(s)\n", 'info')
                        if stats['skipped']:
                            self.log.insert('end', f"   API errors      : {stats['skipped']}\n", 'warn')
                        if stats.get('nav_updated'):
                            self.log.insert('end', f"   Nav comment     : updated ✓\n", 'ok')
                        self.log.insert('end', f"   Output          : {stats['output_file']}\n", 'ok')
                        self.log.insert('end', f"   Backup          : {stats['backup_file']}\n", 'info')
                        if stats['extra_result']:
                            self.log.insert('end',
                                f"\n📝 '{stats['extra_english']}'  →  '{stats['extra_result']}'\n", 'ok')
                        self.log.see('end')
                        messagebox.showinfo("Done",
                            f"Translation complete!\n\n"
                            f"Total   : {stats['total_blocks']}\n"
                            f"Done    : {stats['translated']}\n\n"
                            f"Output: {stats['output_file']}")
                elif cmd == 'error':
                    msg, = args
                    self.status_var.set("Error!")
                    self.log.insert('end', f"\n❌ {msg}\n", 'err')
                    self.log.see('end')
                    self.btn_start.config(state='normal')
                    self.btn_stop.config(state='disabled')
                    messagebox.showerror("Error", msg)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_queue)

    def _browse(self):
        path = filedialog.askopenfilename(title="Select .h file",
                                          filetypes=[("Header files", "*.h"), ("All files", "*.*")])
        if path: self.file_var.set(path)

    def _put(self, *args):
        self._q.put(args)

    def _start(self):
        lang_name = self.lang_var.get().strip()
        filepath  = self.file_var.get().strip()
        extra_eng = self.eng_var.get().strip()

        if not lang_name:   messagebox.showerror("Input Error", "Select a target language."); return
        if not filepath:    messagebox.showerror("Input Error", "Select an input .h file."); return
        if not os.path.isfile(filepath): messagebox.showerror("File Error", f"Not found:\n{filepath}"); return
        lang_code = LANGUAGES.get(lang_name)
        if not lang_code:   messagebox.showerror("Error", f"Unknown language: {lang_name}"); return

        # ── PRE-CHECK Issue 1: No extra_eng → check whole file ───────────────
        if not extra_eng:
            already, count = check_already_translated(filepath, lang_name, specific_english=None)
            if already:
                messagebox.showinfo(
                    "Already Translated",
                    f"'{lang_name}' translation already exists in this file.\n\n"
                    f"Blocks already translated : {count}\n\n"
                    f"No changes were made.")
                return

        if extra_eng:
            # Try UTF-8 first, fall back to Latin-1 for existing files
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines_text_check = [l.rstrip('\r\n') for l in f.read().splitlines()]
            except UnicodeDecodeError:
                with open(filepath, 'r', encoding='latin-1') as f:
                    lines_text_check = [l.rstrip('\r\n') for l in f.read().splitlines()]
            string_exists = english_string_exists_in_file(lines_text_check, extra_eng)

            if string_exists:
                # ── PRE-CHECK Issue 2: String exists → check if already translated ──
                already, count = check_already_translated(filepath, lang_name, specific_english=extra_eng)
                if already:
                    messagebox.showinfo(
                        "Already Translated",
                        f"'{extra_eng}' is already translated in '{lang_name}'.\n\n"
                        f"No changes were made.")
                    return

            if not string_exists:
                str_length = simpledialog.askinteger(
                    "New String — Length",
                    f"'{extra_eng}' is a NEW string not found in the file.\n\n"
                    f"Enter the string length (chars incl. backtick padding):\n"
                    f"Tip: common lengths are 22, 25, 30 etc.",
                    parent=self.root, minvalue=1, maxvalue=200)
                if not str_length: return

                self._stop_event.clear()
                self.btn_start.config(state='disabled')
                self.btn_stop.config(state='normal')
                self.log.delete('1.0', 'end')
                self.progress_var.set(0)
                self.status_var.set("Building new string block…")
                self._put('log', f"➕ New string: '{extra_eng}'  (length={str_length})", 'info')
                self._put('log', f"   File: {os.path.basename(filepath)}", 'info')
                self._put('log', "─" * 62, 'info')

                def new_worker():
                    try:
                        out_path, stats = add_new_string_block(
                            filepath, extra_eng, str_length,
                            on_log      = lambda msg, tag: self._put('log', msg, tag),
                            on_progress = lambda d, t, txt: self._put('progress', d, t, txt),
                        )
                        self._put('new_block_done', out_path, stats)
                    except Exception as e:
                        self._put('error', str(e))

                threading.Thread(target=new_worker, daemon=True).start()
                return

        self._stop_event.clear()
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.log.delete('1.0', 'end')
        self.progress_var.set(0)
        self.status_var.set("Scanning file…")
        self._put('log', f"→ {lang_name} ({lang_code})  |  {os.path.basename(filepath)}", 'info')
        if extra_eng: self._put('log', f"Extra string: '{extra_eng}'", 'info')
        self._put('log', "─" * 62, 'info')

        def worker():
            try:
                out_path, stats = process_file(filepath, lang_name, lang_code, extra_eng,
                    stop_event  = self._stop_event,
                    on_progress = lambda d, t, txt: self._put('progress', d, t, txt),
                    on_log      = lambda msg, tag:  self._put('log', msg, tag))
                self._put('done', out_path, stats)
            except Exception as e:
                self._put('error', str(e))

        threading.Thread(target=worker, daemon=True).start()


# ─────────────────────────── ENTRY ──────────────────────────────────────────

if __name__ == '__main__':
    root = tk.Tk()
    DefStrTranslatorApp(root)
    root.mainloop()
