# Small reusable interface pieces (brand block, avatar, status chips).
# Names and other user text are HTML-escaped before they reach unsafe HTML.

import html
from pathlib import Path

import streamlit as st

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "style.css"

STATUS_CHIPS = {
    "pending": ("Pending", "warn"),
    "confirmed": ("Confirmed", "ok"),
    "declined": ("Declined", "bad"),
    "cancelled": ("Cancelled", "bad"),
}


def inject_css():
    if CSS_PATH.exists():
        st.markdown(
            f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def initials(name):
    parts = (name or "").split()
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def chip(text, kind="neutral"):
    return f'<span class="tg-chip tg-{kind}">{html.escape(text)}</span>'


def brand(big=False):
    st.markdown(
        f'<div class="tg-brand{" tg-brand-big" if big else ""}">'
        '<div class="tg-logo">T</div><div>'
        '<div class="tg-brand-name">TUGMA</div>'
        '<div class="tg-brand-sub">Peer tutoring · DLSU-D</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def person_header(name, subtitle="", badge=None, kind="ok"):
    st.markdown(
        '<div class="tg-person">'
        f'<div class="tg-avatar">{html.escape(initials(name))}</div>'
        '<div class="tg-person-text">'
        f'<div class="tg-name">{html.escape(name)}</div>'
        f'<div class="tg-sub">{html.escape(subtitle)}</div></div>'
        f'{chip(badge, kind) if badge else ""}</div>',
        unsafe_allow_html=True,
    )
