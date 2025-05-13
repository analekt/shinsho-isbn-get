#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import os
import logging
from typing import Dict, Any

class ConfigLoader:
    """設定ファイル読み込みクラス"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """初期化
        
        Args:
            config_file: 設定ファイルのパス
        """
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # デフォルト設定
        self.default_config = {
            "api": {
                "base_wait_time": 0.5, 
                "max_wait_time": 8.0,
                "timeout": 30,
                "max_retries": 3
            },
            "cache": {
                "dir": "./data",
                "books_max_age_days": 30,
                "coverage_max_age_hours": 24,
                "cleanup_older_than_days": 90
            },
            "processing": {
                "chunk_size": 100,
                "sample_limit": 100,
                "shinsho_c_code_prefix": "02"
            },
            "output": {
                "dir": "./docs",
                "title": "新書RSS",
                "description": "OpenBD APIから取得した新しい新書の情報",
                "filename": "feed.xml"
            }
        }
        
        # 設定を読み込み
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む
        
        Returns:
            設定データ
        """
        # デフォルト設定をコピー
        config = dict(self.default_config)
        
        # 設定ファイルが存在する場合は読み込み
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f)
                    
                # 読み込んだ設定をデフォルト設定にマージ
                if file_config:
                    self._deep_update(config, file_config)
                    
                self.logger.info(f"設定ファイルを読み込みました: {self.config_file}")
            except Exception as e:
                self.logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
        else:
            self.logger.warning(f"設定ファイルが見つかりません: {self.config_file}")
            self.logger.info("デフォルト設定を使用します")
        
        return config
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """辞書を再帰的に更新
        
        Args:
            base_dict: 更新される辞書
            update_dict: 更新する値を持つ辞書
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                # 再帰的に辞書を更新
                self._deep_update(base_dict[key], value)
            else:
                # 値を更新
                base_dict[key] = value
    
    def get(self, key: str = None) -> Any:
        """設定値を取得
        
        Args:
            key: 設定キー（ドットで区切られたパス）。Noneの場合は全設定を返す。
            
        Returns:
            設定値、または全設定
        """
        if key is None:
            return self.config
            
        # ドットで区切られたパスを処理
        parts = key.split(".")
        result = self.config
        
        for part in parts:
            if part in result:
                result = result[part]
            else:
                # キーが存在しない場合はNoneを返す
                self.logger.warning(f"設定キーが見つかりません: {key}")
                return None
                
        return result


if __name__ == "__main__":
    # 簡単な使用例
    logging.basicConfig(level=logging.INFO)
    
    config = ConfigLoader()
    print("API設定:")
    print(f"  待機時間: {config.get('api.base_wait_time')}秒")
    print(f"  タイムアウト: {config.get('api.timeout')}秒")
    
    print("\nキャッシュ設定:")
    print(f"  ディレクトリ: {config.get('cache.dir')}")
    print(f"  書籍キャッシュ有効期間: {config.get('cache.books_max_age_days')}日")
    
    print("\n出力設定:")
    print(f"  タイトル: {config.get('output.title')}")
    print(f"  説明: {config.get('output.description')}") 