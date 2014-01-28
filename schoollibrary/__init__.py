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

import sys
import json
import uuid

import book
import user
import util
import busyindicator
import network
import os


class Application(QApplication):
    """The main application class of the schoollibrary client."""

    def __init__(self, argv):
        super(Application, self).__init__(argv)

        # Instanciate services.
        self.settings = QSettings("Schoollibrary")
        self.network = network.NetworkService(self)
        self.login = LoginDialog(self)
        self.users = user.UserListModel(self)
        self.books = book.BookTableModel(self)

    def data(self, path=""):
        """Gets the path to the data directory."""
        if os.path.exists("usr/share/schoollibrary"):
            return "usr/share/schoollibrary/" + path
        else:
            return "/usr/share/schoollibrary/" + path

    def exec_(self):
        """Runs the application."""
        # Login.
        if not self.login.exec_():
            return 0

        # Open the main window and run the event loop.
        mainWindow = MainWindow(self)
        mainWindow.show()
        return super(Application, self).exec_()


class MainWindow(QMainWindow):
    """The main window."""

    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app
        self.app.network.finished.connect(self.onNetworkRequestFinished)

        self.setWindowTitle("Schulbibliothek")

        # Create the user interface.
        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initTabs())
        self.layoutStack.addWidget(self.initBusyIndicator())
        centralWidget = QWidget()
        centralWidget.setLayout(self.layoutStack)
        self.setCentralWidget(centralWidget)

        # Initialize menu and toolbar actions.
        self.initActions()
        self.initToolBar()
        self.initMenu()

        # Restore geometry.
        self.restoreGeometry(self.app.settings.value("MainWindowGeometry"))
        self.restoreState(self.app.settings.value("MainWindowState"))

        # Load data.
        self.ticket = None
        self.onRefreshAction()

    def initTabs(self):
        """Initializes the main tabs."""
        self.tabs = QTabWidget()

        self.allBooksTable = QTableView()
        self.allBooksTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.allBooksTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.allBooksTable.customContextMenuRequested.connect(self.onAllBooksCustomContextMenuRequested)
        self.allBooksTable.setModel(self.app.books.getProxy())
        self.allBooksTable.titleAndDescriptionDelegate = util.TitleAndDescriptionDelegate()
        self.allBooksTable.setItemDelegateForColumn(1, self.allBooksTable.titleAndDescriptionDelegate)
        self.allBooksTable.model().modelReset.connect(self.onAllBooksReset)
        self.allBooksTable.setSortingEnabled(True)
        self.addTab(u"Alle Bücher", self.allBooksTable)

        self.lentBooksTable = QTableView()
        self.lentBooksTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lentBooksTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lentBooksTable.customContextMenuRequested.connect(self.onLentBooksCustomContextMenuRequested)
        self.lentBooksTable.setModel(self.app.books.getLentProxy())
        self.lentBooksTable.titleAndDescriptionDelegate = util.TitleAndDescriptionDelegate()
        self.lentBooksTable.setItemDelegateForColumn(1, self.lentBooksTable.titleAndDescriptionDelegate)
        self.lentBooksTable.model().modelReset.connect(self.onLentBooksReset)
        self.lentBooksTable.setSortingEnabled(True)
        self.addTab(u"Ausgeliehene Bücher", self.lentBooksTable)

        layout = QHBoxLayout()
        layout.addWidget(self.tabs)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def addTab(self, title, widget):
        """Creates a tab in the main tab widget."""
        page = QWidget()
        layout = QHBoxLayout()

        page.setLayout(layout)
        layout.addWidget(widget)
        return self.tabs.addTab(page, title)

    def initBusyIndicator(self):
        """Creates a busy indicator."""
        self.busyIndicator = busyindicator.BusyIndicator()
        return self.busyIndicator

    def showBusyIndicator(self, show):
        """Shows or hides the busy indicator."""
        if show:
            self.layoutStack.setCurrentIndex(1)
            self.busyIndicator.setEnabled(True)
        else:
            self.layoutStack.setCurrentIndex(0)
            self.busyIndicator.setEnabled(False)

    def onAllBooksReset(self):
        """Resizes items in the all-books-table when the model is reset."""
        self.allBooksTable.resizeColumnsToContents()
        self.allBooksTable.setColumnWidth(1, 400)
        self.allBooksTable.resizeRowsToContents()

    def onLentBooksReset(self):
        """Resizes items in the lend-books-table when the model is reset."""
        self.lentBooksTable.resizeColumnsToContents()
        self.lentBooksTable.setColumnWidth(1, 400)
        self.lentBooksTable.resizeRowsToContents()

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
        self.addBookAction.setIcon(QIcon(self.app.data("add-book.png")))
        self.addBookAction.triggered.connect(self.onAddBookAction)
        self.addBookAction.setEnabled(self.app.login.libraryModify)

        self.lendingAction = QAction(u"Ausleihe", self)
        self.lendingAction.setIcon(QIcon(self.app.data("basket.png")))
        self.lendingAction.triggered.connect(self.onLendingAction)
        self.lendingAction.setEnabled(self.app.login.libraryLend)

        self.editBookAction = QAction("Buch bearbeiten", self)
        self.editBookAction.triggered.connect(self.onEditBookAction)
        self.editBookAction.setEnabled(self.app.login.libraryModify)

        self.deleteBookAction = QAction(u"Buch löschen", self)
        self.deleteBookAction.setShortcut("Del")
        self.deleteBookAction.triggered.connect(self.onDeleteBookAction)
        self.deleteBookAction.setEnabled(self.app.login.libraryDelete)

    def initToolBar(self):
        """Creates the toolbar."""
        self.toolBar = self.addToolBar("Test")
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolBar.setObjectName("MainWindowToolBar")
        self.toolBar.setWindowTitle("Toolbar")

        self.toolBar.addAction(self.lendingAction)
        self.toolBar.addAction(self.addBookAction)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.refreshAction)

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
        bookMenu.addSeparator()
        bookMenu.addAction(self.lendingAction)
        bookMenu.addSeparator()
        bookMenu.addAction(self.editBookAction)
        bookMenu.addAction(self.deleteBookAction)

        self.viewMenu = self.menuBar().addMenu("Ansicht")
        self.viewMenu.addAction(self.toolBar.toggleViewAction())

        self.contextMenu = QMenu()
        self.contextMenu.addAction(self.lendingAction)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.editBookAction)
        self.contextMenu.addAction(self.deleteBookAction)

    def onRefreshAction(self):
        """Handles the refresh action."""
        self.showBusyIndicator(True)
        self.app.users.reload()
        self.ticket = self.app.books.reload()

    def onAboutAction(self):
        """Handles the about action."""
        QMessageBox.about(self, u"Schoollibrary %s" % __version__,
            "<h1>Schoollibrary %s</h1>%s &lt;<a href=\"mailto:%s\">%s</a>&gt;" % (__version__, __author__, __email__, __email__))

    def onAboutQtAction(self):
        """Handles the about Qt action."""
        QMessageBox.aboutQt(self, u"Schoollibrary %s" % __version__)

    def onAddBookAction(self):
        """Handles the add book action."""
        book.BookDialog.open(self.app, None, self)

    def onLendingAction(self):
        """Handles the lending action."""
        for currentBook in self.selectedBooks():
            book.LendingDialog.open(self.app, currentBook, self)

    def onEditBookAction(self):
        """Handles the edit book action."""
        for currentBook in self.selectedBooks():
            book.BookDialog.open(self.app, currentBook, self)

    def onDeleteBookAction(self):
        """Handles the delete book action."""
        books = self.selectedBooks()

        buttons = QMessageBox.Yes | QMessageBox.No
        if len(books) > 1:
            buttons = buttons | QMessageBox.Cancel

        for currentBook in books:
            result = QMessageBox.question(self, u"Buch löschen",
                u"Möchten Sie das Buch »%s« wirklich löschen?" % currentBook.title,
                buttons)

            if result == QMessageBox.Yes:
                book.BookDialog.ensureClosed(currentBook)
                book.LendingDialog.ensureClosed(currentBook)
                self.app.books.delete(currentBook)
            elif result == QMessageBox.Cancel:
                return

    def selectedBooks(self):
        """Gets the currently selected books of the currently activa tab."""
        if self.tabs.currentIndex() == 0:
            table = self.allBooksTable
        elif self.tabs.currentIndex() == 1:
            table = self.lentBooksTable
        model = table.model()
        return [model.indexToBook(index) for index in table.selectedIndexes() if index.column() == 0]

    def onAllBooksCustomContextMenuRequested(self, position):
        """Opens the context menu for all books."""
        if self.selectedBooks():
            self.contextMenu.exec_(self.allBooksTable.viewport().mapToGlobal(position))

    def onLentBooksCustomContextMenuRequested(self, position):
        """Opens the context menu for lent books."""
        if self.selectedBooks():
            self.contextMenu.exec_(self.lentBooksTable.viewport().mapToGlobal(position))

    def onNetworkRequestFinished(self, reply):
        """Called when a network request is finished."""
        if reply.request().attribute(network.Ticket) == self.ticket:
            self.ticket = None
            self.showBusyIndicator(False)

    def closeEvent(self, event):
        """Saves the geometry when the window is closed."""
        self.app.settings.setValue("MainWindowGeometry", self.saveGeometry())
        self.app.settings.setValue("MainWindowState", self.saveState())
        return super(MainWindow, self).closeEvent(event)


