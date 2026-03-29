"""
app.py — Tech0 Search v1.0（ミニマルUI版）
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

# ── CSS（余白のみ微調整） ─────────────────────────────────────
st.markdown("""
<style>
.block-container { padding-top: 2rem; max-width: 760px; }
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
st.title("🔍 Tech0 Search")
st.caption(f"PROJECT ZERO — 社内ナレッジ検索エンジン　{len(pages)} 件登録済み")

with st.sidebar:
    st.header("DB の状態")
    st.metric("登録ページ数", f"{len(pages)} 件")
    if st.button("🔄 インデックスを更新"):
        st.cache_resource.clear()
        st.rerun()


# ── タブ ─────────────────────────────────────────────────────
tab_search, tab_crawl, tab_list = st.tabs(["🔍 検索", "🤖 クローラー", "📋 一覧"])


# ── 検索タブ ─────────────────────────────────────────────────
with tab_search:
    col_q, col_n = st.columns([4, 1])
    with col_q:
        query = st.text_input(
            "キーワードを入力",
            placeholder="例: DX, IoT, 製造業",
            label_visibility="collapsed"
        )
    with col_n:
        top_n = st.selectbox("表示件数", [10, 20, 50], label_visibility="collapsed")

    if query:
        results = engine.search(query, top_n=top_n)
        log_search(query, len(results))

        st.caption(f"**{len(results)} 件**（TF-IDFスコア順）")
        st.divider()

        if results:
            for i, page in enumerate(results, 1):
                medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"#{i}"

                col_rank, col_body, col_score = st.columns([0.5, 5, 1])

                with col_rank:
                    st.markdown(f"### {medal}")

                with col_body:
                    st.markdown(f"**{page['title']}**")
                    st.markdown(f"🔗 [{page['url']}]({page['url']})")

                    desc = page.get("description", "") or ""
                    if desc:
                        st.caption(f"{desc[:200]}{'…' if len(desc) > 200 else ''}")

                    kw = page.get("keywords", "") or ""
                    if kw:
                        tags = " ".join(
                            f"`{k.strip()}`"
                            for k in kw.split(",") if k.strip()
                        )
                        st.markdown(f"🏷️ {tags}")

                    c1, c2, c3, c4 = st.columns(4)
                    c1.caption(f"👤 {page.get('author','—') or '—'}")
                    c2.caption(f"📊 {page.get('word_count', 0)} 語")
                    c3.caption(f"📁 {page.get('category','未分類') or '未分類'}")
                    c4.caption(f"📅 {(page.get('crawled_at','') or '')[:10]}")

                with col_score:
                    st.metric(
                        "スコア",
                        page["relevance_score"],
                        delta=f"{page['base_score']}"
                    )

                st.divider()
        else:
            st.info("該当するページが見つかりませんでした")


# ── クローラータブ ────────────────────────────────────────────
if "crawl_results" not in st.session_state:
    st.session_state.crawl_results = []

with tab_crawl:
    st.subheader("🤖 自動クローラー")
    st.caption("URLを改行またはスペース区切りで入力してクロールします")

    crawl_url_input = st.text_area(
        "クロール対象URL",
        placeholder="https://example.com\nhttps://...",
        height=150,
        label_visibility="collapsed"
    )

    if st.button("🤖 クロール実行", type="primary"):
        if crawl_url_input:
            raw = re.split(r'[\s]+', crawl_url_input.strip())
            urls = [u for u in raw if u.startswith(("http://", "https://"))]

            if not urls:
                st.error("有効なURLが見つかりませんでした")
            else:
                st.write(f"🔗 {len(urls)} 件のURLを処理します")
                st.session_state.crawl_results = []

                for url in urls:
                    with st.spinner(f"クロール中: {url}"):
                        result = crawl_url(url)

                    if result and result.get("crawl_status") == "success":
                        st.success(f"✅ 成功: {url}")
                        col1, col2 = st.columns(2)
                        title = result.get("title", "")
                        col1.metric("📄 タイトル", (title[:30] + "…") if len(title) > 30 else title)
                        col2.metric("📊 文字数", f"{result.get('word_count', 0)} 語")
                        st.session_state.crawl_results.append(result)
                    else:
                        st.error(f"❌ 失敗: {url}")

    if st.session_state.crawl_results:
        n = len(st.session_state.crawl_results)
        st.info(f"{n} 件のクロール結果を登録できます")

        if st.button("💾 全てインデックスに登録"):
            progress_text = st.empty()
            progress_bar = st.progress(0)

            for i, r in enumerate(st.session_state.crawl_results, 1):
                progress_text.write(f"📥 {i} / {n} 件登録中...")
                insert_page(r)
                progress_bar.progress(i / n)

            progress_text.write(f"✅ {n} / {n} 件 登録完了！")
            st.success(f"{n} 件 登録完了！")
            st.session_state.crawl_results = []
            st.cache_resource.clear()
            st.rerun()


# ── 一覧タブ ─────────────────────────────────────────────────
with tab_list:
    st.subheader(f"📋 登録済みページ一覧（{len(pages)} 件）")

    if not pages:
        st.info("登録されているページがありません。クローラータブからページを追加してください。")
    else:
        for page in pages:
            with st.expander(f"📄 {page['title']}"):
                st.markdown(f"**URL:** {page['url']}")
                st.markdown(f"**説明:** {page.get('description','（なし）') or '（なし）'}")
                c1, c2, c3 = st.columns(3)
                c1.caption(f"語数: {page.get('word_count', 0)}")
                c2.caption(f"作成者: {page.get('author','不明') or '不明'}")
                c3.caption(f"カテゴリ: {page.get('category','未分類') or '未分類'}")

st.divider()
st.caption("© 2025 PROJECT ZERO — Tech0 Search v1.0 | Powered by TF-IDF")
