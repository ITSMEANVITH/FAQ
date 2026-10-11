"""Local SQLite feedback store for Knowly answer quality ratings."""
from __future__ import annotations
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("knowly_workspace.sqlite3")


def _connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answer_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_key TEXT NOT NULL UNIQUE,
            question TEXT NOT NULL,
            answer_preview TEXT NOT NULL,
            rating TEXT NOT NULL CHECK(rating IN ('helpful', 'not_helpful')),
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    return conn


def save_feedback(answer_key: str, question: str, answer: str, rating: str, reason: str = ""):
    if rating not in {"helpful", "not_helpful"}:
        raise ValueError("Rating must be helpful or not_helpful.")
    with _connection() as conn:
        conn.execute("""
            INSERT INTO answer_feedback(answer_key, question, answer_preview, rating, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(answer_key) DO UPDATE SET
                question=excluded.question,
                answer_preview=excluded.answer_preview,
                rating=excluded.rating,
                reason=excluded.reason,
                created_at=excluded.created_at
        """, (answer_key, question[:1000], answer[:1500], rating, reason[:1000],
              datetime.now().isoformat(timespec="seconds")))


def get_feedback():
    with _connection() as conn:
        rows = conn.execute("""
            SELECT answer_key, question, answer_preview, rating, reason, created_at
            FROM answer_feedback ORDER BY created_at DESC
        """).fetchall()
    return [
        {"answer_key": r[0], "question": r[1], "answer": r[2], "rating": r[3],
         "reason": r[4], "created_at": r[5]}
        for r in rows
    ]


def delete_feedback():
    with _connection() as conn:
        conn.execute("DELETE FROM answer_feedback")


def make_answer_key(question: str, answer: str) -> str:
    """Stable identifier for an answer, independent of its position in chat history."""
    raw = f"{question.strip()}\n---\n{answer.strip()}".encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def render_answer_feedback(question: str, answer: str, key: str):
    """Render rating controls for one assistant answer."""
    import streamlit as st

    feedback_rows = get_feedback()
    current = next((item for item in feedback_rows if item["answer_key"] == key), None)
    st.caption("Was this answer useful?")
    col_yes, col_no, col_reason = st.columns([1, 1, 3])
    with col_yes:
        if st.button("👍 Helpful", key=f"feedback_yes_{key[:12]}",
                     type="primary" if current and current["rating"] == "helpful" else "secondary"):
            save_feedback(key, question, answer, "helpful", "")
            st.toast("Thanks! Feedback saved locally.")
            st.rerun()
    with col_no:
        if st.button("👎 Not helpful", key=f"feedback_no_{key[:12]}",
                     type="primary" if current and current["rating"] == "not_helpful" else "secondary"):
            st.session_state[f"feedback_reason_open_{key[:12]}"] = True
    with col_reason:
        if current:
            st.caption("Current rating: " + ("Helpful" if current["rating"] == "helpful" else "Not helpful"))
    if st.session_state.get(f"feedback_reason_open_{key[:12]}", False):
        with st.form(f"feedback_form_{key[:12]}"):
            reason = st.selectbox(
                "What went wrong?",
                ["Incorrect answer", "Missing evidence or citation", "Irrelevant answer",
                 "Incomplete answer", "Other"],
                key=f"feedback_reason_{key[:12]}",
            )
            details = st.text_area("Optional details", max_chars=1000,
                                   key=f"feedback_details_{key[:12]}")
            submitted = st.form_submit_button("Submit feedback")
            if submitted:
                full_reason = reason + (f": {details.strip()}" if details.strip() else "")
                save_feedback(key, question, answer, "not_helpful", full_reason)
                st.session_state[f"feedback_reason_open_{key[:12]}"] = False
                st.toast("Thanks! Feedback saved locally.")
                st.rerun()


def render_feedback_dashboard():
    """Render simple answer-quality metrics and recent feedback."""
    import streamlit as st
    rows = get_feedback()
    helpful = sum(1 for item in rows if item["rating"] == "helpful")
    not_helpful = sum(1 for item in rows if item["rating"] == "not_helpful")
    total = len(rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Rated answers", total)
    c2.metric("👍 Helpful", helpful)
    c3.metric("👎 Not helpful", not_helpful)
    if total:
        st.progress(helpful / total, text=f"{round(helpful / total * 100)}% of ratings are helpful")
        st.markdown("**Recent feedback**")
        for item in rows[:8]:
            label = "👍 Helpful" if item["rating"] == "helpful" else "👎 Not helpful"
            with st.expander(f"{label} · {item['question'][:75]}"):
                st.write(item["answer"])
                if item["reason"]:
                    st.write("**Reason:** " + item["reason"])
                st.caption("Saved locally: " + item["created_at"].replace("T", " "))
        if st.button("Clear feedback history", key="clear_feedback_history"):
            delete_feedback()
            st.rerun()
    else:
        st.info("No answer ratings yet. Rate an assistant response to start building feedback analytics.")
