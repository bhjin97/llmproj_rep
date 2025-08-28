import streamlit as st
import mysql.connector
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
import os
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
import io
import base64, html

def load_avatar(path):
    img = Image.open(path)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

GPT_AVATAR_PATH = load_avatar("C:/githome/llmproj_rep/data/churros.png")
USER_AVATAR_PATH = load_avatar("C:/githome/llmproj_rep/data/profile.jpg")

st.markdown("""
<style>
.chat-row{display:flex; gap:8px; margin:8px 0; align-items:flex-end;}
.chat-row.user{justify-content:flex-end;}
.chat-row.bot{justify-content:flex-start;}
.chat-bubble{
  max-width:70%;
  padding:12px 16px;
  border-radius:18px;
  line-height:1.55;
  font-size:16px;
  box-shadow:0 4px 14px rgba(0,0,0,.06);
  word-break:break-word;
  white-space:pre-wrap;
}
.chat-bubble.user{background:#e8f5e9; border-top-right-radius:6px;}
.chat-bubble.bot{background:#f5f7fb; border-top-left-radius:6px;}
.chat-avatar{
  width:36px; height:36px; border-radius:50%;
  object-fit:cover;
  box-shadow:0 2px 6px rgba(0,0,0,.12);
}
</style>
""", unsafe_allow_html=True)

def _bytes_to_data_uri(img_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(img_bytes).decode()

def render_bubble(role: str, text: str, avatar_bytes: bytes = None):
    """role: 'user' or 'bot'."""
    bubble_cls = "user" if role == "user" else "bot"
    # 안전하게 특수문자 이스케이프
    safe_text = html.escape(text)
    # 간단한 이모지/줄바꿈 허용하고 싶으면 아래 라인 사용
    # safe_text = safe_text.replace("\\n", "<br>")
    av_html = ""
    if avatar_bytes:
        av_html = f'<img class="chat-avatar" src="{_bytes_to_data_uri(avatar_bytes)}" />'

    if role == "user":
        # [말풍선] [아바타]
        html_block = f'''
        <div class="chat-row user">
          <div class="chat-bubble user">{safe_text}</div>
          {av_html}
        </div>
        '''
    else:
        # [아바타] [말풍선]
        html_block = f'''
        <div class="chat-row bot">
          {av_html}
          <div class="chat-bubble bot">{safe_text}</div>
        </div>
        '''
    st.markdown(html_block, unsafe_allow_html=True)

# ✅ 세션 상태 초기화 (맨 위에서 딱 한 번만 실행)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ========== 환경 변수 로드 ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
client = OpenAI(api_key=OPENAI_API_KEY)

# ========== DB 연결 ==========
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="Churo2_db"
    )

# ========== GPT 호출 ==========
def ask_gpt(user_id, user_input, emotion=None):
    chats = load_chats(user_id)
    messages = []
    for chat in chats:
        messages.append({"role": "user", "content": chat["question"]})
        messages.append({"role": "assistant", "content": chat["answer"]})

    if emotion:
        prompt = f"사용자 입력: {user_input}\n분석된 감정: {emotion}\n감정을 고려해 공감형 답변을 해주세요."
    else:
        prompt = user_input
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content

# ========== 감정 분석 ==========
def analyze_emotion(user_input):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "다음 문장의 감정을 기쁨 슬픔 당황 분노 상처 중 하나의 단어로만 출력해."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content.strip()

# ========== DB 저장 ==========
def save_chat_and_emotion(user_id, question, answer):
    conn = get_db_connection()
    cursor = conn.cursor()
    chat_date = datetime.now().date()
    chat_time = datetime.now().time()

    # UserChat 저장
    cursor.execute("""
        INSERT INTO UserChat (user_id, chat_date, chat_time, question, answer)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, chat_date, chat_time, question, answer))
    chat_id = cursor.lastrowid   # 방금 저장된 chat_id 가져오기

    # 감정 분석
    dominant_emotion = analyze_emotion(question)

    # EmotionLog 저장
    cursor.execute("""
        INSERT INTO EmotionLog (chat_id, user_id, dominant_emotion)
        VALUES (%s, %s, %s)
    """, (chat_id, user_id, dominant_emotion))

    conn.commit()
    cursor.close()
    conn.close()
    return dominant_emotion

# ========== DB 불러오기 ==========
def load_chats(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT chat_id, question, answer, chat_date, chat_time
        FROM UserChat
        WHERE user_id = %s
        ORDER BY chat_id ASC
    """, (user_id,))
    chats = cursor.fetchall()
    cursor.close()
    conn.close()
    return chats

