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

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtNetwork import *

import json
import uuid
import re

import indexed
import util
import busyindicator
import network

def normalize_isbn(isbn):
    isbn = isbn.replace("-", "").replace(" ", "").strip().upper()

    if not isbn:
        return isbn
    elif re.match(r"^([0-9]{9}X|[0-9]{10})$", isbn):
        checksum = 0

        for i in range(0, 9):
            checksum += (i + 1) * int(isbn[i])

        if isbn[9] == "X":
            checksum += 10 * 10
        else:
            checksum += 10 * int(isbn[9])

        if checksum % 11 == 0:
            return isbn
        else:
            raise ValueError("Invalid ISBN-10.")
    elif re.match(r"^([0-9]{13})$", isbn):
        factor = [ 1, 3 ]
        checksum = 0

        for i in range(0, 12):
            checksum += factor[i % 2] * int(isbn[i])

        if (int(isbn[12]) - ((10 - (checksum % 10)) % 10)) == 0:
            return isbn
        else:
            raise ValueError("Invalid ISBN-13.")
    else:
        raise ValueError("Invalid ISBN.")

class Book(object):
    """A book object."""

    def __init__(self):
        self.id = 0
        self.signature = ""
        self.location = ""
        self.title = ""
        self.authors = ""
        self.topic = ""
        self.volume = ""
        self.keywords = ""
        self.publisher = ""
        self.placeOfPublication = ""
        self.year = None
        self.isbn = ""
        self.edition = ""
        self.lendable = True
        self.lendingUser = None
        self.lendingSince = None
        self.lendingDays = None
        self.lent = False

