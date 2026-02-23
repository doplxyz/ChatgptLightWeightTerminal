#!/bin/bash
# ChatGPT LightWeight Terminal (CLWT) - 初期環境セットアップスクリプト

# WORKDIR is the directory where this script resides
WORKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "システム: CLWTの初期環境セットアップを開始します。"

# 1. 必要なサブフォルダの作成
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
echo "システム: python ChatgptLightWeightTerminal.py を実行して起動してください。"
echo "========================================================"