# ========== 로그인 검증 ==========
def get_user_info(login_id, password):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, login_id, role FROM Member WHERE login_id=%s AND password=%s",
        (login_id, password)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result   # {'user_id': 1, 'login_id':'abc', 'role':'user'}

# ========== 회원가입 ==========
def register_user(login_id, name, gender, age, address, password):
    conn = get_db_connection()
    cursor = conn.cursor()
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

# ========== dominant emotion 집계 ==========
def get_dominant_emotion(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT dominant_emotion, COUNT(*) as cnt
        FROM EmotionLog
        WHERE user_id = %s
        GROUP BY dominant_emotion
        ORDER BY cnt DESC
        LIMIT 1
    """, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None

# 드라마 추천
def recommend_drama_by_emotion(emotion):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT drama_id, title, description, poster_url, rating
        FROM Drama
        WHERE emotion_genre = %s
        ORDER BY RAND()
        LIMIT 3
    """, (emotion,))
    dramas = cursor.fetchall()
    cursor.close()
    conn.close()
    return dramas

# 영화 추천
def recommend_movie_by_emotion(emotion):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT movie_id, title, description, poster_url, rating
        FROM Movie
        WHERE emotion_genre = %s
        ORDER BY RAND()
        LIMIT 3
    """, (emotion,))
    movies = cursor.fetchall()
    cursor.close()
    conn.close()
    return movies

# 음악 추천
def recommend_music_by_emotion(emotion):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT music_id, title, artist, album_cover
        FROM Music
        WHERE emotion_genre = %s
        LIMIT 3
    """, (emotion,))
    musics = cursor.fetchall()
    cursor.close()
    conn.close()
    return musics


