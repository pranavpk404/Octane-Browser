import os
import sys

from PyQt5.QtCore import QSize, QUrl
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QStatusBar, QToolBar, QAction, QLineEdit, \
    QApplication

with open("search_engine.txt", "r")as f:
    SEARCH_ENGINE = f.readline()
    f.close()


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        # FONT FOR URL BAR
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)

        # TABS
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.open_new_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        # STATUS BAR
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # NAVIGATION BAR
        navtb = QToolBar("Navigation")
        navtb.setIconSize(QSize(25, 25))
        self.addToolBar(navtb)

        back_btn = QAction(QIcon(os.path.join('images', 'back.png')), "Back", self)
        back_btn.setStatusTip("Back to previous page")
        back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        navtb.addAction(back_btn)

        next_btn = QAction(QIcon(os.path.join('images', 'forward.png')), "Forward", self)
        next_btn.setStatusTip("Forward to next page")
        next_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addAction(next_btn)

        reload_btn = QAction(QIcon(os.path.join('images', 'reload.png')), "Reload", self)
        reload_btn.setStatusTip("Reload page")
        reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addAction(reload_btn)

        home_btn = QAction(QIcon(os.path.join('images', 'home.png')), "Go To Home", self)
        home_btn.setStatusTip("Go To Home")
        home_btn.triggered.connect(self.navigate_home)
        navtb.addAction(home_btn)

        new_tab_btn = QAction(QIcon(os.path.join('images', 'new-tab.png')), "Add New Tab", self)
        new_tab_btn.setStatusTip("Add New Tab")
        new_tab_btn.triggered.connect(self.open_new_tab)
        navtb.addAction(new_tab_btn)

        close_tab_btn = QAction(QIcon(os.path.join('images', 'close-window.png')), "Close Tab", self)
        close_tab_btn.setStatusTip("Close Tab")
        close_tab_btn.triggered.connect(self.close_current_tab)
        navtb.addAction(close_tab_btn)

        # SHORTCUT KEYS FOR ABOVE BUTTONS
        back_btn.setShortcut('Alt+Left')
        next_btn.setShortcut('Alt+Right')
        new_tab_btn.setShortcut('Ctrl+T')
        reload_btn.setShortcut('Ctrl+R')
        home_btn.setShortcut('Ctrl+H')
        close_tab_btn.setShortcut('Ctrl+W')

        # MENU BAR
        search_menu = self.menuBar().addMenu("Change Search Engine")

        def set_search_engine(img, name, command):
            menu = QAction(QIcon(os.path.join('images', img + '.png')), name, self)
            menu.setStatusTip("Set Search Engine")
            menu.triggered.connect(command)
            search_menu.addAction(menu)

        def change_home_page(link):
            self.add_new_tab(QUrl(link), 'Homepage')
            with open("search_engine.txt", "w") as f:
                f.write(link)
                f.close()
            print(link)

        def google_change():
            change_home_page("https://www.google.com/")

        def duckduckgo_change():
            change_home_page("https://www.duckduckgo.com/")

        def bing_change():
            change_home_page("https://www.bing.com/")

        set_search_engine("bing", "Bing", bing_change)
        set_search_engine("google", "Google", google_change)
        set_search_engine("duckduckgo", "Duckduckgo", duckduckgo_change)

        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        self.urlbar.setStatusTip("Please Give Only URL Here")
        self.urlbar.setFont(font)
        navtb.addWidget(self.urlbar)

        self.add_new_tab(QUrl(SEARCH_ENGINE), 'Homepage')

        self.show()

        self.setWindowTitle("Octane")
        self.setWindowIcon(QIcon(os.path.join('images', 'icon.png')))

    def add_new_tab(self, qurl=None, label="Blank"):

        if qurl is None:
            qurl = QUrl('')

        browser = QWebEngineView()
        browser.setUrl(qurl)
        i = self.tabs.addTab(browser, label)

        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser:
                                   self.update_urlbar(qurl, browser))

        browser.loadFinished.connect(lambda _, i=i, browser=browser:
                                     self.tabs.setTabText(i, browser.page().title()))

    def open_new_tab(self, i):
        self.add_new_tab(QUrl(SEARCH_ENGINE), 'Homepage')

    def current_tab_changed(self, i):
        qurl = self.tabs.currentWidget().url()
        self.update_urlbar(qurl, self.tabs.currentWidget())
        self.update_title(self.tabs.currentWidget())

    def close_current_tab(self, i):
        if self.tabs.count() < 2:
            return

        self.tabs.removeTab(i)

    def update_title(self, browser):
        if browser != self.tabs.currentWidget():
            return

        title = self.tabs.currentWidget().page().title()
        self.setWindowTitle("%s - Octane" % title)

    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl(SEARCH_ENGINE))

    def navigate_to_url(self):

        q = QUrl(self.urlbar.text())
        if q.scheme() == "":
            q.setScheme("http")

        self.tabs.currentWidget().setUrl(q)

    def update_urlbar(self, q, browser=None):
        if browser != self.tabs.currentWidget():
            return
        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)


app = QApplication(sys.argv)
app.setApplicationName("Octane")

window = MainWindow()

app.exec_()