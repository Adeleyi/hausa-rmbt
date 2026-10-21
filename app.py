"""The web demo: translate English <-> Hausa in the browser.

On your own computer:   streamlit run app.py
Online:                 deployed from GitHub with Streamlit Community Cloud (see docs/deploy_demo.md)

It uses exactly the same code as try_sentence.py; it only adds a web page around it.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))   # the system's code is in src/

import english_analysis       # noqa: E402  (imported after the line above, on purpose)
import hausa_analysis         # noqa: E402
import transfer_en_ha         # noqa: E402
import transfer_ha_en         # noqa: E402


@st.cache_resource
def warm_up():
    """Read the lexicon once, when the app starts, so the first translation is quick."""
    transfer_en_ha.translate("The boy laughed.")
    transfer_ha_en.translate("Yaron ya yi dariya.")


st.set_page_config(page_title="English ↔ Hausa RBMT", page_icon="🔤")
st.title("English ↔ Hausa translator")
st.write("A rule-based Hausa translation system.")
warm_up()

with st.form("translate"):
    direction = st.radio("Direction", ["English → Hausa", "Hausa → English"], horizontal=True)
    sentence = st.text_area("Type a sentence", height=100)
    show_rules = st.checkbox("Show the rules used")
    show_analysis = st.checkbox("Show the analysis (stage 1)")
    pressed = st.form_submit_button("Translate", type="primary")

if pressed and sentence.strip():
    try:
        if direction == "English → Hausa":
            t = transfer_en_ha.translate(sentence.strip())
            output, describe = t.hausa, english_analysis.describe
        else:
            t = transfer_ha_en.translate(sentence.strip())
            output, describe = t.english, hausa_analysis.describe
    except Exception as err:          # never crash in front of an audience
        st.error(f"Sorry, the system could not translate this sentence ({err}).")
    else:
        st.subheader(output)
        if t.missing:
            st.caption("Words in [brackets] are not in the lexicon yet: "
                       + ", ".join(word for _, word in t.missing))
        if show_rules:
            st.markdown("**Rules used**\n\n" + "\n".join(f"- {rule}" for rule in t.rules))
        if show_analysis:
            st.code(describe(t.analysis), language=None)

st.divider()
st.caption("Source code: https://github.com/Adeleyi/hausa-rmbt")