class BookTableModel(QAbstractTableModel):
    """The book database."""

    def __init__(self, app):
        super(BookTableModel, self).__init__()
        self.app = app
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.cache = indexed.IndexedOrderedDict()

        self.bookPathPattern = re.compile(r"^\/books\/([0-9]+)\/$")

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or not self.hasIndex(row, column, parent):
            return QModelIndex()
        else:
            return self.createIndex(row, column, self.cache.values()[row])

    def rowCount(self, parent=QModelIndex()):
        return len(self.cache)

    def columnCount(self, parent=QModelIndex()):
        return 10

    def data(self, index, role=Qt.DisplayRole):
        book = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                lines = []
                if book.signature:
                    lines.append(book.signature)
                lines.append(str(book.id))
                if book.location:
                    lines.append(book.location)
                return "\n".join(lines)
            elif index.column() == 1:
                return book.title
            elif index.column() == 2:
                return book.topic
            elif index.column() == 3:
                return book.volume
            elif index.column() == 4:
                return book.publisher
            elif index.column() == 5:
                return book.placeOfPublication
            elif index.column() == 6:
                return book.year
            elif index.column() == 7:
                return book.keywords
            elif index.column() == 8:
                return book.isbn
            elif index.column() == 9:
                return book.edition
        elif role == Qt.UserRole:
            if index.column() == 0:
                return book.id
            else:
                return index.data(Qt.DisplayRole)
        elif role == util.TitleAndDescriptionDelegate.DescriptionRole:
            if index.column() == 1:
                return book.authors
        elif role == Qt.TextAlignmentRole:
            if index.column() in (0, 3, 6, 8):
                return Qt.AlignCenter
        elif role == Qt.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setPointSizeF(font.pointSize() * 0.8)
                return font
        elif role == Qt.BackgroundRole:
            if book.lent:
                # TODO: Highlight red if overdue.
                return QColor(100, 200, 100)
            elif not book.lendable:
                return QColor(230, 230, 230)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return "Label"
                if section == 1:
                    return "Buch"
                elif section == 2:
                    return "Thema"
                elif section == 3:
                    return "Band"
                elif section == 4:
                    return "Verlag"
                elif section == 5:
                    return "Erscheinungsort"
                elif section == 6:
                    return "Jahr"
                elif section == 7:
                    return u"Schlüsselwörter"
                elif section == 8:
                    return "ISBN"
                elif section == 9:
                    return "Auflage"

    def reload(self):
        request = QNetworkRequest(self.app.login.getUrl("/books/"))
        return self.app.network.http("GET", request)

    def delete(self, book):
        path = "/books/%d/" % book.id
        request = QNetworkRequest(self.app.login.getUrl(path))
        request.setRawHeader(QByteArray("X-CSRF-Token"), QByteArray(self.app.login.csrf))
        return self.app.network.http("DELETE", request)

    def onNetworkRequestFinished(self, reply):
        request = reply.request()

        if request.url().path() == "/books/" and request.attribute(network.HttpMethod) == "POST":
            # Book created.
            data = json.loads(unicode(reply.readAll()))
            book = self.bookFromData(data)

            assert not book.id in self.cache

            self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
            self.cache[book.id] = book
            self.endInsertRows()
        elif request.url().path() == "/books/" and request.attribute(network.HttpMethod) == "GET":
            # Book list reloaded.
            self.beginResetModel()
            self.cache.clear()

            for data in json.loads(unicode(reply.readAll())).values():
                book = self.bookFromData(data)
                self.cache[book.id] = book

            self.endResetModel()
        else:
            match = self.bookPathPattern.match(request.url().path())
            if match and request.attribute(network.HttpMethod) == "DELETE":
                # Book deleted.
                id = int(match.group(1))
                if id in self.cache:
                    row = self.cache.keys().index(id)
                    self.beginRemoveRows(QModelIndex(), row, row)
                    del self.cache[id]
                    self.endRemoveRows()
            elif match and request.attribute(network.HttpMethod) in ("GET", "PUT"):
                # Book changed or reloaded.
                data = json.loads(unicode(reply.readAll()))
                book = self.bookFromData(data)

                if book.id in self.cache:
                    bookIndex = self.indexFromBook(self.cache[book.id])
                    self.cache[book.id] = book
                    self.dataChanged.emit(bookIndex, self.index(bookIndex.row(), self.columnCount() - 1, QModelIndex()))
                else:
                    self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
                    self.cache[book.id] = book
                    self.endInsertRows()

    def bookFromData(self, data):
        book = Book()

        book.id = int(data["_id"])
        book.isbn = data["isbn"]
        book.title = data["title"]
        book.authors = data["authors"]
        book.volume = data["volume"]
        book.topic = data["topic"]
        book.keywords = data["keywords"]
        book.signature = data["signature"]
        book.location = data["location"]
        book.year = int(data["year"]) if data["year"] else None
        book.publisher = data["publisher"]
        book.placeOfPublication = data["placeOfPublication"]
        book.lendable = bool(data["lendable"])
        book.lent = bool(data["lent"])

        if book.lent:
            book.lendingUser = data["lending"]["user"]
            book.lendingSince = data["lending"]["since"]
            book.lendingDays = data["lending"]["days"]

        return book

    def indexFromBook(self, book):
        books = self.cache.viewvalues()
        if book in books:
            return self.createIndex(self.cache.keys().index(book.id), 0, book)
        else:
            return QModelIndex()

    def indexToBook(self, index):
        if not index.isValid():
            return None
        else:
            return index.internalPointer()

    def getProxy(self):
        proxy = BookTableSortFilterProxyModel()
        proxy.setSourceModel(self)
        return proxy

    def getLentProxy(self):
        proxy = self.getProxy()
        proxy.lentOnly = True
        return proxy

class BookTableSortFilterProxyModel(QSortFilterProxyModel):
    """Sorts and filters an underlying book table model."""

    def __init__(self):
        super(BookTableSortFilterProxyModel, self).__init__()
        self.setDynamicSortFilter(True)
        self.setSortRole(Qt.UserRole)

        self.lentOnly = False

    def indexToBook(self, index):
        """Gets the book associated with an index."""
        return self.sourceModel().indexToBook(self.mapToSource(index))

    def indexFromBook(self, book):
        """Gets the index associated with a book."""
        return self.mapFromSource(self.sourceModel().indexFromBook(book))

    def filterAcceptsRow(self, row, parent=QModelIndex()):
        """Checks if a book should be displayed."""
        if self.lentOnly:
            book = self.sourceModel().indexToBook(self.sourceModel().index(row, 0, parent))
            if not book.lent:
                return False

        return True

