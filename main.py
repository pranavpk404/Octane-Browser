from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from browser_core import (
    MAX_BOOKMARKS,
    MAX_HISTORY,
    add_page,
    load_page_list,
    load_search_engine,
    normalize_address,
    save_page_list,
    save_search_engine,
)

try:
    from PyQt5.QtCore import QUrl, QSize
    from PyQt5.QtGui import QFont, QIcon
    from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QLineEdit, QMainWindow, QMenu, QStatusBar, QTabWidget, QToolBar
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError as error:  # pragma: no cover - exercised when the desktop runtime is missing
    raise SystemExit("Octane needs PyQt5 and PyQtWebEngine. Install them with: python -m pip install PyQt5 PyQtWebEngine") from error

BASE_DIR = Path(__file__).resolve().parent
SEARCH_ENGINE_FILE = BASE_DIR / "search_engine.txt"
HISTORY_FILE = BASE_DIR / "history.json"
BOOKMARKS_FILE = BASE_DIR / "bookmarks.json"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.search_engine = load_search_engine(SEARCH_ENGINE_FILE)
        self.history = load_page_list(HISTORY_FILE, MAX_HISTORY)
        self.bookmarks = load_page_list(BOOKMARKS_FILE, MAX_BOOKMARKS)
        self.setWindowTitle("Octane Browser")
        self.setWindowIcon(QIcon(str(BASE_DIR / "images" / "icon.png")))
        self.resize(1280, 820)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabBarDoubleClicked.connect(self.open_new_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.navtb = QToolBar("Navigation")
        self.navtb.setMovable(False)
        self.navtb.setIconSize(QSize(22, 22))
        self.addToolBar(self.navtb)

        self.back_btn = self._action("back.png", "Back", "Alt+Left", lambda: self.current_browser().back())
        self.next_btn = self._action("forward.png", "Forward", "Alt+Right", lambda: self.current_browser().forward())
        self.reload_btn = self._action("reload.png", "Reload", "Ctrl+R", lambda: self.current_browser().reload())
        self.home_btn = self._action("home.png", "Home", "Ctrl+H", self.navigate_home)
        self.new_tab_btn = self._action("new-tab.png", "New tab", "Ctrl+T", self.open_new_tab)
        self.close_tab_btn = self._action("close-window.png", "Close tab", "Ctrl+W", self.close_current_tab)

        self.urlbar = QLineEdit()
        font = QFont()
        font.setPointSize(11)
        self.urlbar.setFont(font)
        self.urlbar.setClearButtonEnabled(True)
        self.urlbar.setPlaceholderText("Search or enter an address")
        self.urlbar.setStatusTip("Enter a URL or search phrase")
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        self.urlbar.addAction(self._icon("reload.png"), QLineEdit.TrailingPosition).triggered.connect(self.navigate_to_url)
        self.navtb.addWidget(self.urlbar)
        focus_url = QAction("Focus address field", self)
        focus_url.setShortcut("Ctrl+L")
        focus_url.triggered.connect(self.focus_urlbar)
        self.addAction(focus_url)

        self._build_search_menu()
        self._build_library_menu()
        self.add_new_tab(QUrl(self.search_engine), "New tab")

    def _icon(self, name: str) -> QIcon:
        return QIcon(str(BASE_DIR / "images" / name))

    def _action(self, icon: str, label: str, shortcut: str, callback) -> QAction:
        action = QAction(self._icon(icon), label, self)
        action.setShortcut(shortcut)
        action.setToolTip(label)
        action.triggered.connect(callback)
        self.navtb.addAction(action)
        return action

    def _build_search_menu(self) -> None:
        menu = self.menuBar().addMenu("Search engine")
        group = QActionGroup(self)
        group.setExclusive(True)
        engines = {
            "DuckDuckGo": "https://duckduckgo.com/",
            "Google": "https://www.google.com/",
            "Bing": "https://www.bing.com/",
        }
        for name, homepage in engines.items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(homepage == self.search_engine)
            action.triggered.connect(lambda _checked, url=homepage: self.change_search_engine(url))
            group.addAction(action)
            menu.addAction(action)

    def _build_library_menu(self) -> None:
        menu = self.menuBar().addMenu("Library")
        bookmark = QAction("Bookmark this page", self)
        bookmark.setShortcut("Ctrl+D")
        bookmark.triggered.connect(self.bookmark_current_page)
        menu.addAction(bookmark)
        menu.addSeparator()
        self.bookmarks_menu = QMenu("Bookmarks", self)
        self.history_menu = QMenu("History", self)
        menu.addMenu(self.bookmarks_menu)
        menu.addMenu(self.history_menu)
        menu.addSeparator()
        clear = QAction("Clear history", self)
        clear.triggered.connect(self.clear_history)
        menu.addAction(clear)
        menu.aboutToShow.connect(self.refresh_library_menus)

    def current_browser(self) -> QWebEngineView | None:
        browser = self.tabs.currentWidget()
        return browser if isinstance(browser, QWebEngineView) else None

    def add_new_tab(self, qurl: QUrl | None = None, label: str = "New tab") -> None:
        browser = QWebEngineView()
        browser.setUrl(qurl or QUrl(self.search_engine))
        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)
        browser.urlChanged.connect(lambda url, view=browser: self.update_urlbar(url, view))
        browser.titleChanged.connect(lambda title, view=browser: self.update_tab_title(view, title))
        browser.loadStarted.connect(lambda view=browser: self.status.showMessage(f"Loading {view.url().toString()}…"))
        browser.loadFinished.connect(lambda ok, view=browser: self.handle_load_finished(view, ok))

    def open_new_tab(self, _index=None) -> None:
        self.add_new_tab(QUrl(self.search_engine), "New tab")

    def current_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        browser = self.current_browser()
        if browser is not None:
            self.update_urlbar(browser.url(), browser)
            self.update_tab_title(browser, browser.title())

    def close_current_tab(self, index=None) -> None:
        if isinstance(index, bool) or index is None:
            index = self.tabs.currentIndex()
        if index < 0:
            return
        if self.tabs.count() <= 1:
            browser = self.current_browser()
            if browser is not None:
                browser.setUrl(QUrl(self.search_engine))
                self.tabs.setTabText(index, "New tab")
            return
        browser = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if browser is not None:
            browser.deleteLater()

    def change_search_engine(self, homepage: str) -> None:
        self.search_engine = save_search_engine(SEARCH_ENGINE_FILE, homepage)
        self.status.showMessage(f"Search engine changed to {self.search_engine}", 3000)
        self.navigate_home()

    def navigate_home(self) -> None:
        browser = self.current_browser()
        if browser is not None:
            browser.setUrl(QUrl(self.search_engine))

    def focus_urlbar(self) -> None:
        self.urlbar.setFocus()
        self.urlbar.selectAll()

    def navigate_to_url(self) -> None:
        browser = self.current_browser()
        if browser is None:
            return
        target = normalize_address(self.urlbar.text(), self.search_engine)
        browser.setUrl(QUrl(target))

    def update_urlbar(self, url: QUrl, browser: QWebEngineView | None = None) -> None:
        if browser is not self.current_browser():
            return
        self.urlbar.setText(url.toString())
        self.urlbar.setCursorPosition(0)

    def update_tab_title(self, browser: QWebEngineView, title: str) -> None:
        index = self.tabs.indexOf(browser)
        if index < 0:
            return
        label = " ".join(title.split())[:60] or "New tab"
        self.tabs.setTabText(index, label)
        if browser is self.current_browser():
            self.setWindowTitle(f"{label} — Octane Browser")

    def handle_load_finished(self, browser: QWebEngineView, ok: bool) -> None:
        if ok:
            self.record_history(browser)
        if browser is not self.current_browser():
            return
        self.status.showMessage("Page loaded" if ok else "Page could not be loaded", 3000)

    def record_history(self, browser: QWebEngineView) -> None:
        url = browser.url().toString()
        title = browser.title() or url
        self.history = add_page(self.history, url, title, datetime.now(timezone.utc).isoformat(), MAX_HISTORY)
        save_page_list(HISTORY_FILE, self.history, MAX_HISTORY)

    def bookmark_current_page(self) -> None:
        browser = self.current_browser()
        if browser is None:
            return
        url = browser.url().toString()
        title = browser.title() or url
        self.bookmarks = add_page(self.bookmarks, url, title, datetime.now(timezone.utc).isoformat(), MAX_BOOKMARKS)
        save_page_list(BOOKMARKS_FILE, self.bookmarks, MAX_BOOKMARKS)
        self.status.showMessage("Bookmark saved", 2500)

    def refresh_library_menus(self) -> None:
        self.bookmarks_menu.clear()
        if not self.bookmarks:
            empty = QAction("No bookmarks yet", self)
            empty.setEnabled(False)
            self.bookmarks_menu.addAction(empty)
        else:
            for item in self.bookmarks:
                action = QAction(item["title"], self)
                action.setToolTip(item["url"])
                action.triggered.connect(lambda _checked, url=item["url"]: self.open_url(url))
                self.bookmarks_menu.addAction(action)

        self.history_menu.clear()
        if not self.history:
            empty = QAction("No history yet", self)
            empty.setEnabled(False)
            self.history_menu.addAction(empty)
        else:
            for item in self.history[:25]:
                action = QAction(item["title"], self)
                action.setToolTip(item["url"])
                action.triggered.connect(lambda _checked, url=item["url"]: self.open_url(url))
                self.history_menu.addAction(action)

    def open_url(self, url: str) -> None:
        browser = self.current_browser()
        if browser is not None:
            browser.setUrl(QUrl(url))

    def clear_history(self) -> None:
        self.history = []
        save_page_list(HISTORY_FILE, self.history, MAX_HISTORY)
        self.status.showMessage("History cleared", 2500)

    def closeEvent(self, event) -> None:
        save_search_engine(SEARCH_ENGINE_FILE, self.search_engine)
        save_page_list(HISTORY_FILE, self.history, MAX_HISTORY)
        save_page_list(BOOKMARKS_FILE, self.bookmarks, MAX_BOOKMARKS)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Octane Browser")
    app.setOrganizationName("Octane")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
