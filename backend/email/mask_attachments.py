import pandas as pd
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader, PdfWriter
from .pii_masker import mask_text

def mask_attachment(file_obj):
    filename = file_obj.name
    ext = filename.split('.')[-1].lower()

    try:
        file_obj.seek(0)
    except Exception:
        pass

    try:
        if ext == "txt":
            text = file_obj.read().decode("utf-8", errors="ignore")
            masked = mask_text(text)
            return create_bytes_io(masked, filename)

        elif ext == "csv":
            try:
                df = pd.read_csv(file_obj, encoding="utf-8-sig")
            except UnicodeDecodeError:
                file_obj.seek(0)
                df = pd.read_csv(file_obj, encoding="euc-kr")

            for col in df.columns:
                df[col] = df[col].astype(str).apply(mask_text)

            output = BytesIO()
            df.to_csv(output, index=False, encoding="utf-8-sig")
            output.name = "masked_" + filename
            output.seek(0)
            return output

        elif ext == "docx":
            doc = Document(file_obj)
            for para in doc.paragraphs:
                para.text = mask_text(para.text)
            output = BytesIO()
            doc.save(output)
            output.name = "masked_" + filename
            output.seek(0)
            return output

        elif ext == "pdf":
            reader = PdfReader(file_obj)
            writer = PdfWriter()
            for page in reader.pages:
                text = page.extract_text() or ""
                masked = mask_text(text)
                writer.add_blank_page(width=page.mediabox.width, height=page.mediabox.height)
                # PDF가 잘안되네
            output = BytesIO()
            writer.write(output)
            output.name = "masked_" + filename
            output.seek(0)
            return output

        else:
            return None

    except Exception as e:
        print(f"[ERROR] 첨부파일 마스킹 실패: {e}")
        return None

def create_bytes_io(text, original_filename):
    output = BytesIO()
    output.write(text.encode("utf-8"))
    output.name = "masked_" + original_filename
    output.seek(0)
    return output
