# apps/email/gmail_auth.py

import os
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_SECRET_FILE = os.path.join(os.path.dirname(__file__), "credentials", "client_secret.json")

@st.cache_resource  # 인증 객체 재사용
def authenticate_user():
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        return creds
    except Exception as e:
        st.error(f"❌ Gmail 인증 실패: {e}")
        return None

def build_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)