class BookDialog(QDialog):
    """A product editing dialog."""

    dialogs = dict()

    @classmethod
    def open(cls, app, book, parent):
        """Opens a new dialog or sets the focus to an existing one."""
        if book:
            if not book.id in cls.dialogs or not cls.dialogs[book.id].isVisible():
                cls.dialogs[book.id] = BookDialog(app, book, parent)
                cls.dialogs[book.id].show()
            else:
                cls.dialogs[book.id].activateWindow()
            return cls.dialogs[book.id]
        else:
            dialog = BookDialog(app, book, parent)
            dialog.show()
            return dialog

    @classmethod
    def ensureClosed(cls, book):
        if book.id in cls.dialogs:
            dialog = cls.dialogs[book.id]
            del cls.dialogs[book.id]

            if not dialog.close():
                cls.dialogs[book.id] = dialog

    def __init__(self, app, book, parent):
        super(BookDialog, self).__init__(parent)
        self.app = app
        self.book = book

        # Create a stack of the form and a busy indicator.
        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initForm())
        self.layoutStack.addWidget(self.initBusyIndicator())
        self.setLayout(self.layoutStack)

        # Initialize form values.
        self.initValues()

        # Handle network responses.
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.ticket = None

    def initForm(self):
        """Initializes the user interface."""
        form = QFormLayout()

        self.idBox = QLabel()
        form.addRow("ID:", self.idBox)

        self.isbnBox = QLineEdit()
        form.addRow("ISBN:", self.isbnBox)

        self.titleBox = QLineEdit()
        form.addRow("Titel:", self.titleBox)

        self.authorsBox = QLineEdit()
        form.addRow("Autoren:", self.authorsBox)

        self.volumeBox = QLineEdit()
        form.addRow("Band:", self.volumeBox)

        self.topicBox = QLineEdit()
        form.addRow("Thema:", self.topicBox)

        self.keywordsBox = QLineEdit()
        form.addRow(u"Schlüsselwörter", self.keywordsBox)

        self.signatureBox = QLineEdit()
        self.signatureBox.setMaxLength(50)
        form.addRow("Signatur:", self.signatureBox)

        self.locationBox = QLineEdit()
        form.addRow("Standort:", self.locationBox)

        self.yearBox = QLineEdit()
        form.addRow("Jahr:", self.yearBox)

        self.publisherBox = QLineEdit()
        form.addRow("Verlag:", self.publisherBox)

        self.placeOfPublicationBox = QLineEdit()
        form.addRow(u"Veröffentlichungsort:", self.placeOfPublicationBox)

        self.lendableBox = QCheckBox()
        form.addRow("Ausleihbar:", self.lendableBox)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.onSaveClicked)
        buttonBox.rejected.connect(self.close)
        buttonBox.button(QDialogButtonBox.Cancel).setAutoDefault(False)
        form.addRow(buttonBox)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def initValues(self):
        """Initialize the displayed values according to the book."""
        if self.book:
            self.setWindowTitle("Buch: %s" % self.book.title)
            self.idBox.setText(str(self.book.id))
        else:
            self.setWindowTitle("Neues Buch")
            self.idBox.setText("automatisch")
            self.book = Book()

        self.isbnBox.setText(self.book.isbn)
        self.titleBox.setText(self.book.title)
        self.authorsBox.setText(self.book.authors)
        self.volumeBox.setText(self.book.volume)
        self.topicBox.setText(self.book.topic)
        self.keywordsBox.setText(self.book.keywords)
        self.signatureBox.setText(self.book.signature)
        self.locationBox.setText(self.book.location)
        self.yearBox.setText(str(self.book.year) if self.book.year else "")
        self.publisherBox.setText(self.book.publisher)
        self.placeOfPublicationBox.setText(self.book.placeOfPublication)
        self.lendableBox.setChecked(self.book.lendable)

    def initBusyIndicator(self):
        """Initialize a busy indicator."""
        self.busyIndicator = busyindicator.BusyIndicator()
        return self.busyIndicator

    def showBusy(self, visible):
        """Shows or hides the busy indicator."""
        if visible:
            self.busyIndicator.setEnabled(True)
            self.layoutStack.setCurrentIndex(1)
        else:
            self.busyIndicator.setEnabled(False)
            self.layoutStack.setCurrentIndex(0)

    def isDirty(self):
        """Checks if anything has been changed and not saved."""
        if self.isbnBox.text() != self.book.isbn:
            return True

        if self.titleBox.text() != self.book.title:
            return True

        if self.authorsBox.text() != self.book.authors:
            return True

        if self.volumeBox.text() != self.book.volume:
            return True

        if self.topicBox.text() != self.book.topic:
            return True

        if self.keywordsBox.text() != self.book.keywords:
            return True

        if self.signatureBox.text() != self.book.signature:
            return True

        if self.locationBox.text() != self.book.location:
            return True

        if not self.book.year:
            if self.yearBox.text():
                return True
        else:
            if self.yearBox.text() != str(self.book.year):
                return True

        if self.publisherBox.text() != self.book.publisher:
            return True

        if self.placeOfPublicationBox.text() != self.book.placeOfPublication:
            return True

        if self.lendableBox.isChecked() != self.book.lendable:
            return True

        return False

    def save(self):
        """Validates and saves the current product."""
        try:
            isbn = normalize_isbn(self.isbnBox.text())
        except ValueError:
            QMessageBox.warning(self, self.windowTitle(), u"Ungültige ISBN.")
            return False

        title = self.titleBox.text().strip()
        if not title:
            QMessageBox.warning(self, self.windowTitle(), "Ein Titel ist erforderlich.")
            return False

        year = self.yearBox.text().strip()
        if year:
            try:
                year = int(year)
            except ValueError:
                QMessageBox.warning(self, self.windowTitle(), u"Ungültige Eingabe für das Veröffentlichungsjahr.")
                return False

            if year < 0 or year > 3000:
                QMessageBox.warning(self, self.windowTitle(), u"Jahr ist außerhalb das gültigen Bereichs.")
                return False
        else:
            year = None

        params = QUrl()
        params.addQueryItem("_csrf", self.app.login.csrf)
        params.addQueryItem("isbn", isbn)
        params.addQueryItem("title", title)
        params.addQueryItem("authors", self.authorsBox.text())
        params.addQueryItem("topic", self.topicBox.text())
        params.addQueryItem("keywords", self.keywordsBox.text())
        params.addQueryItem("signature", self.signatureBox.text())
        params.addQueryItem("location", self.locationBox.text())
        params.addQueryItem("year", str(year) if year else "")
        params.addQueryItem("publisher", self.publisherBox.text())
        params.addQueryItem("placeOfPublication", self.placeOfPublicationBox.text())
        params.addQueryItem("volume", self.volumeBox.text())
        params.addQueryItem("lendable", "true" if self.lendableBox.isChecked() else "false")

        if not self.book.id:
            request = QNetworkRequest(self.app.login.getUrl("/books/"))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
            self.ticket = self.app.network.http("POST", request, params.encodedQuery())
        else:
            path = "/books/%d/" % self.book.id
            request = QNetworkRequest(self.app.login.getUrl(path))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
            self.ticket = self.app.network.http("PUT", request, params.encodedQuery())

        return True

    def onNetworkRequestFinished(self, reply):
        """Handles responses."""
        # Only handle requests that concern this dialog.
        if self.ticket != reply.request().attribute(network.Ticket):
            return

        self.ticket = None
        self.showBusy(False)

        # Check for network errors.
        if reply.error() != QNetworkReply.NoError:
            QMessageBox.warning(self, self.windowTitle(), reply.errorString())
            return

        # Check for HTTP errors.
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status != 200:
            QMessageBox.warning(self, self.windowTitle(), "HTTP Status Code: %d" % status)
            return

        # Accepted.
        self.accept()

    def onSaveClicked(self):
        """Handles a click on the save button."""
        if self.save():
            self.showBusy(True)

    def closeEvent(self, event):
        """Prevents the window from beeing closed if dirty."""
        # Saving in progress.
        if self.ticket:
            event.ignore()
            return

        # Close immediately if it should not be open.
        if self.book.id and not self.book.id in BookDialog.dialogs:
            event.accept()
            return

        # If there are changes, ask if they should be saved.
        if self.isDirty():
            result = QMessageBox.question(self, self.windowTitle(),
                u"Es gibt noch ungespeicherte Änderungen an diesem Buch.",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

            if result == QMessageBox.Save:
                self.onSaveClicked()
                event.ignore()
                return
            elif result == QMessageBox.Cancel:
                event.ignore()
                return

        # Maintain list of open dialogs.
        if self.book.id in BookDialog.dialogs:
            del BookDialog.dialogs[self.book.id]

        event.accept()

    def sizeHint(self):
        """Make the dialog slightly wider than required."""
        size = super(BookDialog, self).sizeHint()
        return QSize(size.width() + 150, size.height())

class LendingDialog(QDialog):

    dialogs = dict()

    @classmethod
    def open(cls, app, book, parent):
        if not book.id in cls.dialogs or not cls.dialogs[book.id].isVisible():
            cls.dialogs[book.id] = LendingDialog(app, book, parent)
            cls.dialogs[book.id].show()
        else:
            cls.dialogs[book.id].activateWindow()

    @classmethod
    def ensureClosed(cls, book):
        if book.id in cls.dialogs:
            cls.dialogs[book.id].close()

    def __init__(self, app, book, parent):
        super(LendingDialog, self).__init__(parent)
        self.app = app
        self.book = book

        # Create the stack of the different views and a busy indicator.
        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initLendPage())
        self.layoutStack.addWidget(self.initBusyIndicator())
        self.setLayout(self.layoutStack)

        # Initialize the displayed values.
        self.updateValues(False)

        # Handle network responses.
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.ticket = None

    def updateValues(self, busy):
        if busy:
            self.layoutStack.setCurrentIndex(1)
            self.busyIndicator.setEnabled(True)
        else:
            self.busyIndicator.setEnabled(False)

        if not self.book.lent:
            self.lendIdBox.setText(str(self.book.id))
            self.lendIsbnBox.setText(self.book.isbn)
            self.lendTitleBox.setText(self.book.title)
            self.lendAuthorsBox.setText(self.book.authors)
            self.lendLocationBox.setText(self.book.location)

    def initLendPage(self):
        form = QFormLayout()

        self.lendIdBox = QLabel()
        form.addRow("ID:", self.lendIdBox)

        self.lendIsbnBox = QLabel()
        form.addRow("ISBN:", self.lendIsbnBox)

        self.lendTitleBox = QLabel()
        font = self.lendTitleBox.font()
        font.setBold(True)
        self.lendTitleBox.setFont(font)
        form.addRow("Titel:", self.lendTitleBox)

        self.lendAuthorsBox = QLabel()
        form.addRow("Autoren:", self.lendAuthorsBox)

        self.lendLocationBox = QLabel()
        form.addRow("Standort:", self.lendLocationBox)

        self.lendUserBoxCompleter = QCompleter(self)
        self.lendUserBoxCompleter.setModel(self.app.users)
        self.lendUserBoxCompleter.setCaseSensitivity(Qt.CaseInsensitive)
        self.lendUserBoxCompleter.setCompletionMode(QCompleter.PopupCompletion)
        self.lendUserBox = QLineEdit()
        self.lendUserBox.setCompleter(self.lendUserBoxCompleter)
        form.addRow("Ausleihen an:", self.lendUserBox)

        row = QHBoxLayout()
        row.addStretch(1)
        self.lendButton = QPushButton(u"Für 14 Tage ausleihen")
        self.lendButton.setIcon(QIcon("data/basket_go_32.png"))
        self.lendButton.clicked.connect(self.onLendButton)
        row.addWidget(self.lendButton)
        form.addRow(row)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def initBusyIndicator(self):
        self.busyIndicator = busyindicator.BusyIndicator()
        return self.busyIndicator

    def onLendButton(self):
        user = self.lendUserBox.text().strip()

        params = QUrl()
        params.addQueryItem("_csrf", self.app.login.csrf)
        params.addQueryItem("user", user)
        params.addQueryItem("days", str(14))

        path = "/books/%d/lending" % self.book.id
        request = QNetworkRequest(self.app.login.getUrl(path))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
        self.ticket = self.app.network.http("POST", request, params.encodedQuery())
        self.updateValues(True)

    def closeEvent(self, event):
        # Saving in progress.
        if self.ticket:
            event.ignore()
            return

        # Maintain list of open dialogs.
        if self.book.id in LendingDialog.dialogs:
            del LendingDialog.dialogs[self.book.id]

        event.accept()

    def onNetworkRequestFinished(self, reply):
        request = reply.request()
