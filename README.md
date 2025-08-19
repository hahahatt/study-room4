# study-room4


### 필요 라이브러리 설치

- 몽고 DB연결 및 UI/UX
    - pip install streamlit pymongo[srv] python-dotenv

- 마스킹 부분
    - pip install torch transformers


### 몽고디비 연결 
1. VS Code Extension에서 mongoDB 검색 
2. MongoDB for VS Code 설치
3. 왼쪽 사이드바에 MongoDB Extention 클릭(나뭇잎 모양)
4. 왼쪽에 흰색 박스에 있는 connect 클릭
5. 위에 뜬 창에 다음의 값 입력 후 엔터 mongodb+srv://ehddnsdl35:<db_password>@insiderlock.nvk6wbj.mongodb.net/
6. .env 파일 생성 후 디스코드에 있는 내용으로 env파일 내용 채우기
7. 실행은 작업 폴더가 STUDY-ROOM4일 때 터미널 창에서 streamlit run ./streamlit/app.py 하시면 됩니다.