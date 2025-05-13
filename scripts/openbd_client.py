#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import json
import os
import logging
import datetime
from typing import List, Dict, Optional, Any, Set, Tuple

class OpenBDClient:
    """OpenBD APIのクライアント"""
    
    BASE_URL = "https://api.openbd.jp/v1"
    
    def __init__(self, cache_dir: str = "./data"):
        """初期化
        
        Args:
            cache_dir: キャッシュディレクトリのパス
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 書籍データのキャッシュディレクトリ
        self.books_cache_dir = os.path.join(cache_dir, "book_cache")
        os.makedirs(self.books_cache_dir, exist_ok=True)
        
        # ロガーの設定
        self.logger = logging.getLogger(__name__)
        
    def get_coverage(self) -> List[str]:
        """収録されているISBNの一覧を取得
        
        Returns:
            ISBNのリスト
        """
        url = f"{self.BASE_URL}/coverage"
        
        # ファイルキャッシュのパス
        cache_file = os.path.join(self.cache_dir, "coverage_cache.json")
        cache_max_age = 24 * 60 * 60  # 24時間
        
        # キャッシュが有効な場合はキャッシュから返す
        if os.path.exists(cache_file):
            file_time = os.path.getmtime(cache_file)
            if time.time() - file_time < cache_max_age:
                self.logger.info(f"キャッシュからISBN一覧を読み込みます（{cache_file}）")
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        
        # APIからデータを取得
        self.logger.info("APIからISBN一覧を取得します")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            isbns = response.json()
            
            # キャッシュに保存
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(isbns, f, ensure_ascii=False)
                
            return isbns
            
        except Exception as e:
            self.logger.error(f"ISBN一覧の取得に失敗しました: {e}")
            
            # エラー時に既存のキャッシュがあれば、それを返す（緊急時対応）
            if os.path.exists(cache_file):
                self.logger.warning("エラーが発生したため、古いキャッシュを使用します")
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # キャッシュも無い場合は空リストを返す
            return []
    
    def get_books(self, isbns: List[str]) -> List[Dict[str, Any]]:
        """ISBNリストから書籍情報を取得（キャッシュ利用）
        
        Args:
            isbns: 取得する書籍のISBNリスト
        
        Returns:
            書籍情報のリスト
        """
        return self.get_books_with_cache(isbns)
    
    def get_books_with_cache(self, isbns: List[str], cache_max_age: int = 30 * 24 * 60 * 60) -> List[Dict[str, Any]]:
        """キャッシュを活用して書籍情報を取得
        
        Args:
            isbns: 取得する書籍のISBNリスト
            cache_max_age: キャッシュの有効期間（秒）、デフォルトは30日
        
        Returns:
            書籍情報のリスト
        """
        if not isbns:
            return []
        
        # キャッシュから取得済みの書籍を除外
        uncached_isbns = []
        cached_books = []
        
        for isbn in isbns:
            cache_file = os.path.join(self.books_cache_dir, f"{isbn}.json")
            if os.path.exists(cache_file):
                # キャッシュファイルの更新日時を確認
                file_time = os.path.getmtime(cache_file)
                if time.time() - file_time < cache_max_age:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        try:
                            book = json.load(f)
                            cached_books.append(book)
                            continue
                        except json.JSONDecodeError:
                            # キャッシュファイルが破損している場合は再取得
                            pass
            
            uncached_isbns.append(isbn)
        
        # キャッシュの状況をログに出力
        self.logger.info(f"キャッシュから{len(cached_books)}件の書籍情報を読み込みました")
        if uncached_isbns:
            self.logger.info(f"APIから{len(uncached_isbns)}件の新規書籍情報を取得します")
        
        # APIからまだキャッシュされていない書籍を取得
        new_books = []
        if uncached_isbns:
            new_books = self._fetch_books_from_api(uncached_isbns)
            
            # キャッシュに保存
            for book in new_books:
                if book:
                    isbn = self._extract_isbn_from_book(book)
                    if isbn:
                        cache_file = os.path.join(self.books_cache_dir, f"{isbn}.json")
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(book, f, ensure_ascii=False, indent=2)
        
        # キャッシュと新しく取得した書籍を結合
        return cached_books + new_books
    
    def _extract_isbn_from_book(self, book: Dict[str, Any]) -> str:
        """書籍データからISBNを抽出
        
        Args:
            book: 書籍データ
            
        Returns:
            ISBN文字列
        """
        # summaryからの取得を試みる
        if "summary" in book and book["summary"].get("isbn"):
            return book["summary"].get("isbn")
            
        # onixからの取得を試みる
        if "onix" in book:
            # RecordReferenceを使用
            record_ref = book["onix"].get("RecordReference")
            if record_ref:
                return record_ref
                
            # ProductIdentifierを使用
            identifiers = book["onix"].get("ProductIdentifier", [])
            if isinstance(identifiers, list):
                for identifier in identifiers:
                    if identifier.get("ProductIDType") == "15":  # 15 = ISBN-13
                        return identifier.get("IDValue", "")
            elif isinstance(identifiers, dict):
                if identifiers.get("ProductIDType") == "15":
                    return identifiers.get("IDValue", "")
                    
        return ""
    
    def _fetch_books_from_api(self, isbns: List[str]) -> List[Dict[str, Any]]:
        """APIから書籍情報を取得（スロットリングとバックオフ機能付き）
        
        Args:
            isbns: 取得する書籍のISBNリスト
        
        Returns:
            書籍情報のリスト
        """
        if not isbns:
            return []
            
        # APIの制限に合わせて10件ずつに分割
        chunk_size = 10
        result = []
        
        # スロットリングとバックオフのパラメータ
        base_wait_time = 0.5  # 基本待機時間（秒）
        max_wait_time = 8.0   # 最大待機時間（秒）
        current_wait = base_wait_time
        max_retries = 3
        
        for i in range(0, len(isbns), chunk_size):
            chunk = isbns[i:i+chunk_size]
            isbn_param = ",".join(chunk)
            url = f"{self.BASE_URL}/get?isbn={isbn_param}"
            
            for retry in range(max_retries):
                try:
                    self.logger.debug(f"APIリクエスト: {url}")
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    books = response.json()
                    
                    # Noneでない要素のみを追加
                    result.extend([book for book in books if book])
                    
                    # 成功したら待機時間をリセット
                    current_wait = base_wait_time
                    break
                    
                except (requests.RequestException, json.JSONDecodeError) as e:
                    # エラー時は指数バックオフで待機時間を増やす
                    if retry < max_retries - 1:
                        sleep_time = current_wait * (1.5 ** retry)
                        self.logger.warning(f"APIリクエストが失敗しました。{sleep_time:.1f}秒後に再試行します: {e}")
                        time.sleep(min(sleep_time, max_wait_time))
                        current_wait = min(current_wait * 2, max_wait_time)
                    else:
                        # 最大リトライ回数に達したらエラーを記録して続行
                        self.logger.error(f"APIリクエストが最大試行回数に達しました: {url} - {str(e)}")
            
            # APIへの負荷を抑えるため少し待機
            if i + chunk_size < len(isbns):
                time.sleep(current_wait)
        
        return result
    
    def get_latest_isbns(self, last_updated: str = None) -> List[str]:
        """前回の更新以降に追加されたISBNのみを取得
        
        Args:
            last_updated: 前回の更新日時（YYYY-MM-DD形式）
        
        Returns:
            新しく追加されたISBNのリスト
        """
        # 前回の更新情報を保存/読み込みするファイル
        update_file = os.path.join(self.cache_dir, "last_update.json")
        
        # 前回の更新情報を取得
        if last_updated is None and os.path.exists(update_file):
            with open(update_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_updated = data.get("last_updated")
                last_isbns = set(data.get("isbns", []))
        else:
            last_isbns = set()
        
        # 現在のISBN一覧を取得
        current_isbns = set(self.get_coverage())
        
        # 差分を計算
        new_isbns = list(current_isbns - last_isbns)
        
        # 更新情報を保存
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(update_file, "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": current_date,
                "isbns": list(current_isbns)
            }, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"全ISBN数: {len(current_isbns)}, 新規ISBN数: {len(new_isbns)}")
        return new_isbns
    
    def save_processed_isbns(self, isbns: List[str]):
        """処理済みISBNを保存
        
        Args:
            isbns: 処理済みのISBNリスト
        """
        file_path = os.path.join(self.cache_dir, "processed_isbns.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(isbns, f, ensure_ascii=False, indent=2)
    
    def load_processed_isbns(self) -> List[str]:
        """処理済みISBNを読み込み
        
        Returns:
            処理済みのISBNリスト
        """
        file_path = os.path.join(self.cache_dir, "processed_isbns.json")
        if not os.path.exists(file_path):
            return []
            
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clear_old_cache(self, max_age_days: int = 90):
        """古いキャッシュファイルを削除
        
        Args:
            max_age_days: キャッシュの最大保持日数
        """
        max_age_seconds = max_age_days * 24 * 60 * 60
        now = time.time()
        
        # 書籍キャッシュの掃除
        count = 0
        for filename in os.listdir(self.books_cache_dir):
            file_path = os.path.join(self.books_cache_dir, filename)
            if os.path.isfile(file_path):
                file_time = os.path.getmtime(file_path)
                if now - file_time > max_age_seconds:
                    os.remove(file_path)
                    count += 1
        
        if count > 0:
            self.logger.info(f"{count}件の古いキャッシュファイルを削除しました")


if __name__ == "__main__":
    # 簡単な使用例
    logging.basicConfig(level=logging.INFO)
    
    client = OpenBDClient()
    # 差分更新でISBNを取得
    new_isbns = client.get_latest_isbns()
    print(f"新規ISBN数: {len(new_isbns)}")
    
    # 最初の3件の書籍情報を取得（キャッシュ利用）
    if new_isbns:
        books = client.get_books(new_isbns[:3])
        for book in books:
            if book:
                print(f"ISBN: {client._extract_isbn_from_book(book)}")
                print(f"タイトル: {book.get('summary', {}).get('title')}")
                print("-" * 30) 