class LoginDialog(QDialog):
    """The login dialog."""

    def __init__(self, app, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.app = app
        self.app.network.finished.connect(self.onNetworkRequestFinished)

        self.setWindowTitle("Schulbibliothek Login")

        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initForm())
        self.layoutStack.addWidget(self.initProgressSpinner())
        self.setLayout(self.layoutStack)

        self.ticket = None

    def initForm(self):
        """Creates the login form."""
        form = QFormLayout()

        self.urlBox = QLineEdit()
        self.urlBox.setText(self.app.settings.value("ApiUrl", "http://localhost:5000/"))
        form.addRow("URL:", self.urlBox)

        self.userNameBox = QLineEdit()
        self.userNameBox.setText(self.app.settings.value("ApiUserName", ""))
        form.addRow("Benutzername:", self.userNameBox)

        self.passwordBox = QLineEdit()
        self.passwordBox.setEchoMode(QLineEdit.Password)
        self.passwordBox.setText(self.app.settings.value("ApiPassword", ""))
        form.addRow("Passwort:", self.passwordBox)

        self.savePasswordBox = QCheckBox("Passwort speichern")
        self.savePasswordBox.setChecked(self.app.settings.value("ApiPassword", "") != "")
        form.addRow(self.savePasswordBox)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttons.button(QDialogButtonBox.Ok).setAutoDefault(True)
        self.buttons.button(QDialogButtonBox.Ok).setDefault(True)
        self.buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.onAccept)
        form.addRow(self.buttons)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def initProgressSpinner(self):
        """Creates a busy indicator with a cancel button."""
        layout = QVBoxLayout()

        self.busyIndicator = busyindicator.BusyIndicator()
        layout.addWidget(self.busyIndicator)

        row = QHBoxLayout()
        row.addStretch(1)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.onCancel)
        self.cancelButton.setAutoDefault(False)
        row.addWidget(self.cancelButton)
        row.addStretch(1)
        layout.addLayout(row)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def getUrl(self, path=None):
        """Gets a URL with the settings chosen in the dialog."""
        url = QUrl(self.urlBox.text())
        url.setUserName(self.userNameBox.text())
        url.setPassword(self.passwordBox.text())

        basepath = url.path()
        if basepath.endswith("/"):
            basepath = basepath[:-1]

        if path:
            url.setPath(basepath + path)

        return url

    def onAccept(self):
        """Sends a login request to the service."""
        url = self.getUrl("/")

        if not url.isValid():
            QMessageBox.warning(self, self.windowTitle(), "Invalid URL: %s" % url.toString(QUrl.RemovePassword))
            return

        self.layoutStack.setCurrentIndex(1)
        self.busyIndicator.setEnabled(True)

        self.ticket = self.app.network.http("GET", QNetworkRequest(url))

    def onCancel(self):
        self.layoutStack.setCurrentIndex(0)
        self.busyIndicator.setEnabled(False)
        self.ticket = None

    def onNetworkRequestFinished(self, reply):
        """Handles responses to the login request."""
        # Ensure the reply is meant for this dialog.
        if reply.request().attribute(network.Ticket) != self.ticket:
            return
        else:
            self.busyIndicator.setEnabled(False)
            self.layoutStack.setCurrentIndex(0)

        # Check for an authentication error.
        if reply.error() == QNetworkReply.AuthenticationRequiredError:
            self.passwordBox.setText("")
            self.passwordBox.setFocus()
            QMessageBox.warning(self, self.windowTitle(), "Login fehlgeschlagen.")
            return

        # Check for network errors.
        if reply.error() != QNetworkReply.NoError:
            QMessageBox.warning(self, self.windowTitle(), self.censorError(reply.errorString()))
            return

        # Check for HTTP errors.
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status != 200:
            QMessageBox.warning(self, self.windowTitle(), "HTTP Status Code: %d" % status)
            return

        # Ensure the response is structured as expected.
        try:
            user = json.loads(unicode(reply.readAll()))
            self.csrf = user["_csrf"]
            self.groups = user["groups"]
            self.libraryAdmin = "library_admin" in self.groups
            self.libraryModify = self.libraryAdmin or "library_modify" in self.groups
            self.libraryDelete = self.libraryAdmin or "library_delete" in self.groups
            self.libraryLend = self.libraryAdmin or "library_lend" in self.groups
        except:
            QMessageBox.warning(self, self.windowTitle(), "Host scheint keine Bibliothek zu sein.")
            return

        # Finish dialog.
        if self.isVisible():
            self.app.settings.setValue("ApiUrl", self.urlBox.text())
            self.app.settings.setValue("ApiUserName", self.userNameBox.text())
            if self.savePasswordBox.isChecked():
                self.app.settings.setValue("ApiPassword", self.passwordBox.text())
            else:
                self.app.settings.setValue("ApiPassword", "")
            self.accept()

    def censorError(self, error):
        """Censors the password in an error message."""
        password = self.passwordBox.text()
        return str(error).replace(password, "***")

    def sizeHint(self):
        """Make dialog a little wider than strictly nescessary."""
        size = super(LoginDialog, self).sizeHint()
        return QSize(size.width() + 150, size.height())


if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec_())
