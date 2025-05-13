# 新書RSS生成 - ローカルテスト

このドキュメントではローカル環境で新書RSS生成システムをテストする方法を説明します。

## 準備

1. 必要なパッケージのインストール:
   ```bash
   pip install -r requirements.txt
   ```

2. `output` ディレクトリの作成:
   ```bash
   mkdir -p output
   ```

## テスト実行方法

### 対話式スクリプトの実行 (推奨)

Windows:
```bash
local_test_en.bat  # 英語版（最も安定）
```

または

```bash
local_test_win.bat  # 日本語版（文字化けする場合は英語版を使用）
```

UNIX/Linux/macOS:
```bash
chmod +x local_test.sh  # 初回のみ
./local_test.sh
```

### コマンドラインからの実行

以下のコマンドを使用してテストを実行できます:

```bash
python scripts/local_test.py [オプション]
```

#### 主なオプション:

- `--sample`: サンプルモード（処理件数を制限）
- `--full-refresh`: 全データを再取得
- `--output-dir OUTPUT_DIR`: 出力ディレクトリを指定（デフォルト: ./output）
- `--cache-dir CACHE_DIR`: キャッシュディレクトリを指定（デフォルト: ./data）
- `--server`: ローカルWebサーバーを起動
- `--port PORT`: サーバーのポート番号を指定（デフォルト: 8000）
- `--browser`: 処理後にブラウザで開く
- `--no-save`: 処理データを保存しない
- `--use-existing`: 新規データがない場合に既存データを使用

### 実行例

1. サンプルモードでテスト:
   ```bash
   python scripts/local_test.py --sample --browser
   ```

2. ローカルサーバーを起動してブラウザで結果を確認:
   ```bash
   python scripts/local_test.py --server --browser
   ```

3. 完全更新モードでテスト:
   ```bash
   python scripts/local_test.py --full-refresh --browser
   ```

4. 既存データの表示（APIリクエストなし）:
   ```bash
   python scripts/local_test.py --use-existing --no-save --browser
   ```

## 出力ファイル

テスト実行後、以下のファイルが `output` ディレクトリに生成されます:

- `feed.xml`: RSSフィード
- `index.html`: HTML形式の新書一覧

## トラブルシューティング

- **サーバーモードが終了しない**: `Ctrl+C` を押して終了できます
- **ブラウザが自動で開かない**: 出力ディレクトリの `index.html` を手動でブラウザで開いてください
- **RSSリーダーでの確認**: お使いのRSSリーダーに `file:///パス/output/feed.xml` を登録してください
- **文字化けする場合**: Windows環境では `local_test_en.bat`（英語版）を使用してください
- **日本語入力の問題**: Windows環境で日本語入力に問題がある場合は、コマンドラインから直接実行してください

## 設定カスタマイズ

ローカルテストの設定は `config.yaml` ファイルで調整できます:

```yaml
api:
  base_wait_time: 0.5      # 待機時間を短く設定するとテストが早く完了
  
processing:
  sample_limit: 50         # サンプルモード時の処理件数を少なく設定
``` 