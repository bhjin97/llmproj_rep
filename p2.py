import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import plotly.express as px
from PIL import Image
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from openai import OpenAI
from dotenv import load_dotenv
import os
import mysql.connector

# 페이지 기본 설정
st.set_page_config(page_title="츄러스미 심리케어",layout='wide')

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",   # 배포 시에는 docker-compose 또는 RDS 주소
        user="root",
        password="1234",    # ✅ 실제 설정한 비밀번호
        database="Churo2_db"
    )

# 세션 상태 초기화 -------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# 로그인 함수 ------------------------------------------
def get_user_from_db(username, password):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, login_id, role FROM Member WHERE login_id=%s AND password=%s",
        (username, password)  # username은 실제로 login_id에 매핑됨
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def login():
    st.subheader("🔐 로그인")
    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")
    
    if st.button("로그인"):
        user = get_user_from_db(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user["login_id"]
            st.session_state.role = user["role"]
            st.session_state.user_id = user["user_id"]   # ✅ DB user_id 저장
            st.success(f"로그인 성공! 환영합니다 {user['login_id']}님")
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 잘못되었습니다 😓")

                
def register_user(login_id, name, gender, age, address, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 중복 체크
    cursor.execute("SELECT COUNT(*) FROM Member WHERE login_id=%s", (login_id,))
    if cursor.fetchone()[0] > 0:
        cursor.close()
        conn.close()
        return False, "이미 존재하는 아이디입니다."
    
    cursor.execute("""
        INSERT INTO Member (login_id, name, gender, age, address, password, role)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (login_id, name, gender, age, address, password, "user"))
    
    conn.commit()
    cursor.close()
    conn.close()
    return True, "회원가입 성공! 로그인 해주세요."
                
st.subheader("🔐 로그인")
username = st.text_input("아이디")      # DB의 login_id 컬럼과 매핑
password = st.text_input("비밀번호", type="password")

if st.button("로그인"):
    user = get_user_from_db(username, password)  # username=login_id
    if user:
        st.session_state.logged_in = True
        st.session_state.username = user["login_id"]  # UI 출력용
        st.session_state.role = user["role"]
        st.session_state.user_id = user["user_id"]    # DB 참조용 PK
        st.success(f"로그인 성공! 환영합니다 {user['login_id']}님")
        st.rerun()
    else:
        st.error("아이디 또는 비밀번호가 잘못되었습니다 😓")

    
    