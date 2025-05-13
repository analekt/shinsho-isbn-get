#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from feedgen.feed import FeedGenerator
from typing import List, Dict, Any
import datetime
import os
import logging

# タイムゾーン情報を取り扱うためのモジュール
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python 3.8以前の場合はpython-dateutilを使用
    from dateutil.tz import tzlocal

logger = logging.getLogger(__name__)

class RSSGenerator:
    """RSSフィードを生成するクラス"""
    
    def __init__(self, output_dir: str = "./docs"):
        """初期化
        
        Args:
            output_dir: 出力ディレクトリのパス
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_rss(self, books: List[Dict[str, Any]], feed_url: str, site_url: str, title: str, description: str):
        """RSSフィードを生成
        
        Args:
            books: 書籍情報のリスト
            feed_url: フィードのURL
            site_url: サイトのURL
            title: フィードのタイトル
            description: フィードの説明
        """
        fg = FeedGenerator()
        fg.id(feed_url)
        fg.title(title)
        fg.author({'name': 'OpenBD RSS Generator', 'email': 'info@example.com'})
        fg.link(href=site_url, rel='alternate')
        fg.link(href=feed_url, rel='self')
        fg.language('ja')
        fg.description(description)
        
        # 現在時刻（タイムゾーン付き）
        try:
            # Python 3.9以降の場合
            now = datetime.datetime.now(ZoneInfo("Asia/Tokyo"))
        except NameError:
            # Python 3.8以前の場合
            now = datetime.datetime.now(tzlocal())
        
        # アイテムの追加
        for book in books:
            fe = fg.add_entry()
            
            # タイトルの設定
            title = book.get("title", "")
            subtitle = book.get("subtitle", "")
            full_title = title
            if subtitle:
                full_title = f"{title}：{subtitle}"
                
            fe.id(f"urn:isbn:{book.get('isbn', '')}")
            fe.title(full_title)
            
            # 著者の設定
            authors = book.get("authors", [])
            author_text = "、".join(authors) if authors else "不明"
            fe.author({'name': author_text})
            
            # 内容の設定
            description = book.get("description", "")
            publisher = book.get("publisher", "")
            price = book.get("price", "")
            
            content = f"""<p><strong>出版社:</strong> {publisher}</p>
<p><strong>著者:</strong> {author_text}</p>
"""
            
            if price:
                content += f"<p><strong>価格:</strong> {price}円</p>\n"
                
            if description:
                content += f"<p><strong>内容:</strong></p>\n<p>{description}</p>"
                
            fe.content(content, type="html")
            
            # リンクの設定
            isbn = book.get("isbn", "")
            if isbn:
                link = f"https://api.openbd.jp/v1/get?isbn={isbn}"
                fe.link(href=link, rel='alternate')
                
            # 日付の設定
            pub_date = book.get("publish_date", "")
            try:
                if len(pub_date) == 8:  # YYYYMMDD形式
                    dt = datetime.datetime.strptime(pub_date, "%Y%m%d")
                    # タイムゾーン情報を追加
                    try:
                        dt = dt.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
                    except NameError:
                        dt = dt.replace(tzinfo=tzlocal())
                    fe.published(dt)
                else:
                    # 現在時刻を使用（タイムゾーン付き）
                    fe.published(now)
            except (ValueError, TypeError):
                # エラーが発生した場合も現在時刻を使用
                logger.warning(f"日付の解析エラー: {pub_date}、現在時刻を使用します")
                fe.published(now)
                
        # ファイルに保存
        file_path = os.path.join(self.output_dir, "feed.xml")
        fg.rss_file(file_path, pretty=True)
        
        # HTMLインデックスの生成
        self._generate_html_index(title, description, books)
        
    def _generate_html_index(self, title: str, description: str, books: List[Dict[str, Any]]):
        """HTMLインデックスページを生成
        
        Args:
            title: ページのタイトル
            description: ページの説明
            books: 書籍情報のリスト
        """
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .book {{
            margin-bottom: 30px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .book h2 {{
            margin-top: 0;
            color: #007bff;
        }}
        .book-meta {{
            color: #666;
            margin-bottom: 10px;
        }}
        .rss-link {{
            display: inline-block;
            margin-top: 20px;
            background-color: #FF8C00;
            color: white;
            padding: 5px 15px;
            text-decoration: none;
            border-radius: 3px;
        }}
        .rss-link:hover {{
            background-color: #e67e00;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>{description}</p>
    
    <a href="feed.xml" class="rss-link">RSSフィードを購読</a>
    
    <h2>最新の新書</h2>
"""
        
        for book in books:
            title = book.get("title", "")
            subtitle = book.get("subtitle", "")
            full_title = title
            if subtitle:
                full_title = f"{title}：{subtitle}"
                
            authors = book.get("authors", [])
            author_text = "、".join(authors) if authors else "不明"
            
            publisher = book.get("publisher", "")
            description = book.get("description", "")
            isbn = book.get("isbn", "")
            
            html += f"""
    <div class="book">
        <h2>{full_title}</h2>
        <div class="book-meta">
            著者: {author_text} | 出版社: {publisher}
        </div>
        <p>{description}</p>
    </div>
"""
        
        html += """
    <footer>
        <p>このページは<a href="https://openbd.jp/">OpenBD</a>のデータを使用しています。</p>
    </footer>
</body>
</html>
"""
        
        file_path = os.path.join(self.output_dir, "index.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html) 