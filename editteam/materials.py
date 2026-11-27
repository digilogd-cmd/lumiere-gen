# -*- coding: utf-8 -*-
"""대본 파일 읽기(txt·md·rtf·docx·hwpx·hwp·doc) — 생성형 의뢰서가 씀.
(뤼미에르 에디트의 materials.py 에서 대본 읽기만 남김 — 2026-10-09 젠 분리 정리)"""
import html, os, re, subprocess, zipfile, zlib

SCRIPT = (".txt", ".md", ".docx", ".doc", ".hwp", ".hwpx", ".rtf")


def _xml_text(xml, tags):
    out = []
    for para in re.split(r"</(?:w:p|hp:p)>", xml):
        t = "".join(re.findall(r"<(?:%s)[^>]*>([^<]*)</(?:%s)>" % (tags, tags), para))
        if t.strip():
            out.append(html.unescape(t))
    return "\n".join(out)


def read_hwp(path):
    """한글 5.x(hwp) 본문 글자. 레코드 HWPTAG_PARA_TEXT(67)만 모은다."""
    import olefile
    f = olefile.OleFileIO(path)
    head = f.openstream("FileHeader").read()
    compressed = bool(head[36] & 1)
    secs = sorted([e for e in f.listdir() if e[0] == "BodyText"], key=lambda e: int(re.sub(r"\D", "", e[1]) or 0))
    paras = []
    for e in secs:
        data = f.openstream(e).read()
        if compressed:
            data = zlib.decompress(data, -15)
        i = 0
        while i + 4 <= len(data):
            h = int.from_bytes(data[i:i + 4], "little"); i += 4
            tag, size = h & 0x3FF, (h >> 20) & 0xFFF
            if size == 0xFFF:
                size = int.from_bytes(data[i:i + 4], "little"); i += 4
            rec = data[i:i + size]; i += size
            if tag != 67:
                continue
            w = [int.from_bytes(rec[k:k + 2], "little") for k in range(0, len(rec) - 1, 2)]
            s, k = [], 0
            while k < len(w):
                c = w[k]
                if c >= 32:
                    s.append(chr(c)); k += 1
                elif c in (10, 13):
                    s.append("\n"); k += 1
                elif c == 0 or 24 <= c <= 31:
                    k += 1
                else:                     # 확장·인라인 컨트롤은 8글자 묶음
                    k += 8
            t = "".join(s).strip()
            if t:
                paras.append(t)
    f.close()
    return "\n".join(paras)


def read_doc_with_word(path):
    out = os.path.splitext(path)[0] + "__lumiere_tmp.txt"
    ps = ("$w = New-Object -ComObject Word.Application; $w.Visible = $false; try { "
          f"$d = $w.Documents.Open('{path}', $false, $true); $d.SaveAs2('{out}', 7, $false, '', $false, '', $false, $false, $false, $false, $false, 65001); $d.Close($false) "
          "} finally { $w.Quit() }")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True)
    if not os.path.exists(out):
        raise RuntimeError("옛 워드(doc) 파일은 MS 워드가 있어야 읽을 수 있어요. 워드에서 docx로 저장해 주세요.")
    t = open(out, encoding="utf-8", errors="replace").read()
    os.remove(out)
    return t


def read_text(path):
    e = os.path.splitext(path)[1].lower()
    if e in (".txt", ".md", ".rtf"):
        raw = open(path, "rb").read()
        for enc in ("utf-8-sig", "cp949", "utf-16"):
            try:
                t = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            t = raw.decode("utf-8", "replace")
        if e == ".rtf":
            t = re.sub(r"\\[a-z]+-?\d* ?|[{}]", "", t)
        return t
    if e == ".docx":
        return _xml_text(zipfile.ZipFile(path).read("word/document.xml").decode("utf8"), "w:t")
    if e == ".hwpx":
        z = zipfile.ZipFile(path)
        secs = sorted([n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)], key=lambda n: int(re.findall(r"\d+", n)[0]))
        return "\n".join(_xml_text(z.read(n).decode("utf8"), "hp:t") for n in secs)
    if e == ".hwp":
        return read_hwp(path)
    if e == ".doc":
        return read_doc_with_word(path)
    raise RuntimeError(f"읽을 수 없는 대본 형식: {e}")

