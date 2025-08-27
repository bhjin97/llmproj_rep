import streamlit as st
import mysql.connector
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
import os

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
    # DB에서 해당 유저의 모든 대화 불러오기
    chats = load_chats(user_id)

    messages = []
    for chat in chats:
        messages.append({"role": "user", "content": chat["question"]})
        messages.append({"role": "assistant", "content": chat["answer"]})

    # 이번 입력 추가
    if emotion:
        prompt = f"사용자 입력: {user_input}\n분석된 감정: {emotion}\n감정을 고려해 공감형 답변을 해주세요."
    else:
        prompt = user_input
    messages.append({"role": "user", "content": prompt})

    # GPT 호출
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content

# ========== DB 저장 ==========
def save_chat(user_id, question, answer):
    conn = get_db_connection()
    cursor = conn.cursor()

    chat_date = datetime.now().date()
    chat_time = datetime.now().time()

    cursor.execute("""
        INSERT INTO UserChat (user_id, chat_date, chat_time, question, answer)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, chat_date, chat_time, question, answer))

    conn.commit()
    cursor.close()
    conn.close()

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
def get_user_id(login_id, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Member WHERE login_id=%s AND password=%s", (login_id, password))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None

# ========== 감정 분석 함수 ==========
def analyze_emotion(user_input):
    # GPT로 간단한 감정 태깅
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "다음 문장의 감정을 우울, 불안, 기쁨, 분노, 평온 중 하나로 분류해줘."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content.strip()

# ========== 세션 전체 감정 요약 ==========
def get_dominant_emotion(user_id):
    chats = load_chats(user_id)
    emotions = []
    for chat in chats:
        emo = analyze_emotion(chat["question"])
        emotions.append(emo)

    # 가장 많이 나온 감정 선택
    if emotions:
        return max(set(emotions), key=emotions.count)
    return None

# ========== 드라마 추천 ==========
def recommend_drama_by_emotion(emotion):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT title, description, poster_url, rating
        FROM Drama
        WHERE emotion_genre = %s
        ORDER BY rating DESC
        LIMIT 3
    """, (emotion,))
    dramas = cursor.fetchall()
    cursor.close()
    conn.close()
    return dramas


# ========== Streamlit UI ==========
st.title("💬 심리 상담 챗봇")

# 로그인 상태 확인
if "user_id" not in st.session_state:
    st.subheader("🔑 로그인")
    login_id = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        user_id = get_user_id(login_id, password)
        if user_id:
            st.session_state["user_id"] = user_id
            st.success(f"로그인 성공! user_id={user_id}")
            st.rerun()
        else:
            st.error("아이디/비밀번호가 잘못되었습니다.")
else:
    user_id = st.session_state["user_id"]   # ✅ 세션에서 user_id 사용
    st.success(f"환영합니다! user_id={user_id}")

    # 사용자 입력창
    user_input = st.text_input("메시지를 입력하세요:")
    if st.button("보내기") and user_input:
        # GPT 응답
        answer = ask_gpt(user_id, user_input)

        # DB 저장
        save_chat(user_id, user_input, answer)

        # 입력창 초기화
        st.session_state["last_input"] = user_input
        st.session_state["last_answer"] = answer

    # 대화 내역 불러오기
    chats = load_chats(user_id)
    
    # ✅ 추천 버튼
    if st.button("추천 받기"):
        chats = load_chats(st.session_state["user_id"])
        if chats:
            last_message = chats[-1]["question"]
            detected_emotion = analyze_emotion(last_message)
            st.info(f"최근 감정 분석 결과: **{detected_emotion}**")

            recs = recommend_drama_by_emotion(detected_emotion)
            for d in recs:
                st.image(d["poster_url"], width=150)
                st.markdown(f"**{d['title']}** ⭐ {d['rating']}")
                st.caption(d["description"])
                st.markdown("---")

    # ✅ 세션 종료 시 dominant emotion 분석
    if st.button("세션 종료"):
        dominant_emotion = get_dominant_emotion(st.session_state["user_id"])
        if dominant_emotion:
            st.success(f"세션 전체 감정 요약 → **{dominant_emotion}**")
            recs = recommend_drama_by_emotion(dominant_emotion)
            for d in recs:
                st.image(d["poster_url"], width=150)
                st.markdown(f"**{d['title']}** ⭐ {d['rating']}")
                st.caption(d["description"])
                st.markdown("---")
        else:
            st.warning("대화 기록이 없어 세션 요약을 할 수 없습니다.")

    # 출력
    for chat in chats:
        st.markdown(f"👤 **User:** {chat['question']}")
        st.markdown(f"🤖 **AI:** {chat['answer']}")
        st.markdown("---")
