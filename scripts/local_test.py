#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import argparse
import webbrowser
import http.server
import socketserver
import threading
import time
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.openbd_client import OpenBDClient
from scripts.book_processor import BookProcessor
from scripts.rss_generator import RSSGenerator
from scripts.config_loader import ConfigLoader

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def start_local_server(directory, port=8000):
    """ローカルWebサーバーを起動
    
    Args:
        directory: 公開するディレクトリ
        port: ポート番号
    """
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    
    class CustomServer(socketserver.TCPServer):
        allow_reuse_address = True
    
    with CustomServer(("", port), handler) as httpd:
        logger.info(f"ローカルサーバーを起動しました: http://localhost:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("サーバーを停止します...")
            httpd.shutdown()

def run_test(args):
    """テスト実行
    
    Args:
        args: コマンドライン引数
    """
    # 設定の読み込み
    config = ConfigLoader(args.config)
    
    # 出力ディレクトリを絶対パスに変換
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # キャッシュディレクトリを絶対パスに変換
    cache_dir = os.path.abspath(args.cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    
    logger.info(f"出力ディレクトリ: {output_dir}")
    logger.info(f"キャッシュディレクトリ: {cache_dir}")
    
    # 各クラスの初期化
    client = OpenBDClient(cache_dir=cache_dir)
    processor = BookProcessor(data_dir=cache_dir)
    generator = RSSGenerator(output_dir=output_dir)
    
    # 古いキャッシュの削除（オプション）
    if args.clean_cache:
        logger.info("古いキャッシュを削除します")
        client.clear_old_cache(max_age_days=config.get("cache.cleanup_older_than_days"))
    
    # 処理の実行
    try:
        # 収録範囲の取得
        if args.full_refresh:
            logger.info("完全更新モード: OpenBD APIから全収録範囲を取得中...")
            all_isbns = client.get_coverage()
            processed_isbns = client.load_processed_isbns()
            new_isbns = [isbn for isbn in all_isbns if isbn not in processed_isbns]
        else:
            logger.info("差分更新モード: 前回更新以降の新規ISBNを取得中...")
            new_isbns = client.get_latest_isbns()
            
        logger.info(f"新規ISBN数: {len(new_isbns)}")
        
        # サンプルモードの場合は制限
        sample_limit = config.get("processing.sample_limit")
        if args.sample and len(new_isbns) > sample_limit:
            logger.info(f"サンプルモード: 最初の{sample_limit}件のみ処理します")
            new_isbns = new_isbns[:sample_limit]
            
        # 新書の抽出
        new_shinsho_books = []
        
        # チャンク処理
        chunk_size = config.get("processing.chunk_size")
        for i in range(0, len(new_isbns), chunk_size):
            chunk = new_isbns[i:i+chunk_size]
            logger.info(f"ISBNチャンク {i+1}〜{i+len(chunk)} / {len(new_isbns)} を処理中...")
            
            # 書籍情報の取得
            books = client.get_books(chunk)
            
            # 新書のフィルタリングと情報抽出
            for book in books:
                if processor.is_shinsho(book):
                    book_info = processor.extract_book_info(book)
                    if book_info:
                        new_shinsho_books.append(book_info)
        
        logger.info(f"新規新書数: {len(new_shinsho_books)}")
        
        # データの保存（オプション）
        if not args.no_save:
            if new_isbns:
                processed_isbns = client.load_processed_isbns()
                processed_isbns.extend(new_isbns)
                client.save_processed_isbns(processed_isbns)
                logger.info(f"処理済みISBNを更新しました: {len(processed_isbns)}件")
            
            if new_shinsho_books:
                processor.save_new_books(new_shinsho_books)
                logger.info(f"新規新書情報を保存しました: {len(new_shinsho_books)}件")
        
        # 既存データの使用（オプション）
        if not new_shinsho_books and args.use_existing:
            logger.info("新規の新書が見つかりませんでした。最新の保存データを使用します。")
            new_shinsho_books = processor.get_new_books()
        
        # RSSフィード生成
        if new_shinsho_books:
            feed_url = f"http://localhost:{args.port}/feed.xml" if args.server else f"file://{output_dir}/feed.xml"
            site_url = f"http://localhost:{args.port}/" if args.server else f"file://{output_dir}/"
            
            logger.info("RSSフィードを生成中...")
            generator.generate_rss(
                books=new_shinsho_books,
                feed_url=feed_url,
                site_url=site_url,
                title=config.get("output.title"),
                description=config.get("output.description")
            )
            
            feed_path = os.path.join(output_dir, "feed.xml")
            index_path = os.path.join(output_dir, "index.html")
            
            logger.info(f"RSSフィードを生成しました: {feed_path}")
            logger.info(f"HTMLインデックスを生成しました: {index_path}")
            
            return (feed_path, index_path)
        else:
            logger.warning("新書情報が見つからなかったため、RSSフィードは更新されませんでした。")
            return None
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        return None

def main():
    parser = argparse.ArgumentParser(description="OpenBD APIから新書情報を取得してRSSフィードを生成するローカルテスト")
    parser.add_argument("--cache-dir", default="./data", help="キャッシュディレクトリのパス")
    parser.add_argument("--output-dir", default="./output", help="出力ディレクトリのパス")
    parser.add_argument("--config", default="config.yaml", help="設定ファイルのパス")
    parser.add_argument("--sample", action="store_true", help="サンプルモード（件数を制限）")
    parser.add_argument("--full-refresh", action="store_true", help="全データを再取得するモード")
    parser.add_argument("--clean-cache", action="store_true", help="古いキャッシュを削除する")
    parser.add_argument("--no-save", action="store_true", help="データを保存しない")
    parser.add_argument("--use-existing", action="store_true", help="新規データがない場合に既存データを使用")
    parser.add_argument("--server", action="store_true", help="ローカルWebサーバーを起動する")
    parser.add_argument("--port", type=int, default=8000, help="ローカルWebサーバーのポート番号")
    parser.add_argument("--browser", action="store_true", help="処理後にブラウザで開く")
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 処理の実行
    result = run_test(args)
    
    # 処理時間の表示
    elapsed_time = time.time() - start_time
    logger.info(f"処理が完了しました（処理時間: {elapsed_time:.2f}秒）")
    
    # 結果の表示
    if result:
        feed_path, index_path = result
        
        # ファイルURLを作成
        file_url = f"file://{index_path}"
        
        logger.info("=====================================================")
        logger.info(f"RSSフィード: {feed_path}")
        logger.info(f"HTMLページ: {index_path}")
        logger.info("=====================================================")
        
        # ローカルサーバーの起動（オプション）
        if args.server:
            server_thread = threading.Thread(
                target=start_local_server, 
                args=(os.path.dirname(index_path), args.port),
                daemon=True
            )
            server_thread.start()
            
            # URLを更新
            file_url = f"http://localhost:{args.port}/index.html"
            logger.info(f"ローカルサーバーURL: {file_url}")
            logger.info("サーバーを停止するには Ctrl+C を押してください")
            
        # ブラウザで開く（オプション）
        if args.browser:
            logger.info(f"ブラウザでページを開きます: {file_url}")
            webbrowser.open(file_url)
            
        # サーバーモードならスレッドが終了するまで待機
        if args.server:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("終了します...")
    
if __name__ == "__main__":
    main() 