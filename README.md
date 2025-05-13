# 新書RSS生成

OpenBDのAPIから新しく追加された新書（Cコード/ジャンルコードが「02」から始まる書籍）の情報を取得し、RSSフィードとして配信するシステムです。

## 機能

- OpenBD APIから定期的に新しい書籍データを取得
- 「02」から始まるCコード/ジャンルコードを持つ新書のみをフィルタリング
- 新たに追加された書籍情報からRSSフィードを生成
- GitHub Actionsで自動実行（週3回：月・水・金）
- GitHub Pagesでフィードを公開

## API負荷軽減機能

このプロジェクトは以下の機能によりOpenBD APIへの負荷を最小限に抑えています：

- **差分更新**: 前回の実行以降に追加されたISBNのみを取得
- **キャッシュ機能**: 取得した書籍データを30日間キャッシュ
- **スロットリング**: APIリクエスト間に適切な待機時間を設定
- **バックオフ**: 失敗時は指数バックオフで再試行
- **チャンク処理**: 大量データを小分けにして処理
- **実行頻度の最適化**: 週3回の実行と月1回の全更新

## 技術スタック

- Python 3.x
- GitHub Actions
- GitHub Pages

## 使用方法

RSSフィードは以下のURLで公開されています：
`https://[ユーザー名].github.io/shinsho-isbn-get/feed.xml`

## 設定

`config.yaml` ファイルで以下の設定をカスタマイズできます：

```yaml
api:
  base_wait_time: 0.5      # APIリクエスト間の待機時間（秒）
  max_wait_time: 8.0       # 最大待機時間（秒）
  
cache:
  books_max_age_days: 30   # 書籍キャッシュの有効期間（日）

processing:
  chunk_size: 100          # 一度に処理するISBN数
```

## インストールと実行

```bash
# リポジトリをクローン
git clone https://github.com/[ユーザー名]/shinsho-isbn-get.git
cd shinsho-isbn-get

# 依存関係のインストール
pip install -r requirements.txt

# 初期実行
bash scripts/init.sh

# 手動実行（オプション）
python scripts/main.py
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。 