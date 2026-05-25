import io
import fitz


def extract_text(content: bytes, filename: str) -> str:
    fn = (filename or "").lower()
    if fn.endswith(".pdf"):
        pdf  = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text() for page in pdf)
        pdf.close()
    elif fn.endswith((".docx", ".doc")):
        import docx
        doc  = docx.Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise ValueError("Only PDF and DOCX files are supported.")
    if not text.strip():
        raise ValueError("Could not extract any text from the file.")
    return text


def extract_job_title(jd_text: str) -> str:
    import re
    import os
    import anthropic as _anthropic

    label_patterns = [
        r'(?:job\s+title|position\s+title|role\s+title|title)\s*[:\-]\s*(.+)',
        r'(?:position|role|opening)\s*[:\-]\s*(.+)',
        r'(?:we\s+are\s+(?:hiring|looking)\s+for|seeking)\s+(?:a\s+|an\s+)?(.+?)(?:\s+to\b|\s+who\b|\s*[.,]|$)',
        r'(?:vacancy|opening)\s+for\s+(?:a\s+|an\s+)?(.+?)(?:\s*[.,]|$)',
    ]
    for line in jd_text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        for pat in label_patterns:
            m = re.search(pat, stripped, re.IGNORECASE)
            if m:
                title = m.group(1).strip().rstrip('.,;:').strip()
                if 3 <= len(title) <= 80:
                    return title[:60]

    claude_key = os.getenv("CLAUDE_API_KEY")
    if claude_key:
        try:
            client = _anthropic.Anthropic(api_key=claude_key)
            resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=20,
                system="Extract only the job title from the job description. Reply with only the job title — no other words.",
                messages=[{"role": "user", "content": jd_text[:600]}],
            )
            title = resp.content[0].text.strip().strip('"\'').rstrip('.,;:')
            if 3 <= len(title) <= 80:
                return title[:60]
        except Exception:
            pass

    for line in jd_text.split('\n'):
        line = line.strip()
        if line and len(line) <= 80:
            return line[:60]
    return "the position"
