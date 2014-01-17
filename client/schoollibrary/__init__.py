# -*- coding: utf-8 -*-

# Client for a schoollibrary-server.
# Copyright (c) 2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have receicved a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

__author__ = "Niklas Fiekas"
__copyright__ = "Copyright 2013, Niklas Fiekas"
__license__ = "GPL3+"
__version__ = "0.0.1"
__email__ = "niklas.fiekas@tu-clausthal.de"
__status__ = "Development"

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtNetwork import *

import json

import book
import user
import util

class Application(QApplication):
    """The main application class of the schoollibrary client."""

    def __init__(self, argv):
        super(Application, self).__init__(argv)

        # Instanciate services.
        self.settings = QSettings("Schoollibrary")
        self.network = QNetworkAccessManager(self)
        self.login = LoginDialog(self)
        self.users = user.UserListModel(self)
        self.books = book.BookTableModel(self)

    def exec_(self):
        # Login.
        if not self.login.exec_():
            return 0

        # Load data.
        self.users.reload()
        self.books.reload()

        view = QListView()
        view.setModel(self.users)
        view.show()

        # Open the main window and run the event loop.
        mainWindow = MainWindow(self)
        mainWindow.show()
        return super(Application, self).exec_()

class MainWindow(QMainWindow):
    """The main window."""

    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app

        self.setWindowTitle("Schulbibliothek")

        self.initUi()
        self.initActions()
        self.initMenu()
        self.initToolBar()

        # Restore geometry.
        self.restoreGeometry(self.app.settings.value("MainWindowGeometry"))

    def initUi(self):
        """Creates the central tab widget."""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.allBooksTable = QTableView()
        self.allBooksTable.setModel(self.app.books)
        self.allBooksTable.titleAndDescriptionDelegate = util.TitleAndDescriptionDelegate()
        self.allBooksTable.setItemDelegateForColumn(0, self.allBooksTable.titleAndDescriptionDelegate)
        self.allBooksTable.model().modelReset.connect(self.onBooksReset)
        self.tabs.addTab(self.allBooksTable, u"Alle Bücher")

    def onBooksReset(self):
        self.allBooksTable.resizeColumnsToContents()
        self.allBooksTable.setColumnWidth(0, 400)
        self.allBooksTable.resizeRowsToContents()

    def initActions(self):
        """Creates actions."""
        style = self.style()

        self.refreshAction = QAction("Daten aktualisieren", self)
        self.refreshAction.setShortcut("F5")
        self.refreshAction.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.refreshAction.triggered.connect(self.onRefreshAction)

        self.aboutAction = QAction(u"Über ...", self)
        self.aboutAction.setShortcut("F1")
        self.aboutAction.triggered.connect(self.onAboutAction)

        self.aboutQtAction = QAction(u"Über Qt ...", self)
        self.aboutQtAction.triggered.connect(self.onAboutQtAction)

        self.quitAction = QAction("Beenden", self)
        self.quitAction.setShortcut("Ctrl+C")
        self.quitAction.triggered.connect(self.close)

        self.addBookAction = QAction(u"Buch hinzufügen", self)
        self.addBookAction.setShortcut("Ctrl+N")
        self.addBookAction.setIcon(QIcon("data/address_book_add_32.png"))
        self.addBookAction.triggered.connect(self.onAddBookAction)

    def initMenu(self):
        """Creates the main menu."""
        mainMenu = self.menuBar().addMenu("Bibliothek")
        mainMenu.addAction(self.refreshAction)
        mainMenu.addSeparator()
        mainMenu.addAction(self.aboutAction)
        mainMenu.addAction(self.aboutQtAction)
        mainMenu.addSeparator()
        mainMenu.addAction(self.quitAction)

        bookMenu = self.menuBar().addMenu(u"Bücher")
        bookMenu.addAction(self.addBookAction)

    def initToolBar(self):
        """Creates the toolbar."""
        toolBar = self.addToolBar("Test")
        toolBar.addAction(self.addBookAction)
        toolBar.addSeparator()
        toolBar.addAction(self.refreshAction)

    def onRefreshAction(self):
        """Handles the refresh action."""
        self.app.users.reload()
        self.app.books.reload()

    def onAboutAction(self):
        """Handles the about action."""
        QMessageBox.about(self, u"Schoollibrary %s" % __version__,
            "<h1>Schoollibrary %s</h1>%s &lt;<a href=\"mailto:%s\">%s</a>&gt;" % (__version__, __author__, __email__, __email__))

    def onAboutQtAction(self):
        """Handles the about Qt action."""
        QMessageBox.aboutQt(self, u"Schoollibrary %s" % __version__)

    def onAddBookAction(self):
        """Handles the add book action."""
        dialog = book.BookDialog(self.app, None, self)
        dialog.show()

    def closeEvent(self, event):
        """Saves the geometry when the window is closed."""
        self.app.settings.setValue("MainWindowGeometry", self.saveGeometry())
        return super(MainWindow, self).closeEvent(event)

