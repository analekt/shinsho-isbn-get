#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Dict, Any, Optional
import datetime
import json
import os

class BookProcessor:
    """書籍情報の処理クラス"""
    
    def __init__(self, data_dir: str = "./data"):
        """初期化
        
        Args:
            data_dir: データディレクトリのパス
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
    def is_shinsho(self, book: Dict[str, Any]) -> bool:
        """新書かどうかを判定
        
        Args:
            book: 書籍情報
            
        Returns:
            新書の場合True
        """
        if not book:
            return False
            
        # 「C」コード/ジャンルコードを取得
        onix = book.get("onix", {})
        descriptive_detail = onix.get("DescriptiveDetail", {})
        subjects = descriptive_detail.get("Subject", [])
        
        for subject in subjects:
            subject_code = subject.get("SubjectCode", "")
            subject_scheme = subject.get("SubjectSchemeIdentifier", "")
            
            # Cコードを探す (79がCコード)
            if subject_scheme == "79" and subject_code.startswith("02"):
                return True
                
        return False
        
    def extract_book_info(self, book: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """書籍から必要な情報を抽出
        
        Args:
            book: 書籍情報
            
        Returns:
            抽出した情報、または抽出できなかった場合None
        """
        if not book:
            return None
            
        onix = book.get("onix", {})
        
        # 基本情報の取得
        descriptive_detail = onix.get("DescriptiveDetail", {})
        title_detail = descriptive_detail.get("TitleDetail", {})
        title_elements = title_detail.get("TitleElement", [{}])[0] if title_detail.get("TitleElement") else {}
        
        # 出版社情報の取得
        publishing_detail = onix.get("PublishingDetail", {})
        imprint = publishing_detail.get("Imprint", {})
        publisher = publishing_detail.get("Publisher", {})
        
        # 内容紹介の取得
        collateral_detail = onix.get("CollateralDetail", {})
        text_contents = collateral_detail.get("TextContent", [])
        description = ""
        
        for text in text_contents:
            # TextTypeが「03」なら内容紹介
            if text.get("TextType") == "03":
                description = text.get("Text", "")
                break
                
        # 著者情報の取得
        contributors = descriptive_detail.get("Contributor", [])
        authors = []
        
        for contributor in contributors:
            role = contributor.get("ContributorRole", "")
            # A01が著者
            if role == "A01":
                name = contributor.get("PersonName", {}).get("content", "")
                if not name:
                    name = contributor.get("PersonName", "")
                if name:
                    authors.append(name)
        
        # ISBN情報
        identifiers = onix.get("ProductIdentifier", [])
        isbn = ""
        
        if isinstance(identifiers, list):
            for identifier in identifiers:
                if identifier.get("ProductIDType") == "15":  # 15 = ISBN-13
                    isbn = identifier.get("IDValue", "")
                    break
        elif isinstance(identifiers, dict):
            if identifiers.get("ProductIDType") == "15":
                isbn = identifiers.get("IDValue", "")
        
        # リンク情報
        if not isbn:
            # RecordReferenceからISBNを取得（代替）
            isbn = onix.get("RecordReference", "")
        
        # 出版日情報の取得
        publishing_dates = publishing_detail.get("PublishingDate", [])
        pub_date = ""
        
        for date in publishing_dates:
            if date.get("PublishingDateRole") == "01":  # 01 = 出版日
                pub_date = date.get("Date", "")
                break
        
        # 価格の取得
        product_supply = onix.get("ProductSupply", {})
        supply_details = product_supply.get("SupplyDetail", {})
        price_info = {}
        
        if isinstance(supply_details, dict):
            prices = supply_details.get("Price", [])
            if isinstance(prices, list) and prices:
                price_info = prices[0]
            elif isinstance(prices, dict):
                price_info = prices
        
        price = price_info.get("PriceAmount", "")
        
        # 結果を返す
        return {
            "isbn": isbn,
            "title": title_elements.get("TitleText", ""),
            "subtitle": title_elements.get("Subtitle", ""),
            "authors": authors,
            "description": description,
            "publisher": imprint.get("ImprintName", "") or publisher.get("PublisherName", ""),
            "publish_date": pub_date,
            "price": price
        }

    def save_new_books(self, books: List[Dict[str, Any]]):
        """新しい書籍情報を保存
        
        Args:
            books: 書籍情報のリスト
        """
        file_path = os.path.join(self.data_dir, "new_books.json")
        
        # 既存データの読み込み
        existing_books = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    existing_books = json.load(f)
                except json.JSONDecodeError:
                    existing_books = []
        
        # 現在の日付を追加
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        daily_data = {
            "date": current_date,
            "books": books
        }
        
        # 最大10日分のデータを保持
        existing_books.insert(0, daily_data)
        if len(existing_books) > 10:
            existing_books = existing_books[:10]
        
        # データの保存
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_books, f, ensure_ascii=False, indent=2)
            
    def get_new_books(self) -> List[Dict[str, Any]]:
        """新しい書籍情報を取得
        
        Returns:
            最新の書籍情報リスト
        """
        file_path = os.path.join(self.data_dir, "new_books.json")
        
        if not os.path.exists(file_path):
            return []
            
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                all_books = json.load(f)
                if all_books and isinstance(all_books, list) and len(all_books) > 0:
                    return all_books[0].get("books", [])
                return []
            except json.JSONDecodeError:
                return [] 