# ========== 추천 저장 ==========
def save_recommendation(user_id, emotion, content_type, content_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO UserRecommendation (user_id, emotion, content_type, content_id)
        VALUES (%s, %s, %s, %s)
    """, (user_id, emotion, content_type, content_id))
    conn.commit()
    cursor.close()
    conn.close()

# ========== 추천 출력 (3종) ==========
def show_recommendations_all(emotion):
    st.subheader(f"🎭 {emotion} 감정 기반 추천 콘텐츠")

    tabs = st.tabs(["🎬 영화", "📺 드라마", "🎵 음악" ])

    # 🎵 음악 탭
    with tabs[2]:
        musics = recommend_music_by_emotion(emotion)
        if musics:
            cols = st.columns(3)
            for idx, mu in enumerate(musics):
                with cols[idx % 3]:
                    if mu.get("album_cover"):
                        st.image(mu["album_cover"], width=120)
                    st.markdown(f"**{mu['title']}**")
                    st.caption(f"가수: {mu['artist']}")
                    save_recommendation(st.session_state["user_id"], emotion, "music", mu["music_id"])
        else:
            st.warning("해당 감정에 맞는 음악이 없습니다 😢")

    # 📺 드라마 탭
    with tabs[1]:
        dramas = recommend_drama_by_emotion(emotion)
        if dramas:
            cols = st.columns(3)
            for idx, d in enumerate(dramas):
                with cols[idx % 3]:
                    if d.get("poster_url"):
                        st.image(d["poster_url"], width=120)
                    st.markdown(f"**{d['title']}** ⭐ {d.get('rating','')}")

                    # ✅ 줄거리 자르기
                    desc = d.get("description", "")
                    if desc and len(desc) > 100:
                        desc = desc[:100] + "..."
                    st.caption(desc)

                    save_recommendation(st.session_state["user_id"], emotion, "drama", d["drama_id"])
        else:
            st.warning("해당 감정에 맞는 드라마가 없습니다 😢")

    # 🎬 영화 탭
    with tabs[0]:
        movies = recommend_movie_by_emotion(emotion)
        if movies:
            cols = st.columns(3)
            for idx, m in enumerate(movies):
                with cols[idx % 3]:
                    if m.get("poster_url"):
                        st.image(m["poster_url"], width=120)
                    st.markdown(f"**{m['title']}** ⭐ {m.get('rating','')}")

                    # ✅ 줄거리 자르기
                    desc = m.get("description", "")
                    if desc and len(desc) > 100:
                        desc = desc[:100] + "..."
                    st.caption(desc)

                    save_recommendation(st.session_state["user_id"], emotion, "movie", m["movie_id"])
        else:
            st.warning("해당 감정에 맞는 영화가 없습니다 😢")

# ======================================= Dash Board ==========================================
# 세션 상태 초기화 -------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None  
    
def my_dashboard():
    user_id = st.session_state["user_id"]
    st.subheader(f"{st.session_state.username}님의 심리 대시보드 💉")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ 날짜별 감정 로그 불러오기 (dominant_emotion만 활용)
    cursor.execute("""
        SELECT uc.chat_date, el.dominant_emotion, COUNT(*) as cnt
        FROM EmotionLog el
        JOIN UserChat uc ON el.chat_id = uc.chat_id
        WHERE el.user_id=%s
        GROUP BY uc.chat_date, el.dominant_emotion
        ORDER BY uc.chat_date ASC
    """, (user_id,))
    logs = cursor.fetchall()
    df_psych = pd.DataFrame(logs)

    # 2️⃣ 우울 점수 계산 (불안40% + 상처30% + 슬픔30%)
    today_depression, max_depression = None, None
    if not df_psych.empty:
        pivot = df_psych.pivot(index="chat_date", columns="dominant_emotion", values="cnt").fillna(0)
        # 가중치 적용
        weights = {"불안": 0.4, "상처": 0.3, "슬픔": 0.3}
        pivot["depression_score"] = (
            pivot.get("불안", 0)*weights["불안"] +
            pivot.get("상처", 0)*weights["상처"] +
            pivot.get("슬픔", 0)*weights["슬픔"]
        )
        today_depression = round(pivot.iloc[-1]["depression_score"], 1)  # 가장 최근 날짜
        max_depression = round(pivot["depression_score"].max(), 1)

    # 3️⃣ KPI 카드
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("오늘 우울 점수", f"😔 {today_depression if today_depression else '-'}")
    with col2:
        st.metric("최근 최고 우울 점수", f"📈 {max_depression if max_depression else '-'}")
    with col3:
        st.metric("총 기록된 일수", f"{df_psych['chat_date'].nunique() if not df_psych.empty else 0}일")

    st.divider()

    # 4️⃣ 감정 상태 분석 (Radar Chart: dominant_emotion 비율)
    if not df_psych.empty:
        last_day = df_psych["chat_date"].max()
        daily = df_psych[df_psych["chat_date"] == last_day]
        emo_counts = daily.set_index("dominant_emotion")["cnt"].to_dict()

        emotions = ["기쁨","슬픔","분노","상처","당황","불안"]
        values = [emo_counts.get(e, 0) for e in emotions]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=values+[values[0]], theta=emotions+[emotions[0]], fill="toself"))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values)+1])),
                                showlegend=False, height=300)
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("아직 감정 데이터가 없습니다.")

    # 5️⃣ 우울 점수 추이 (Line Chart)
    if not df_psych.empty:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=pivot.index, y=pivot["depression_score"],
                                      mode="lines+markers", line=dict(shape="spline")))
        fig_line.update_layout(yaxis_range=[0, pivot["depression_score"].max()+1], height=300)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("아직 우울 점수 데이터 없음")

    cursor.close()
    conn.close()

def logout():
    # 세션 상태 초기화
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None
    
    st.success("👋 성공적으로 로그아웃되었습니다.")
    st.rerun()  # 🔥 rerun 해서 로그인 화면으로 돌아가기

def truncate_text(text, max_len=60):
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len] + "..."

def render_card(rec, content_type):
    if rec.get("cover"):
        st.image(rec["cover"], width=120)

    if content_type == "music":
        st.markdown(f"🎵 **{rec['title']} - {rec['artist']}**")
    else:
        st.markdown(f"**{rec['title']}**")

    # ✅ 줄거리 고정 길이 + 카드 스타일
    st.markdown(
        f"<div style='min-height:60px; max-height:60px; overflow:hidden; font-size:13px; color:gray;'>"
        f"{truncate_text(rec.get('description',''), 60)}  "
        f"(감정: {rec['emotion']})</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

def content():
    st.subheader("🎬 내가 추천받은 콘텐츠 기록")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.emotion, r.content_type, r.created_at,
               COALESCE(m.title, d.title, mu.title) as title,
               COALESCE(m.poster_url, d.poster_url, mu.album_cover) as cover,
               COALESCE(m.description, d.description, '') as description,
               mu.artist
        FROM UserRecommendation r
        LEFT JOIN Movie m ON r.content_type='movie' AND r.content_id=m.movie_id
        LEFT JOIN Drama d ON r.content_type='drama' AND r.content_id=d.drama_id
        LEFT JOIN Music mu ON r.content_type='music' AND r.content_id=mu.music_id
        WHERE r.user_id=%s
        ORDER BY r.created_at DESC
        LIMIT 30
    """, (st.session_state["user_id"],))
    recs = cursor.fetchall()
    cursor.close()
    conn.close()

    if not recs:
        st.info("아직 추천받은 콘텐츠 기록이 없습니다.")
        return

    # 👉 탭 나누기
    tab_movie, tab_drama, tab_music = st.tabs(["🎬 영화", "📺 드라마", "🎵 음악" ])

    # 🎵 음악 탭
    with tab_music:
        musics = [r for r in recs if r["content_type"] == "music"]
        if musics:
            cols = st.columns(3)
            for idx, rec in enumerate(musics):
                with cols[idx % 3]:
                    if rec["cover"]:
                        st.image(rec["cover"], width=120)
                    st.markdown(f"**{rec['title']} - {rec['artist']}**")
                    st.caption(f"감정: {rec['emotion']}")
        else:
            st.warning("추천받은 음악 기록이 없습니다.")

    # 📺 드라마 탭
    with tab_drama:
        dramas = [r for r in recs if r["content_type"] == "drama"]
        if dramas:
            cols = st.columns(3)
            for idx, rec in enumerate(dramas):
                with cols[idx % 3]:
                    render_card(rec, "drama")   # 카드 함수 사용
        else:
            st.warning("추천받은 드라마 기록이 없습니다.")


    # 🎬 영화 탭
    with tab_movie:
        movies = [r for r in recs if r["content_type"] == "movie"]
        if movies:
            cols = st.columns(3)
            for idx, rec in enumerate(movies):
                with cols[idx % 3]:
                    render_card(rec, "movie")   # 카드 함수 사용
        else:
            st.warning("추천받은 영화 기록이 없습니다.")

