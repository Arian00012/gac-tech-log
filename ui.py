import streamlit as st

_CSS = (
    "<style>"
    ".stats{display:flex;flex-wrap:wrap;gap:.5rem;margin:.25rem 0 1rem}"
    ".stat{flex:1 1 7rem;background:#F3F5F8;border-radius:.5rem;padding:.5rem .75rem}"
    ".stat-n{font-size:1.7rem;font-weight:600;line-height:1.1;color:#1B2430}"
    ".stat-l{font-size:.8rem;color:#5B6675}"
    "</style>"
)


def stat_cards(items: list[tuple[str, int]]) -> None:
    """Contadores que se acomodan en una o varias filas según el ancho de pantalla."""
    cards = "".join(
        f'<div class="stat"><div class="stat-n">{n}</div>'
        f'<div class="stat-l">{label}</div></div>'
        for label, n in items
    )
    st.markdown(f'{_CSS}<div class="stats">{cards}</div>', unsafe_allow_html=True)