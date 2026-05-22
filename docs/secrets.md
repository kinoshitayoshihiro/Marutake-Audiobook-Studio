# API キーと認証情報

このリポジトリには API キー、OAuth クライアント JSON、アクセストークンを保存しません。

## 旧 2tb スクリプト

次のスクリプトは API キーを環境変数から読み込みます。

- `2tb/batch_analyze.py`
- `2tb/batch_analyze_resume.py`
- `2tb/batch_analyze_resume_v2.py`
- `2tb/import google.py`
- `2tb/tools/analyze_yamamoto_works.py`

実行前に必要なキーをシェルへ設定してください。

```bash
export YOUTUBE_API_KEY="..."
export GEMINI_API_KEY="..."
```

`2tb/tools/analyze_yamamoto_works.py` は `GEMINI_API_KEY` のみ使います。

## 漏えい時

公開リポジトリ、ログ、共有ファイルへキーを出した場合は、コードから削除するだけでは不十分です。

1. Google Cloud Console で該当キーを無効化または削除する
2. 必要な場合は新しいキーを作成する
3. API 制限とアプリケーション制限を設定する
4. Git 履歴に残った認証情報の扱いを確認する

`.gitignore` は `.env`、`client_secret.json`、`token.json` を除外します。キーをコードや Markdown に貼り付けないでください。
