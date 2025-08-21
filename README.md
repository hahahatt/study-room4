# study-room4


### 필요 라이브러리 

streamlit>=1.34
pymongo>=4.6
python-dotenv>=1.0
google-api-python-client>=2.130
google-auth>=2.31
google-auth-oauthlib>=1.2
pandas>=2.2
numpy>=1.26
pillow>=10.3
pytesseract>=0.3.10
python-docx>=1.1
openpyxl>=3.1
pymupdf>=1.24          # PDF 처리(읽기/마스킹)
opencv-python-headless>=4.10  # 이미지 전처리(서버/헤드리스 환경)

Tesseract : 
Invoke-WebRequest -Uri https://github.com/tesseract-ocr/tessdata_best/raw/main/kor.traineddata `
  -OutFile "C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata"


### 몽고디비 연결 
1. VS Code Extension에서 mongoDB 검색 
2. MongoDB for VS Code 설치
3. 왼쪽 사이드바에 MongoDB Extention 클릭(나뭇잎 모양)
4. 왼쪽에 흰색 박스에 있는 connect 클릭
5. 위에 뜬 창에 다음의 값 입력 후 엔터 mongodb+srv://ehddnsdl35:<db_password>@insiderlock.nvk6wbj.mongodb.net/
6. .env 파일 생성 후 디스코드에 있는 내용으로 env파일 내용 채우기
7. 실행은 작업 폴더가 STUDY-ROOM4일 때 터미널 창에서 streamlit run ./streamlit/app.py 하시면 됩니다.


# 3차 통합 이후
1. ner_model은 backend 폴더에 넣어주시면 됩니다
2. backend/credentials 폴더에 client_secret.json 파일 넣어주시면 됩니다. 해당 파일은 정희님이 디스코드에 올리신 통합.zip에 있습니다.

