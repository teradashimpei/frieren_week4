"""
app.py — Tech0 Search v1.0（1800更新版）
Streamlit コンポーネントのみ使用。機能はすべて維持。
"""

import re
import streamlit as st
from database import init_db, get_all_pages, insert_page, log_search
from ranking import get_engine, rebuild_index
from crawler import crawl_url

init_db()

st.set_page_config(
    page_title="Tech0 Search",
    page_icon="🔍",
    layout="centered"
)

st.markdown("""
<style>
/* ── ベース ── */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 720px;
}

/* ── タイトル ── */
h1 { font-size: 1.4rem !important; font-weight: 600 !important; margin-bottom: 0 !important; }

/* ── タブ ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #e0e0e0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.82rem;
    font-weight: 500;
    color: #999;
    padding: 0.5rem 1rem;
    border: none;
    background: transparent;
    letter-spacing: 0.03em;
}
.stTabs [aria-selected="true"] {
    color: #111 !important;
    border-bottom: 2px solid #111 !important;
    background: transparent !important;
}

/* ── ボタン ── */
.stButton > button[kind="primary"] {
    background-color: #111 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 4px !important;
    font-size: 0.83rem !important;
    padding: 0.4rem 1.1rem !important;
    font-weight: 500 !important;
}
.stButton > button[kind="secondary"],
.stButton > button:not([kind]) {
    background-color: transparent !important;
    color: #111 !important;
    border: 1px solid #ddd !important;
    border-radius: 4px !important;
    font-size: 0.83rem !important;
    padding: 0.4rem 1.1rem !important;
}

/* ── divider ── */
hr { border: none; border-top: 1px solid #f0f0f0 !important; margin: 0.6rem 0 !important; }

/* ── metric を非表示にせず小さく ── */
[data-testid="stMetric"] {
    background: transparent !important;
    padding: 0 !important;
}
[data-testid="stMetricLabel"] { font-size: 0.7rem !important; color: #bbb !important; }
[data-testid="stMetricValue"] { font-size: 1rem !important; font-weight: 600 !important; color: #111 !important; }
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] { font-size: 0.72rem !important; color: #bbb !important; }

/* ── テキスト入力・セレクトボックス ── */
.stTextInput input {
    border: none !important;
    border-bottom: 1px solid #ccc !important;
    border-radius: 0 !important;
    font-size: 1rem !important;
    padding: 0.4rem 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}
.stTextInput input:focus {
    border-bottom: 1.5px solid #111 !important;
    box-shadow: none !important;
}

/* ── selectbox ── */
[data-baseweb="select"] > div {
    border: none !important;
    border-bottom: 1px solid #ccc !important;
    border-radius: 0 !important;
    background: transparent !important;
    font-size: 0.83rem !important;
}

/* ── expander ── */
.streamlit-expanderHeader {
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #333 !important;
}

/* ── info / success / error ── */
[data-testid="stAlert"] {
    font-size: 0.83rem !important;
    padding: 0.5rem 0.9rem !important;
    border-radius: 4px !important;
}

/* ── sidebar を非表示 ── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ── インデックス構築 ─────────────────────────────────────────
@st.cache_resource
def load_and_index():
    pages = get_all_pages()
    if pages:
        rebuild_index(pages)
    return pages

pages = load_and_index()
engine = get_engine()


# ── ヘッダー ─────────────────────────────────────────────────
col_title, col_meta = st.columns([3, 1])
with col_title:
    st.title("🔍 Tech0 Search")
with col_meta:
    st.caption(f"**{len(pages)}** 件登録済み")
    if st.button("更新", key="refresh"):
        st.cache_resource.clear()
        st.rerun()

st.divider()


# ── タブ ─────────────────────────────────────────────────────
tab_search, tab_crawl, tab_list = st.tabs(["検索", "クローラー", "一覧"])


# ── 検索タブ ─────────────────────────────────────────────────
with tab_search:
    col_q, col_n = st.columns([4, 1])
    with col_q:
        query = st.text_input(
            "query",
            placeholder="キーワードを入力...",
            label_visibility="collapsed"
        )
    with col_n:
        top_n = st.selectbox("件数", [10, 20, 50], label_visibility="collapsed")

    if query:
        results = engine.search(query, top_n=top_n)
        log_search(query, len(results))

        st.caption(f"{len(results)} 件 — TF-IDFスコア順")
        st.divider()

        if results:
            for i, page in enumerate(results, 1):
                medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"#{i}"

                col_rank, col_body, col_score = st.columns([0.5, 5, 1.2])

                with col_rank:
                    st.caption(medal)

                with col_body:
                    st.markdown(f"**{page['title']}**")
                    st.caption(f"[{page['url']}]({page['url']})")

                    desc = page.get("description", "") or ""
                    if desc:
                        st.caption(f"{desc[:180]}{'…' if len(desc) > 180 else ''}")

                    kw = page.get("keywords", "") or ""
                    if kw:
                        tags = " ".join(
                            f"`{k.strip()}`"
                            for k in kw.split(",") if k.strip()
                        )
                        st.caption(f"🏷️ {tags}")

                    c1, c2, c3, c4 = st.columns(4)
                    c1.caption(page.get("author", "—") or "—")
                    c2.caption(f"{page.get('word_count', 0)} 語")
                    c3.caption(page.get("category", "未分類") or "未分類")
                    c4.caption((page.get("crawled_at", "") or "")[:10])

                with col_score:
                    st.metric(
                        "score",
                        page["relevance_score"],
                        delta=f"base {page['base_score']}"
                    )

                st.divider()
        else:
            st.info("該当するページが見つかりませんでした")


# ── クローラータブ ────────────────────────────────────────────
if "crawl_results" not in st.session_state:
    st.session_state.crawl_results = []

with tab_crawl:
    st.caption("URLを改行またはスペース区切りで入力")

    crawl_url_input = st.text_area(
        "URLs",
        placeholder="https://example.com\nhttps://...",
        height=140,
        label_visibility="collapsed"
    )

    if st.button("クロール実行", type="primary"):
        if crawl_url_input:
            raw = re.split(r'[\s]+', crawl_url_input.strip())
            urls = [u for u in raw if u.startswith(("http://", "https://"))]

            if not urls:
                st.error("有効なURLが見つかりませんでした")
            else:
                st.caption(f"{len(urls)} 件のURLを処理します")
                st.session_state.crawl_results = []

                for url in urls:
                    with st.spinner(f"{url}"):
                        result = crawl_url(url)

                    if result and result.get("crawl_status") == "success":
                        st.success(f"✓ {result.get('title', url)[:60]}")
                        col1, col2 = st.columns(2)
                        title = result.get("title", "")
                        col1.metric("タイトル", (title[:28] + "…") if len(title) > 28 else title)
                        col2.metric("文字数", f"{result.get('word_count', 0)} 語")
                        st.session_state.crawl_results.append(result)
                    else:
                        st.error(f"✗ {url}")

    if st.session_state.crawl_results:
        n = len(st.session_state.crawl_results)
        st.info(f"{n} 件 クロール済み — インデックスに登録できます")

        if st.button(f"インデックスに登録（{n} 件）", type="primary"):
            progress_text = st.empty()
            progress_bar = st.progress(0)

            for i, r in enumerate(st.session_state.crawl_results, 1):
                progress_text.caption(f"{i} / {n} 件登録中...")
                insert_page(r)
                progress_bar.progress(i / n)

            progress_text.caption(f"✓ {n} 件 登録完了")
            st.success(f"{n} 件 登録しました")
            st.session_state.crawl_results = []
            st.cache_resource.clear()
            st.rerun()


# ── 一覧タブ ─────────────────────────────────────────────────
with tab_list:
    st.caption(f"{len(pages)} 件登録済み")

    if not pages:
        st.info("登録されているページがありません。クローラータブからページを追加してください。")
    else:
        for page in pages:
            with st.expander(page["title"]):
                st.caption(page["url"])
                desc = page.get("description", "") or ""
                if desc:
                    st.caption(desc)
                c1, c2, c3 = st.columns(3)
                c1.caption(f"{page.get('word_count', 0)} 語")
                c2.caption(page.get("author", "—") or "—")
                c3.caption(page.get("category", "—") or "—")

st.divider()
st.caption("© 2025 PROJECT ZERO · Tech0 Search v1.0")
