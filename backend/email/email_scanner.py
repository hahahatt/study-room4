from .pii_masker import mask_text, contains_sensitive_keywords
import pandas as pd
import docx
import PyPDF2
from io import BytesIO

def scan_email(subject, body, attachments):
    warnings = []
    masked_body = mask_text(body)

    if contains_sensitive_keywords(subject, ["기밀", "내부문서", "계약서"]):
        warnings.append("제목에 기밀 관련 키워드 포함")

    if masked_body != body:
        warnings.append("본문에 개인정보 또는 민감 정보 포함")

    for file in attachments or []:
        filename = file.name.lower()
        content = ""

        if filename.endswith(".txt"):
            content = file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".csv"):
            df = pd.read_csv(file)
            content = df.to_string()
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(file)
            content = df.to_string()
        elif filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            content = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif filename.endswith(".docx"):
            doc = docx.Document(file)
            content = "\n".join([p.text for p in doc.paragraphs])
        else:
            continue

        if contains_sensitive_keywords(content, ["기밀", "내부자료", "주민번호", "카드번호"]):
            warnings.append(f"첨부파일 `{file.name}` 에 기밀 또는 개인정보 포함")

        try:
            file.seek(0)
        except Exception:
            pass

    return warnings, masked_body
