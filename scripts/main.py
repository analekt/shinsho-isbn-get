#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import logging
import sys
import time
from typing import List, Dict, Any

from openbd_client import OpenBDClient
from book_processor import BookProcessor
from rss_generator import RSSGenerator

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="OpenBD APIから新書情報を取得してRSSフィードを生成します")
    parser.add_argument("--data-dir", default="./data", help="データディレクトリのパス")
    parser.add_argument("--output-dir", default="./docs", help="出力ディレクトリのパス")
    parser.add_argument("--feed-url", default="https://example.com/feed.xml", help="フィードのURL")
    parser.add_argument("--site-url", default="https://example.com/", help="サイトのURL")
    parser.add_argument("--title", default="新書RSS", help="フィードのタイトル")
    parser.add_argument("--description", default="OpenBD APIから取得した新しい新書の情報", help="フィードの説明")
    parser.add_argument("--sample", action="store_true", help="サンプルモード（新しいデータを保存しない）")
    parser.add_argument("--full-refresh", action="store_true", help="全データを再取得するモード")
    parser.add_argument("--clean-cache", action="store_true", help="古いキャッシュを削除する")
    args = parser.parse_args()
    
    # ディレクトリを作成
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 各クラスの初期化
    client = OpenBDClient(cache_dir=args.data_dir)
    processor = BookProcessor(data_dir=args.data_dir)
    generator = RSSGenerator(output_dir=args.output_dir)
    
    # 古いキャッシュの削除（オプション）
    if args.clean_cache:
        logger.info("古いキャッシュを削除します")
        client.clear_old_cache(max_age_days=30)  # 30日以上経過したキャッシュを削除
    
    # 処理済みISBNの読み込み
    processed_isbns = client.load_processed_isbns()
    logger.info(f"処理済みISBN数: {len(processed_isbns)}")
    
    start_time = time.time()
    
    try:
        # 収録範囲の取得（更新方法選択）
        if args.full_refresh:
            # 完全更新モードの場合は全ISBNを取得
            logger.info("完全更新モード: OpenBD APIから全収録範囲を取得中...")
            all_isbns = client.get_coverage()
            new_isbns = [isbn for isbn in all_isbns if isbn not in processed_isbns]
        else:
            # 差分更新モードの場合は新しいISBNのみ取得
            logger.info("差分更新モード: 前回更新以降の新規ISBNを取得中...")
            new_isbns = client.get_latest_isbns()
            
        logger.info(f"新規ISBN数: {len(new_isbns)}")
        
        # 書籍情報の取得とフィルタリング
        logger.info("新規ISBNから書籍情報を取得中...")
        
        # サンプルモードの場合は最大100件に制限
        if args.sample and len(new_isbns) > 100:
            logger.info(f"サンプルモード: 最初の100件のみ処理します")
            new_isbns = new_isbns[:100]
            
        # 新書の抽出
        new_shinsho_books = []
        
        # チャンク単位で処理（メモリ対策とエラー時の継続性向上）
        chunk_size = 100
        for i in range(0, len(new_isbns), chunk_size):
            chunk = new_isbns[i:i+chunk_size]
            logger.info(f"ISBNチャンク {i+1}〜{i+len(chunk)} / {len(new_isbns)} を処理中...")
            
            try:
                # 書籍情報の取得（キャッシュ機能付き）
                books = client.get_books(chunk)
                
                # 新書のフィルタリングと情報抽出
                for book in books:
                    if processor.is_shinsho(book):
                        book_info = processor.extract_book_info(book)
                        if book_info:
                            new_shinsho_books.append(book_info)
            
            except Exception as e:
                # チャンク処理中のエラーは記録して次のチャンクに進む
                logger.error(f"チャンク処理中にエラーが発生しました: {e}", exc_info=True)
        
        logger.info(f"新規新書数: {len(new_shinsho_books)}")
        
        # 処理済みISBNの更新（サンプルモードでなければ）
        if not args.sample:
            processed_isbns.extend(new_isbns)
            client.save_processed_isbns(processed_isbns)
            logger.info(f"処理済みISBNを更新しました: {len(processed_isbns)}件")
            
            # 新規新書情報の保存
            if new_shinsho_books:
                processor.save_new_books(new_shinsho_books)
                logger.info(f"新規新書情報を保存しました: {len(new_shinsho_books)}件")
        
        # 既存の新書データがない場合は、保存されたデータを読み込む
        if not new_shinsho_books and not args.sample and not args.full_refresh:
            logger.info("新規の新書が見つかりませんでした。最新の保存データを使用します。")
            new_shinsho_books = processor.get_new_books()
            
        # RSSフィードの生成
        if new_shinsho_books:
            logger.info("RSSフィードを生成中...")
            generator.generate_rss(
                books=new_shinsho_books,
                feed_url=args.feed_url,
                site_url=args.site_url,
                title=args.title,
                description=args.description
            )
            logger.info(f"RSSフィードを生成しました: {os.path.join(args.output_dir, 'feed.xml')}")
            logger.info(f"HTMLインデックスを生成しました: {os.path.join(args.output_dir, 'index.html')}")
        else:
            logger.warning("新書情報が見つからなかったため、RSSフィードは更新されませんでした。")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        sys.exit(1)
        
    elapsed_time = time.time() - start_time
    logger.info(f"処理が完了しました（処理時間: {elapsed_time:.2f}秒）")
    
if __name__ == "__main__":
    main() 