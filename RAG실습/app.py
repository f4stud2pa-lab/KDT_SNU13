"""시연용 웹 UI.  실행: streamlit run app.py"""
import streamlit as st

from kiosk import create_agent

st.set_page_config(page_title="카페 소담 키오스크", page_icon="☕", layout="wide")

if "agent" not in st.session_state:
    st.session_state.agent = create_agent()
agent = st.session_state.agent

chat_col, side_col = st.columns([2, 1])

with side_col:
    st.subheader("🛒 장바구니")
    st.text(agent.cart.as_text())
    if agent.cart.completed_order:
        o = agent.cart.completed_order
        st.success(f"주문번호 {o['order_number']} · {o['total_price']:,}원 · {o['dine_option']}")
    if st.button("처음부터 다시"):
        agent.reset()
        st.rerun()
    show_debug = st.toggle("RAG 내부 동작 보기", value=True)
    if show_debug and agent.last_trace.analysis:
        t = agent.last_trace
        st.caption("질의 분석")
        st.json(t.analysis)
        st.caption("검색된 문서 (id, score)")
        st.write(t.retrieved)
        st.caption("도구 호출")
        st.write(t.tool_calls or "-")

with chat_col:
    st.title("☕ 카페 소담 AI 키오스크")
    for m in agent.history:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    if prompt := st.chat_input("주문하실 메뉴나 궁금한 점을 입력하세요"):
        with st.spinner("생각 중..."):
            agent.chat(prompt)
        st.rerun()