class LoginDialog(QDialog):
    """The login dialog."""

    def __init__(self, app, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.app = app
        self.app.network.finished.connect(self.onNetworkRequestFinished)

        self.setWindowTitle("Schulbibliothek Login")

        grid = QGridLayout()

        grid.addWidget(QLabel("Verbindung:"), 0, 0)
        row = QHBoxLayout()
        self.schemaBox = QComboBox()
        self.schemaBox.addItem("http")
        self.schemaBox.addItem("https")
        self.schemaBox.setCurrentIndex(0 if self.app.settings.value("ApiScheme", "http") else 1)
        row.addWidget(self.schemaBox)
        row.addWidget(QLabel("://"))
        self.hostBox = QLineEdit()
        self.hostBox.setText(self.app.settings.value("ApiHost", "localhost"))
        row.addWidget(self.hostBox)
        self.portBox = QSpinBox()
        self.portBox.setMinimum(1)
        self.portBox.setMaximum(65535)
        self.portBox.setValue(int(self.app.settings.value("ApiPort", 5000)))
        row.addWidget(QLabel(":"))
        row.addWidget(self.portBox)
        grid.addLayout(row, 0, 1)

        grid.addWidget(QLabel("Benutzername:"), 3, 0)
        self.userNameBox = QLineEdit()
        self.userNameBox.setText(self.app.settings.value("ApiUserName", ""))
        grid.addWidget(self.userNameBox, 3, 1)

        grid.addWidget(QLabel("Passwort:"), 4, 0)
        self.passwordBox = QLineEdit()
        self.passwordBox.setEchoMode(QLineEdit.Password)
        grid.addWidget(self.passwordBox, 4, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.onAccept)
        grid.addWidget(self.buttons, 5, 0, 1, 2)

        self.setLayout(grid)

    def getUrl(self, path=None):
        """Gets a URL with the settings chosen in the dialog."""
        url = QUrl()
        url.setScheme(self.schemaBox.itemText(self.schemaBox.currentIndex()))
        url.setHost(self.hostBox.text())
        url.setPort(self.portBox.value())
        url.setUserName(self.userNameBox.text())
        url.setPassword(self.passwordBox.text())

        if path:
            url.setPath(path)

        return url

    def onAccept(self):
        """Sends a login request to the service."""
        url = self.getUrl("/")

        if not url.isValid():
            QMessageBox.warning(self, self.windowTitle(), "Invalid URL: %s" % url.toString(QUrl.RemovePassword))
            return

        self.buttons.setEnabled(False)

        request = QNetworkRequest(url)
        self.app.network.get(request)

    def onNetworkRequestFinished(self, reply):
        """Handles responses to the login request."""
        # Ensure the reply is meant for this dialog.
        if reply.request().url().path() != "/":
            return
        else:
            self.buttons.setEnabled(True)

        # Check for network errors.
        if reply.error() != QNetworkReply.NoError:
            QMessageBox.warning(self, self.windowTitle(), reply.errorString())
            return

        # Check for HTTP errors.
        staus = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if staus != 200:
            QMessageBox.warning(self, self.windowTitle(), "HTTP Status Code: %d" % status)
            return

        # Ensure the response is structured as expected.
        try:
            user = json.loads(unicode(reply.readAll()))
            self.csrf = user["_csrf"]
            self.groups = user["groups"]
        except:
            QMessageBox.warning(self, self.windowTitle(), "Host scheint keine Bibliothek zu sein.")
            return

        # Finish dialog.
        if self.isVisible():
            self.app.settings.setValue("ApiScheme", "http" if self.schemaBox.currentIndex() == 0 else "https")
            self.app.settings.setValue("ApiHost", self.hostBox.text())
            self.app.settings.setValue("ApiPort", self.portBox.value())
            self.app.settings.setValue("ApiUserName", self.userNameBox.text())
            self.accept()