def hospital():
    st.title("🏥심린이 병원추천")

    # 기본 위치: 서울 시청
    default_lat, default_lon = 37.5665, 126.9780

    # 사용자 위치 입력
    user_location = st.text_input("📍 현재 위치를 입력하세요 (예: 서울시 강남구 역삼동)")

    # 지도 초기화
    m = folium.Map(location=[default_lat, default_lon], zoom_start=13)

    # 사용자 위치 입력 시 처리
    if user_location:
        geolocator = Nominatim(user_agent="myGeocoder")
        location = geolocator.geocode(user_location)

        if location:
            lat, lon = location.latitude, location.longitude

            # 내 위치 마커
            folium.Marker(
                [lat, lon], tooltip="내 위치", icon=folium.Icon(color="blue")
            ).add_to(m)

            # 병원 예시 마커 (임의 좌표, 실제 데이터로 바꿀 수 있음)
            folium.Marker(
                [lat + 0.001, lon + 0.001],
                tooltip="힐링 정신건강의학과의원",
                icon=folium.Icon(color="green")
            ).add_to(m)

            folium.Marker(
                [lat - 0.001, lon - 0.001],
                tooltip="마음숲 클리닉",
                icon=folium.Icon(color="green")
            ).add_to(m)

            # 중심을 사용자 위치로 이동
            m.location = [lat, lon]
            m.zoom_start = 15

        else:
            st.error("❌ 위치를 찾을 수 없습니다. 다시 입력해 주세요.")
    else:
        st.info("📌 위치를 입력하면 주변 병원이 지도에 표시됩니다.")

        # 지도 표시
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        st_folium(m, width=700, height=450)
    with col2:
        st.text("거리기반")
    with col3:
        st.text("평점기반")
        
