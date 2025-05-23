#!/bin/bash

# 必要なディレクトリを作成
mkdir -p data
mkdir -p data/book_cache
mkdir -p docs

# サンプルデータで初期実行（キャッシュを活用）
echo "サンプルデータで初期実行します..."

# まず差分更新モードで軽く実行
echo "1. 差分更新モードで実行..."
python scripts/main.py --sample

book_count=$(find docs -name "feed.xml" -exec grep -c "<item>" {} \; 2>/dev/null || echo "0")
echo "検出された新書数: $book_count"

# 全更新モードの分岐・実行を削除

echo "初期化が完了しました。"
echo "GitHub Pagesを有効にするには、リポジトリの設定から「Pages」を選択し、ソースを「main」ブランチの「docs」ディレクトリに設定してください。"
echo ""
echo "更新頻度: 週3回（月・水・金）"
echo "完全更新: 毎月1日" 