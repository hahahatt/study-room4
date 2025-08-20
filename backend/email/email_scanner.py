from .pii_masker import mask_text, contains_sensitive_keywords
import pandas as pd
import docx
import PyPDF2
import pytesseract
from io import BytesIO
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def scan_image(file_obj):
    """
    이미지 파일에서 텍스트를 추출하여 문자열로 반환하는 함수.
    """
    try:
        print('===============================')
        print('Start!!\n', file_obj)
        img = Image.open(file_obj)
        print('===============================')
        
        text = pytesseract.image_to_string(img, lang='kor+eng')
        
        return text
    except FileNotFoundError:
        return "오류: 이미지를 찾을 수 없습니다. 경로를 다시 확인해 주세요."
    except Exception as e:
        return f"텍스트 추출 중 오류가 발생했습니다: {e}"

# 📄 OCR 기반 PDF 텍스트 추출 함수
def extract_text_from_pdf_with_ocr(file_obj):
    import pytesseract
    import fitz  # PyMuPDF
    from PIL import Image

    file_obj.seek(0)
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    full_text = ""

    for page in doc:
        pix = page.get_pixmap(dpi=250)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="kor+eng")
        full_text += text + "\n"

    return full_text

# 📬 메일 본문/제목/첨부파일 민감정보 스캐너
def scan_email(subject, body, attachments):
    warnings = []
    masked_body = mask_text(body)

    # 제목 키워드 탐지
    if contains_sensitive_keywords(subject, ["기밀", "내부문서", "계약서", "극비", "대외비"]):
        warnings.append("제목에 기밀 관련 키워드 포함")

    # 본문 마스킹 여부 확인
    if masked_body != body:
        warnings.append("본문에 개인정보 또는 민감 정보 포함")

    # 첨부파일 검사
    for file in attachments or []:
        try:
            file.seek(0)
        except Exception:
            pass

        filename = file.name.lower()
        content = ""

        try:
            if filename.endswith(".txt"):
                file.seek(0)
                content = file.read().decode("utf-8", errors="ignore")

            elif filename.endswith(".csv"):
                file.seek(0)
                df = pd.read_csv(file)
                content = df.to_string()

            elif filename.endswith(".xlsx"):
                file.seek(0)
                df = pd.read_excel(file)
                content = df.to_string()

            elif filename.endswith(".docx"):
                file.seek(0)
                docx_obj = docx.Document(file)
                content_parts = []

                # 본문
                content_parts.extend([p.text for p in docx_obj.paragraphs if p.text.strip()])

                # 테이블
                for table in docx_obj.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text.strip():
                                content_parts.append(cell.text)

                content = "\n".join(content_parts)

            elif filename.endswith(".pdf"):
                file.seek(0)
                reader = PyPDF2.PdfReader(file)
                content = "\n".join([page.extract_text() or "" for page in reader.pages])

                if not content.strip():
                    content = extract_text_from_pdf_with_ocr(file)

            elif filename.endswith(".jpg") or filename.endswith(".png"):
                file.seek(0)
                img_bytes = BytesIO(file.read())
                content = scan_image(img_bytes)

            else:
                continue

        except Exception as e:
            warnings.append(f"첨부파일 `{file.name}` 처리 중 오류 발생: {e}")
            continue

        # 민감 키워드 또는 마스킹 전후 비교로 탐지
        if (
            contains_sensitive_keywords(content, ["기밀", "내부자료", "주민번호", "카드번호", "주소", "전화번호", "이메일", "계좌번호", "이름"]) or
            mask_text(content) != content
        ):
            warnings.append(f"첨부파일 `{file.name}` 에 개인정보 또는 민감 정보 포함")

    return warnings, masked_body