def user_dashboard():
    # 사이드바 메뉴
    with st.sidebar:
        selected = option_menu(
            "츄러스미 메뉴",
            ["나의 대시보드", "심린이랑 대화하기", "심린이 추천병원", "심린이 추천 콘텐츠", "로그아웃"],
            icons=['bar-chart', 'chat-dots', 'hospital', 'camera-video', 'box-arrow-right'],
            default_index=0,
            styles={
                "container": {"padding": "5px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#b3d9ff"},
            }
        )

    if selected == '나의 대시보드':
        my_dashboard()

     # === 대화 불러오기 ===
    elif selected == '심린이랑 대화하기':       
        chats = load_chats(st.session_state["user_id"])
        for chat in chats:
            render_bubble("user", chat["question"], USER_AVATAR_PATH)
            render_bubble("bot",  chat["answer"],   GPT_AVATAR_PATH)

        # 입력창
        user_input = st.chat_input("메시지를 입력하세요…")
        if user_input:
            # 1) DB 저장 + GPT 호출
            answer = ask_gpt(st.session_state["user_id"], user_input)
            detected_emotion = save_chat_and_emotion(st.session_state["user_id"], user_input, answer)

            # 2) 화면에 바로 말풍선으로 렌더
            render_bubble("user", user_input, USER_AVATAR_PATH)
            render_bubble("bot", answer, GPT_AVATAR_PATH)

            st.rerun()

        if user_input:
            # 1) DB 저장 + GPT 호출
            answer = ask_gpt(st.session_state["user_id"], user_input)
            detected_emotion = save_chat_and_emotion(st.session_state["user_id"], user_input, answer)

            # 2) 세션에 추가
            with st.chat_message("user", avatar=USER_AVATAR_PATH):
                st.markdown(user_input)
            with st.chat_message("assistant", avatar=GPT_AVATAR_PATH):
                st.markdown(answer)

            st.rerun()

        # === 추천/세션 종료 버튼 ===
        col1, col2 = st.columns(2)
        with col1:
            if st.button("추천 받기"):
                if chats:
                    last_message = chats[-1]["question"]
                    detected_emotion = analyze_emotion(last_message)
                    st.info(f"최근 감정 분석 결과: **{detected_emotion}**")
                    show_recommendations_all(detected_emotion)

        with col2:
            if st.button("세션 종료"):
                dominant_emotion = get_dominant_emotion(st.session_state["user_id"])
                if dominant_emotion:
                    st.success(f"세션 전체 감정 요약 → **{dominant_emotion}**")
                    show_recommendations_all(dominant_emotion)
                else:
                    st.warning("대화 기록이 없어 세션 요약을 할 수 없습니다.")


    elif selected == '심린이 추천병원':
        hospital()

    elif selected == '심린이 추천 콘텐츠':
        content()

    else:
        logout()

# ==== 관리자 =====
def admin_dashboard():
    st.title("👮‍♂️ 츄러스미 관리자 Dash Board")


# ========== Streamlit UI ==========
st.title("💬 심리 상담 챗봇")

# 페이지 상태 초기화
if "page" not in st.session_state:
    st.session_state["page"] = "login"

# 🟢 로그인 페이지
if st.session_state["page"] == "login" and not st.session_state.get("user_id"):
    st.subheader("🔑 로그인")
    login_id = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
        user_info = get_user_info(login_id, password)
        if user_info:
            st.session_state["user_id"] = user_info["user_id"]
            st.session_state["username"] = user_info["login_id"]   # ✅ username 저장
            st.session_state["role"] = user_info["role"]
            st.success(f"로그인 성공! {st.session_state['username']}님 ({user_info['role']})")
            st.rerun()
        else:
            st.error("아이디/비밀번호가 잘못되었습니다.")

    if st.button("👉 회원가입"):
        st.session_state["page"] = "register"
        st.rerun()

# 🟢 회원가입 페이지
elif st.session_state["page"] == "register":
    st.subheader("📝 회원가입")

    new_id = st.text_input("아이디")
    new_name = st.text_input("이름")
    new_gender = st.selectbox("성별", ["M", "F", "Other"])
    new_age = st.number_input("나이", min_value=0, max_value=120, step=1)
    new_address = st.text_input("주소")
    new_pw = st.text_input("비밀번호", type="password")

    if st.button("가입하기"):
        success, msg = register_user(new_id, new_name, new_gender, new_age, new_address, new_pw)
        if success:
            st.success(msg)
            st.session_state["page"] = "login"
        else:
            st.error(msg)

    if st.button("⬅ 돌아가기"):
        st.session_state["page"] = "login"
        st.rerun()

# 🟢 유저 대시보드
elif st.session_state.get("role") == "user":
    user_dashboard()

# 🟢 관리자 대시보드
elif st.session_state.get("role") == "admin":
    admin_dashboard()

# 🟡 예외 처리 (빈 화면 방지)
else:
    st.warning("⚠️ 화면을 불러올 수 없습니다. 다시 로그인 해주세요.")