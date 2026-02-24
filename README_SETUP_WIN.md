# ChatGPT LightWeight Terminal (CLWT) Windowsセットアップガイド

このガイドでは、Windows環境でChatGPT LightWeight Terminal (CLWT)をセットアップする手順を説明します。

## 1. 前提条件: Pythonのインストール

CLWTを実行するには、Python 3.xが必要です。以下の手順でインストールしてください。

1.  Python公式サイト (https://www.python.org/downloads/) から最新のPythonインストーラーをダウンロードします。
2.  インストーラーを実行します。
3.  **重要:** インストール画面の下部にある **"Add Python to PATH" (Pythonを環境変数PATHに追加する)** のチェックボックスを必ずオンにしてください。
    - これを行わないと、`setup_clwt_env.bat` が正常に動作しません。
4.  "Install Now" をクリックしてインストールを完了します。

## 2. セットアップスクリプトの実行

1.  エクスプローラーでCLWTのフォルダを開きます。
2.  `setup_clwt_env.bat` をダブルクリックして実行します。
3.  コマンドプロンプトが開き、自動的に以下の処理が行われます。
    - 必要なフォルダの作成 (`applog`, `tmp1`, `log1`)
    - Python仮想環境 (`venv`) の作成
    - 必要なライブラリ (`PyQt6`, `playwright`) のインストール
    - Playwright用ブラウザ (Chromium) のインストール
4.  "System: Setup complete." と表示されたらセットアップは完了です。何かキーを押してウィンドウを閉じてください。

## 3. アプリケーションの起動

セットアップ完了後、以下の手順でアプリケーションを起動します。

1.  コマンドプロンプト（またはPowerShell）を開き、CLWTのディレクトリに移動します。
2.  以下のコマンドを実行します。

```batch
call venv\Scripts\activate
python ChatgptLightWeightTerminal.py
```

または、以下の内容で `run_clwt.bat` というファイルを作成し、ダブルクリックで起動することも可能です。

```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
start pythonw ChatgptLightWeightTerminal.py
```

## トラブルシューティング

### "Pythonが見つかりません" (Error: Python is not installed...) エラーが出る場合
Pythonがインストールされていないか、PATHに追加されていません。
手順1の「**"Add Python to PATH" (Pythonを環境変数PATHに追加する)**」を確認して、Pythonを再インストールしてください。
インストール後にPCの再起動が必要な場合があります。

### セットアップが途中で止まる場合
インターネット接続を確認してください。ライブラリやブラウザのダウンロードに時間がかかる場合があります。
