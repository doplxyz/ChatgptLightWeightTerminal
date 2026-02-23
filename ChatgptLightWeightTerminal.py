import sys
import os
import queue
import logging
import re
import json
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QPushButton, QComboBox, QLabel, QSplitter, QPlainTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QSize
from PyQt6.QtGui import QPainter, QColor
from playwright.sync_api import sync_playwright

WORKDIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(WORKDIR, "applog", "session")
TMP_DIR = os.path.join(WORKDIR, "tmp1")
LOG_DIR = os.path.join(WORKDIR, "log1")

for d in [SESSION_DIR, TMP_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

log_filename = os.path.join(LOG_DIR, f"clwt_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(file_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler(sys.stdout))

def cleanup_old_files():
    logger.info("システム: 古いキャッシュとログファイルのクリーンアップを実行します...")
    now = time.time()
    expiry_time = now - 604800
    deleted_count = 0
    for directory in [TMP_DIR, LOG_DIR]:
        if not os.path.exists(directory): continue
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                if os.stat(filepath).st_mtime < expiry_time:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except: pass

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth(0)

    def lineNumberAreaWidth(self):
        digits = 1
        max_count = max(1, self.blockCount())
        while max_count >= 10:
            max_count /= 10
            digits += 1
        space = 5 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#2d2d2d"))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                state = block.userState()
                if state == 1:
                    color = QColor("#aaffaa") # ユーザ (薄い緑)
                elif state == 2:
                    color = QColor("#aaaaff") # AI (薄い青)
                else:
                    color = QColor("#888888")

                painter.setPen(color)
                painter.drawText(0, top, self.lineNumberArea.width() - 2, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1


class PlaywrightWorker(QThread):
    chat_signal = pyqtSignal(dict)
    stream_start_signal = pyqtSignal(dict)
    stream_signal = pyqtSignal(str)
    sys_signal = pyqtSignal(dict)
    history_list_signal = pyqtSignal(list)

    def __init__(self, msg_queue):
        super().__init__()
        self.msg_queue = msg_queue
        self.is_running = True
        self.timeout_ms = 300000
        self.current_chat_id = "new_chat"

    def emit_sys_line(self, text):
        logger.info(text)
        self.sys_signal.emit({"type": "line", "text": text})

    def emit_sys_append(self, text):
        self.sys_signal.emit({"type": "append", "text": text})

    def get_chat_id(self, url):
        match = re.search(r'/c/([a-zA-Z0-9-]+)', url)
        return match.group(1) if match else "new_chat"

    def compress_text(self, text):
        if not text: return ""
        return re.sub(r'\n{3,}', '\n\n', text.strip())

    def send_chat_data(self, data_list):
        for item in data_list:
            role = item.get('role', 'unknown')
            content = self.compress_text(item.get('text', ''))
            if role == 'user':
                self.chat_signal.emit({"role": "user", "text": f"\nユーザ:\n{content}\n"})
            elif role == 'assistant':
                self.chat_signal.emit({"role": "ai", "text": f"\nAI:\n{content}\n"})
            else:
                self.chat_signal.emit({"role": "system", "text": f"\n不明:\n{content}\n"})

    def fetch_sidebar_history(self, page):
        self.emit_sys_line("システム: 最新の履歴リストの同期を試みます")
        js_code = """
        () => {
            const links = document.querySelectorAll('nav a[href^="/c/"]');
            return Array.from(links).slice(0, 50).map(a => {
                let title = a.innerText.split('\\n')[0].trim();
                return {title: title, url: a.href};
            });
        }
        """
        history_data = []
        for attempt in range(20):
            if not self.is_running: return
            try:
                history_data = page.evaluate(js_code)
                if history_data and len(history_data) > 0:
                    self.emit_sys_append(" 完了\n")
                    break
            except Exception as e: pass
            self.emit_sys_append(".")
            page.wait_for_timeout(3000)

        if history_data:
            self.history_list_signal.emit(history_data)
            self.emit_sys_line(f"システム: {len(history_data)}件の履歴リストを同期しました。")
        else:
            self.emit_sys_line("システムエラー: 規定回数リトライしましたが、履歴リストを取得できませんでした。")

    def scrape_current_chat(self, page):
        # 実DOMからの直接抽出と退避による、改行・言語の絶対保持ロジック
        js_code = """
        () => {
            const articles = document.querySelectorAll('article[data-testid^="conversation-turn"]');

            const container = document.createElement('div');
            container.style.position = 'absolute';
            container.style.left = '-9999px';
            container.style.width = '1000px';
            container.style.whiteSpace = 'pre-wrap';
            document.body.appendChild(container);

            const results = Array.from(articles).map(a => {
                const roleEl = a.querySelector('[data-message-author-role]');
                const role = roleEl ? roleEl.getAttribute('data-message-author-role') : 'unknown';

                // ★超重要：画面にマウント済みの実要素(a)からコードを直接抽出し退避させる★
                const originalPres = Array.from(a.querySelectorAll('pre'));
                const preTexts = originalPres.map(pre => {
                    let lang = '';
                    const codeEl = pre.querySelector('code');

                    if (codeEl && codeEl.className) {
                        const match = codeEl.className.match(/language-([a-zA-Z0-9_\\-]+)/);
                        if (match) lang = match[1].toUpperCase();
                    }
                    if (!lang) {
                        const headerSpan = pre.querySelector('.flex.items-center span, .bg-token-main-surface-secondary span');
                        if (headerSpan && headerSpan.textContent) {
                            lang = headerSpan.textContent.trim().toUpperCase();
                        }
                    }

                    // 実画面のinnerTextを使うため、ブラウザが計算した完璧な改行が保持される
                    let text = pre.innerText || pre.textContent;

                    // Copy codeボタン等の混入ノイズを消去
                    text = text.replace(/^(Copy code|コピー)\\s*/i, '').trim();
                    if (lang && lang !== 'CODE' && lang !== 'TEXT' && lang !== 'PLAINTEXT') {
                        const langRegex = new RegExp('^' + lang + '\\\\s*', 'i');
                        text = text.replace(langRegex, '').trim();
                        lang = '## ' + lang + '\\n';
                    } else {
                        lang = '';
                    }

                    return '\\n========コードブロック箇所ここから========\\n' + lang + text + '\\n========コードブロック箇所ここまで========\\n';
                });

                const targetEl = roleEl ? roleEl : a;
                const clone = targetEl.cloneNode(true);

                // clone側のpreをプレースホルダに置き換える
                clone.querySelectorAll('pre').forEach((pre, idx) => {
                    const marker = document.createElement('div');
                    marker.innerText = `___CODE_BLOCK_${idx}___`;
                    pre.replaceWith(marker);
                });

                // リスト改行の保護
                clone.querySelectorAll('ol').forEach(ol => {
                    let i = 1;
                    Array.from(ol.children).forEach(child => {
                        if (child.tagName === 'LI') {
                            const p = child.querySelector('p');
                            (p ? p : child).prepend(document.createTextNode(i + '. '));
                            i++;
                        }
                    });
                });
                clone.querySelectorAll('ul').forEach(ul => {
                    Array.from(ul.children).forEach(child => {
                        if (child.tagName === 'LI') {
                            const p = child.querySelector('p');
                            (p ? p : child).prepend(document.createTextNode('・ '));
                        }
                    });
                });

                const wrapperDiv = document.createElement('div');
                wrapperDiv.appendChild(clone);
                container.appendChild(wrapperDiv);

                return { role: role, element: wrapperDiv, codes: preTexts };
            });

            // コンテナで計算された本文テキストと、退避させた完璧なコードテキストを合体
            const finalData = results.map(item => {
                let text = item.element.innerText;
                item.codes.forEach((codeStr, idx) => {
                    text = text.replace(`___CODE_BLOCK_${idx}___`, codeStr);
                });
                return { role: item.role, text: text };
            });

            document.body.removeChild(container);
            return finalData;
        }
        """
        try:
            return page.evaluate(js_code)
        except Exception as e:
            logger.debug(f"JS Bulk Evaluate Error: {e}")
            return []

    def sync_history_fast(self, page, url, force_web=False):
        self.current_chat_id = self.get_chat_id(url)
        cache_path = os.path.join(TMP_DIR, f"{self.current_chat_id}.json")

        cached_data = []
        if not force_web and os.path.exists(cache_path) and self.current_chat_id != "new_chat":
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                if cached_data:
                    self.emit_sys_line("システム: ローカルキャッシュを展開しました。")
                    self.chat_signal.emit({"role": "system", "text": "----------------------------------------\n【履歴同期】"})
                    self.send_chat_data(cached_data)
                    self.chat_signal.emit({"role": "system", "text": "----------------------------------------\n"})
            except Exception as e:
                logger.error(f"Cache Load Error: {e}")

        if self.current_chat_id != "new_chat":
            self.emit_sys_line("システム: ブラウザ側のDOM同期を待機中 (取得漏れ防止のため下へスクロール中...)")
            dom_ready = False
            last_count = -1
            stable_polls = 0

            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except: pass

            for attempt in range(40):
                if not self.is_running: return
                try:
                    count = page.locator('article[data-testid^="conversation-turn"]').count()
                    if count > 0:
                        self.emit_sys_append(f" [検知:{count}件]")
                        if count == last_count:
                            stable_polls += 1
                            if stable_polls >= 4:
                                self.emit_sys_append(" 安定化確認\n")
                                dom_ready = True
                                break
                        else:
                            stable_polls = 0
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        last_count = count
                    else:
                        self.emit_sys_append(".")
                except Exception as e:
                    if "closed" in str(e).lower() or "target" in str(e).lower():
                        raise e
                page.wait_for_timeout(1000)

            if not dom_ready:
                self.emit_sys_append(" タイムアウト\n")
                self.emit_sys_line("システム: DOM同期がタイムアウトしました。取得できた状態までで進行します。")

        try:
            self.emit_sys_line("システム: コンテキストを超高速一括解析中...")
            current_data = self.scrape_current_chat(page)

            if not cached_data:
                if current_data:
                    if not force_web:
                        self.chat_signal.emit({"role": "system", "text": "----------------------------------------\n【履歴同期 (Web)】"})
                    self.send_chat_data(current_data)
                    if not force_web:
                        self.chat_signal.emit({"role": "system", "text": "----------------------------------------\n"})
            else:
                diff_len = len(current_data) - len(cached_data)
                if diff_len > 0:
                    new_items = current_data[-diff_len:]
                    self.emit_sys_line(f"システム: Web側との差分({diff_len}件)を追記します。")
                    self.send_chat_data(new_items)

            if self.current_chat_id != "new_chat":
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(current_data, f, ensure_ascii=False, indent=2)

            self.emit_sys_line("システム: コンテキスト完全同期完了。")

        except Exception as e:
            self.emit_sys_line(f"システムエラー: 高速同期に失敗しました。詳細: {e}")
            raise e

    def run(self):
        while self.is_running:
            browser_context = None
            try:
                with sync_playwright() as p:
                    self.emit_sys_line("システム: バックグラウンドブラウザを起動中...")
                    browser_context = p.chromium.launch_persistent_context(
                        user_data_dir=SESSION_DIR,
                        headless=False,
                        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                        no_viewport=True
                    )

                    page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
                    page.set_default_navigation_timeout(self.timeout_ms)
                    page.set_default_timeout(self.timeout_ms)

                    self.emit_sys_line("システム: ChatGPTへ接続しています...")
                    page.goto("https://chatgpt.com/", wait_until="domcontentloaded")

                    self.emit_sys_line("システム: 初期アクセス完了。")
                    self.fetch_sidebar_history(page)
                    self.sync_history_fast(page, page.url)

                    while self.is_running:
                        try:
                            msg = self.msg_queue.get(timeout=1)
                            if not isinstance(msg, dict): continue
                            msg_type = msg.get("type")

                            if msg_type == "QUIT":
                                break

                            elif msg_type == "FETCH_SIDEBAR":
                                self.fetch_sidebar_history(page)

                            elif msg_type == "RELOAD_DELETE":
                                url = msg.get("url")
                                if not url: url = "https://chatgpt.com/"
                                self.emit_sys_line(f"システム: キャッシュを削除してリロードを実行中... ({url})")
                                chat_id = self.get_chat_id(url)
                                path = os.path.join(TMP_DIR, f"{chat_id}.json")
                                if os.path.exists(path):
                                    try: os.remove(path)
                                    except: pass
                                page.reload(wait_until="domcontentloaded")
                                self.sync_history_fast(page, url, force_web=True)

                            elif msg_type == "RELOAD_SIMPLE":
                                url = msg.get("url")
                                if not url: url = "https://chatgpt.com/"
                                self.emit_sys_line(f"システム: 単純リロードを実行中... ({url})")
                                page.reload(wait_until="domcontentloaded")
                                self.sync_history_fast(page, url, force_web=True)

                            elif msg_type == "CLEAR_CACHE":
                                self.emit_sys_line("システム: tmp1内の全キャッシュをクリア中...")
                                count = 0
                                for filename in os.listdir(TMP_DIR):
                                    filepath = os.path.join(TMP_DIR, filename)
                                    if os.path.isfile(filepath):
                                        try:
                                            os.remove(filepath)
                                            count += 1
                                        except: pass
                                self.emit_sys_line(f"システム: キャッシュクリア完了。{count}件削除しました。")
                                self.fetch_sidebar_history(page)

                            elif msg_type == "NAVIGATE":
                                url = msg.get("url")
                                if not url: url = "https://chatgpt.com/"
                                self.emit_sys_line(f"システム: 指定URLへ移動中... ({url})")
                                page.goto(url, wait_until="domcontentloaded")
                                self.sync_history_fast(page, url)

                            elif msg_type == "SEND":
                                text = msg.get("text")
                                self.emit_sys_line("システム: メッセージ送信中...")

                                page.fill('#prompt-textarea', text)
                                page.wait_for_timeout(500)
                                page.keyboard.press('Enter')

                                self.emit_sys_line("システム: AIの応答を待機中")
                                page.wait_for_timeout(3000)

                                last_text = ""
                                stable_count = 0
                                self.stream_start_signal.emit({"role": "ai", "text": "\nAI:\n"})

                                for _ in range(600):
                                    if not self.is_running: break
                                    page.wait_for_timeout(1000)
                                    self.emit_sys_append(".")
                                    assistant_messages = page.locator('[data-message-author-role="assistant"]').all()
                                    if not assistant_messages: continue

                                    try:
                                        raw_current_text = assistant_messages[-1].inner_text(timeout=1000)
                                    except: continue

                                    current_text = self.compress_text(raw_current_text)

                                    if current_text != last_text:
                                        diff = current_text[len(last_text):]
                                        if diff:
                                            self.stream_signal.emit(diff)
                                        last_text = current_text
                                        stable_count = 0
                                    else:
                                        if current_text: stable_count += 1

                                    if stable_count >= 10:
                                        self.stream_signal.emit("\n\n")
                                        self.emit_sys_append(" 完了\n")
                                        self.emit_sys_line("システム: 回答完了。最新のキャッシュを構築します...")
                                        if self.current_chat_id != "new_chat":
                                            updated_data = self.scrape_current_chat(page)
                                            cache_path = os.path.join(TMP_DIR, f"{self.current_chat_id}.json")
                                            with open(cache_path, "w", encoding="utf-8") as f:
                                                json.dump(updated_data, f, ensure_ascii=False, indent=2)
                                        break

                        except queue.Empty:
                            continue
                        except Exception as inner_e:
                            if "closed" in str(inner_e).lower() or "target" in str(inner_e).lower():
                                raise inner_e
                            else:
                                self.emit_sys_line(f"システムエラー(ループ内): {inner_e}")

                    if not self.is_running:
                        self.emit_sys_line("システム: 終了処理を実行中。プロセスの完全終了を待機しています...")
                        if browser_context: browser_context.close()
                        break

            except Exception as e:
                if not self.is_running: break
                self.emit_sys_line(f"【警告】ブラウザとの接続が切断されました。({e})")
                self.emit_sys_line("システム: 5秒後にブラウザの再起動を試みます...")
                time.sleep(5)


class CustomInputArea(QTextEdit):
    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui
        self.mode = "notepad"

    def set_mode(self, mode):
        self.mode = mode

    def keyPressEvent(self, event):
        if self.mode == "browser":
            if event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.parent_ui.handle_send()
            else:
                super().keyPressEvent(event)
        else:
            if event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                return
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)

class ChatGPTLightWeightTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatGPT LightWeight Terminal (CLWT)")
        self.resize(900, 850)

        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: sans-serif; font-size: 11pt; }
            QPlainTextEdit, QTextEdit { background-color: #1e1e1e; border: 1px solid #444; padding: 5px; }
            QTextEdit#input_box { background-color: #2d2d2d; color: #ffffff; font-size: 12pt; }
            QPushButton { background-color: #007acc; color: white; font-weight: bold; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: #0098ff; }
            QComboBox { background-color: #2d2d2d; color: #ffffff; padding: 5px; border: 1px solid #444; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #2d2d2d; color: #ffffff; selection-background-color: #007acc; }
            QSplitter::handle { background-color: #444444; height: 3px; }
        """)

        main_layout = QVBoxLayout(self)

        nav_layout = QHBoxLayout()

        self.cache_clear_btn = QPushButton("全キャッシュクリア")
        self.cache_clear_btn.clicked.connect(self.handle_cache_clear)
        nav_layout.addWidget(self.cache_clear_btn)

        self.reload_del_btn = QPushButton("削除リロード")
        self.reload_del_btn.clicked.connect(self.handle_reload_delete)
        nav_layout.addWidget(self.reload_del_btn)

        self.reload_simple_btn = QPushButton("単純リロード")
        self.reload_simple_btn.clicked.connect(self.handle_reload_simple)
        nav_layout.addWidget(self.reload_simple_btn)

        self.fetch_btn = QPushButton("画面左履歴取込")
        self.fetch_btn.clicked.connect(self.handle_fetch_sidebar)
        nav_layout.addWidget(self.fetch_btn)

        self.history_combo = QComboBox()
        self.history_combo.setEditable(True)
        self.history_combo.setPlaceholderText("履歴リストから選ぶか、URLを直接入力")
        self.history_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        nav_layout.addWidget(self.history_combo, stretch=1)

        self.nav_btn = QPushButton("移動")
        self.nav_btn.clicked.connect(self.handle_nav)
        nav_layout.addWidget(self.nav_btn)

        main_layout.addLayout(nav_layout)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self.splitter, stretch=1)

        self.chat_log = CodeEditor()
        self.chat_log.setReadOnly(True)
        self.splitter.addWidget(self.chat_log)

        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 5, 0, 5)

        # Task 007o: ツールバーレイアウトの最適化（左寄せ）
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        mode_label = QLabel("入力モード:")
        mode_label.setStyleSheet("color: #d4d4d4; font-size: 10pt;")
        toolbar_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["ボタンで送信、ENTER改行のみ", "ENTER送信、SHIFT+ENTER改行"])
        self.mode_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.mode_combo.currentIndexChanged.connect(self.handle_mode_change)
        self.mode_combo.setCurrentIndex(0)
        toolbar_layout.addWidget(self.mode_combo)

        toolbar_layout.addSpacing(20)

        warning_label = QLabel("ファイルはブラウザ側に添付してください。")
        warning_label.setStyleSheet("color: #ffaa00; font-size: 10pt; font-weight: bold;")
        toolbar_layout.addWidget(warning_label)

        toolbar_layout.addStretch(1)
        input_layout.addLayout(toolbar_layout)

        hbox = QHBoxLayout()
        self.input_box = CustomInputArea(self)
        self.input_box.setObjectName("input_box")
        hbox.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("送信")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self.handle_send)
        hbox.addWidget(self.send_btn)

        input_layout.addLayout(hbox)
        self.splitter.addWidget(input_widget)

        sys_log_widget = QWidget()
        self.sys_log_layout = QVBoxLayout(sys_log_widget)
        self.sys_log_layout.setContentsMargins(0, 0, 0, 0)

        self.sys_toggle_btn = QPushButton("▲ システムログを隠す")
        self.sys_toggle_btn.setStyleSheet("background-color: #333333; text-align: left; padding-left: 10px;")
        self.sys_toggle_btn.clicked.connect(self.toggle_sys_log)
        self.sys_log_layout.addWidget(self.sys_toggle_btn)

        self.sys_log = QTextEdit()
        self.sys_log.setReadOnly(True)
        self.sys_log.setStyleSheet("background-color: #0d0d0d; color: #00ff00; font-family: monospace; font-size: 10pt;")
        self.sys_log.show()
        self.sys_log_layout.addWidget(self.sys_log)
        self.splitter.addWidget(sys_log_widget)

        self.splitter.setSizes([500, 150, 100])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)
        sys_log_widget.setMinimumHeight(35)

        cleanup_old_files()

        self.msg_queue = queue.Queue()
        self.worker = PlaywrightWorker(self.msg_queue)
        self.worker.chat_signal.connect(self.append_chat_log)
        self.worker.stream_start_signal.connect(self.append_chat_stream_start)
        self.worker.stream_signal.connect(self.append_chat_stream)
        self.worker.sys_signal.connect(self.append_sys_log)
        self.worker.history_list_signal.connect(self.update_history_combo)
        self.worker.start()

    def handle_mode_change(self, index):
        if index == 1:
            self.input_box.set_mode("browser")
        else:
            self.input_box.set_mode("notepad")

    def toggle_sys_log(self):
        sizes = self.splitter.sizes()
        if self.sys_log.isVisible():
            self.sys_log.hide()
            self.sys_toggle_btn.setText("▼ システムログを表示")
            self.splitter.setSizes([sizes[0] + sizes[2] - 35, sizes[1], 35])
        else:
            self.sys_log.show()
            self.sys_toggle_btn.setText("▲ システムログを隠す")
            self.splitter.setSizes([sizes[0] - 65, sizes[1], sizes[2] + 65])

    def handle_cache_clear(self):
        self.chat_log.clear()
        self.msg_queue.put({"type": "CLEAR_CACHE"})

    def handle_reload_delete(self):
        url = self.history_combo.currentData()
        if not url: url = self.history_combo.currentText().strip()
        if url:
            self.chat_log.clear()
            self.msg_queue.put({"type": "RELOAD_DELETE", "url": url})

    def handle_reload_simple(self):
        url = self.history_combo.currentData()
        if not url: url = self.history_combo.currentText().strip()
        if url:
            self.chat_log.clear()
            self.msg_queue.put({"type": "RELOAD_SIMPLE", "url": url})

    def handle_fetch_sidebar(self):
        self.history_combo.clear()
        self.history_combo.addItem("【新規チャットを作成】", "https://chatgpt.com/")
        self.msg_queue.put({"type": "FETCH_SIDEBAR"})

    def update_history_combo(self, history_data):
        self.history_combo.clear()
        self.history_combo.addItem("【新規チャットを作成】", "https://chatgpt.com/")
        for item in history_data:
            self.history_combo.addItem(item["title"], item["url"])

    def handle_nav(self):
        url = self.history_combo.currentData()
        if not url: url = self.history_combo.currentText().strip()

        if url:
            self.chat_log.clear()
            self.msg_queue.put({"type": "NAVIGATE", "url": url})

    def handle_send(self):
        text = self.input_box.toPlainText().strip()
        if not text: return
        self.input_box.clear()
        self.append_chat_log({"role": "user", "text": f"ユーザ:\n{text}\n"})
        self.msg_queue.put({"type": "SEND", "text": text})

    def append_chat_log(self, data):
        role_str = data.get("role", "system")
        text = data.get("text", "")
        if role_str == "user": state = 1
        elif role_str == "ai": state = 2
        else: state = 0

        cursor = self.chat_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        start_block = cursor.blockNumber()
        cursor.insertText(text + "\n")
        end_block = self.chat_log.document().blockCount()

        doc = self.chat_log.document()
        for i in range(start_block, end_block):
            doc.findBlockByNumber(i).setUserState(state)

        self.chat_log.setTextCursor(cursor)
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def append_chat_stream_start(self, data):
        self.append_chat_log(data)

    def append_chat_stream(self, text):
        state = 2 # AI
        cursor = self.chat_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        start_block = cursor.blockNumber()
        cursor.insertText(text)
        end_block = self.chat_log.document().blockCount()

        doc = self.chat_log.document()
        for i in range(start_block, end_block):
            doc.findBlockByNumber(i).setUserState(state)

        self.chat_log.setTextCursor(cursor)
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def append_sys_log(self, data):
        msg_type = data.get("type")
        text = data.get("text")

        cursor = self.sys_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        if msg_type == "line":
            if self.sys_log.toPlainText() and not self.sys_log.toPlainText().endswith("\n"):
                cursor.insertText("\n")
            cursor.insertText(text)
        elif msg_type == "append":
            cursor.insertText(text)

        self.sys_log.setTextCursor(cursor)
        self.sys_log.verticalScrollBar().setValue(self.sys_log.verticalScrollBar().maximum())

    def closeEvent(self, event):
        self.msg_queue.put({"type": "QUIT"})
        self.worker.is_running = False

        if not self.worker.wait(3000):
            logger.warning("システム: ワーカースレッドの応答がありません。強制終了(terminate)を実行します。")
            self.worker.terminate()
            self.worker.wait()

        logger.info("システム: プロセスは正常に終了しました。")
        event.accept()

if __name__ == '__main__':
    if sys.platform != 'win32':
        os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    cleanup_old_files()

    app = QApplication(sys.argv)
    ui = ChatGPTLightWeightTerminal()
    ui.show()
    sys.exit(app.exec())
