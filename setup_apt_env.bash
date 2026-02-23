#!/bin/bash
# Akutsu Proxy Terminal (APT) - 初期環境セットアップスクリプト (Task 1〜6統合)

WORKDIR="/home/dop/workdir/006_pythonweb"

echo "システム: APTの初期環境セットアップを開始します。"

# 1. ワークディレクトリと必要なサブフォルダの作成
mkdir -p "$WORKDIR"
cd "$WORKDIR" || { echo "エラー: ディレクトリに移動できません。"; exit 1; }
mkdir -p applog/session tmp1 log1

# 2. Python仮想環境(venv)の作成
if [ ! -d "venv" ]; then
    echo "システム: Python仮想環境(venv)を作成しています..."
    python3 -m venv venv
else
    echo "システム: 仮想環境(venv)は既に存在します。"
fi

# 3. 仮想環境の有効化
source venv/bin/activate

# 4. 必要なライブラリのインストール
echo "システム: pipを最新にし、PyQt6 と Playwright をインストールしています..."
pip install --upgrade pip
pip install PyQt6 playwright

# 5. Playwrightのブラウザ(Chromium)インストール
echo "システム: Playwright用のブラウザエンジンをダウンロードしています..."
playwright install chromium

echo "========================================================"
echo "システム: セットアップが完全に終了しました。"
echo "システム: 以降は Task 007o などのPython起動スクリプトをそのまま実行可能です。"
echo "========================================================"
