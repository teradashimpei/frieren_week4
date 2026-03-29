"""
database.py — Tech0 Search v1.0
SQLite DB への接続・初期化・CRUD 操作を一元管理する。
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# DB ファイルのパス（data/ サブフォルダに保存する）
DB_PATH = Path("data/tech0_search.db")


def get_connection():
    """
    DB への接続を取得する。

    row_factory を設定することで、行データを辞書のように扱える。
    data/ フォルダが存在しない場合は自動で作成する。
    """
    DB_PATH.parent.mkdir(exist_ok=True)   # data/ フォルダがなければ作る
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row        # 行データを辞書のように扱う
    return conn


def init_db():
    """
    schema.sql を読み込んで DB を初期化する。

    CREATE TABLE IF NOT EXISTS を使っているので、
    すでにテーブルが存在する場合は何もしない。
    """
    conn = get_connection()
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def insert_page(page: dict) -> int:
    """
    ページ情報を DB に登録する。

    INSERT OR REPLACE：同じ URL のデータがあれば上書き、なければ新規追加する。
    keywords は pages テーブルとは別に keywords テーブルへ保存する。

    Args:
        page: ページ情報の辞書（crawl_url() の返り値と同形式）

    Returns:
        登録された行の id
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO pages
            (url, title, description, full_text, author, category, word_count, crawled_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        page["url"],
        page["title"],
        page.get("description", ""),
        page.get("full_text", ""),
        page.get("author", ""),
        page.get("category", ""),
        page.get("word_count", 0),
        page.get("crawled_at", datetime.now().isoformat()),
    ))

    page_id = cursor.lastrowid

    # ── keywords テーブルへ保存 ──────────────────────────────
    # crawler.py は keywords を list で返すが、
    # 文字列（カンマ区切り）で来る場合も考慮して両対応する。
    kw = page.get("keywords", [])
    if isinstance(kw, str):
        kw_list = [k.strip() for k in kw.split(",") if k.strip()]
    else:
        kw_list = [k.strip() for k in kw if k.strip()]

    if kw_list:
        # 同じページを再クロールした場合は古いキーワードを削除してから再登録する
        cursor.execute("DELETE FROM keywords WHERE page_id = ?", (page_id,))
        cursor.executemany(
            "INSERT INTO keywords (page_id, keyword) VALUES (?, ?)",
            [(page_id, kw_item) for kw_item in kw_list],
        )

    conn.commit()
    conn.close()
    return page_id


def get_all_pages() -> list:
    """
    全ページを登録日時の新しい順で取得する。

    keywords テーブルを LEFT JOIN し、キーワードをカンマ区切り文字列として結合する。
    ranking.py と app.py が期待する 'keywords' キーをここで付与する。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.*,
            GROUP_CONCAT(k.keyword, ', ') AS keywords
        FROM pages p
        LEFT JOIN keywords k ON k.page_id = p.id
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_search(query: str, results_count: int, user_id: str = None) -> int:
    """
    検索クエリと結果件数を search_logs テーブルに記録する。

    Args:
        query:         検索キーワード
        results_count: 検索結果の件数
        user_id:       ユーザー識別子（任意）

    Returns:
        登録された行の id
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO search_logs (query, results_count, user_id)
        VALUES (?, ?, ?)
    """, (query, results_count, user_id))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id
