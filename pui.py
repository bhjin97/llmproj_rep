# 실행 흐름 -----------------------------
if st.session_state.logged_in:
    if st.session_state.role == "admin":
        admin_dashboard()
    elif st.session_state.role == "user":
        user_dashboard()
    else:
        unuser_dashboard()
else:
    login()