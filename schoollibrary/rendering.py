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


class Document(object):
    """A rendering context."""

    def __init__(self, font, pageWidth, pageHeight):
        self.font = font
        self.pageWidth = pageWidth
        self.pageHeight = pageHeight

    def pageSize(self):
        return QSize(self.pageWidth, self.pageHeight)

    def contentsSize(self):
        return QSize(self.pageWidth, self.pageHeight - self.footerHeight() - self.headerHeight())

    def footerHeight(self):
        return 0

    def headerHeight(self):
        return 0

    def renderPage(self, painter, pageNumber):
        pass

    @classmethod
    def fromPrinter(cls, printer):
        """Creates a document with the properties of a printer."""
        return cls(QApplication.font(), printer.width(), printer.height())


class Spacer(object):
    """Placeholder object. Nothing is rendered."""

    def __init__(self, width=0, height=0):
        self._width = width
        self._height = height

    def height(self):
        return self._height

    def width(self):
        return self._width

    def render(self, painter, size):
        pass


class BorderedBox(object):
    """A box with a child, margins, borders and background color."""

    TopBorder = 0x0001
    BottomBorder = 0x0010
    LeftBorder = 0x0100
    RightBorder = 0x1000
    VerticalBorders = 0x1100
    HorizontalBorders = 0x0011
    NoBorders = 0x0000
    AllBorders = 0x1111

    def __init__(self, document, child=Spacer(), margins=QMargins(10, 10, 10, 10), borders=0x1111, borderWidth=1, backgroundColor=None):
        self.document = document
        self.child = child
        if not self.child:
            self.child = Spacer()
        self.margins = margins
        self.borders = borders
        self.borderWidth = borderWidth
        self.backgroundColor = backgroundColor

    def width(self):
        return self.margins.left() + self.child.width() + self.margins.right()

    def height(self):
        return self.margins.top() + self.child.height() + self.margins.bottom()

    def render(self, painter, size):
        # Draw the background.
        if self.backgroundColor:
            painter.fillRect(0, 0, size.width(), size.height(), QBrush(self.backgroundColor))

        # Draw the borders.
        oldPen = painter.pen()
        pen = QPen(Qt.SolidLine)
        pen.setWidth(self.borderWidth)
        painter.setPen(pen)

        if self.borders & BorderedBox.TopBorder:
            painter.drawLine(QPoint(0, 0), QPoint(size.width(), 0))
        if self.borders & BorderedBox.BottomBorder:
            painter.drawLine(QPoint(0, size.height()), QPoint(size.width(), size.height()))
        if self.borders & BorderedBox.LeftBorder:
            painter.drawLine(QPoint(0, 0), QPoint(0, size.height()))
        if self.borders & BorderedBox.RightBorder:
            painter.drawLine(QPoint(size.width(), 0), QPoint(size.width(), size.height()))

        painter.setPen(oldPen)

        # Render the child widget.
        if self.child:
            childSize = QSize(
                size.width() - self.margins.left() - self.margins.right(),
                size.height() - self.margins.top() - self.margins.bottom())
            painter.save()
            painter.translate(self.margins.left(), self.margins.top())
            self.child.render(painter, childSize)
            painter.restore()


class TextBox(object):
    """A box with aligned text and a fixed width."""

    def __init__(self, document, text, width, align=Qt.AlignLeft | Qt.AlignTop, font=None, textColor=QColor()):
        self.document = document
        self.text = text
        self._width = width
        self.align = align
        self.textColor = textColor

        self._font = font

    def font(self):
        if self._font:
            return self._font
        else:
            return self.document.font

    def width(self):
        return self._width

    def height(self):
        metrics = QFontMetrics(self.font())
        rect = metrics.boundingRect(0, 0, self.width(), self.document.pageHeight, Qt.TextWordWrap, self.text)
        return rect.height()

    def render(self, painter, size):
        oldPen = painter.pen()
        pen = painter.pen()
        pen.setBrush(QBrush(self.textColor))
        painter.setPen(pen)
        oldFont = painter.font()
        painter.setFont(self.font())
        option = QTextOption(self.align)
        option.setWrapMode(QTextOption.WordWrap)
        painter.drawText(QRect(QPoint(0, 0), size), self.text, option)
        painter.setFont(oldFont)
        painter.setPen(oldPen)


class IndentedText(object):
    """A box with indented text and a fixed width."""

    def __init__(self, document, text, width, indentation=0, font=None, bullet=False):
        self.document = document
        self.text = text
        self._width = width
        self.indentation = indentation
        self._font = font
        self.bullet = bullet

    def font(self):
        if self._font:
            return self._font
        else:
            return self.document.font

    def width(self):
        return self._width

    def height(self):
        metrics = QFontMetrics(self.font())
        rect = metrics.boundingRect(0, 0, self.width() - self.indentation, self.document.pageHeight, Qt.TextWordWrap, self.text)
        return rect.height()

    def render(self, painter, size):
        oldFont = painter.font()
        painter.setFont(self.font())
        option = QTextOption(Qt.AlignLeft | Qt.AlignTop)
        option.setWrapMode(QTextOption.WordWrap)
        if self.bullet:
            fontHeight = QFontMetrics(self.font()).height()
            painter.drawText(QRect(QPoint(self.indentation - fontHeight, 0), QSize(fontHeight, fontHeight)), u"•", QTextOption(Qt.AlignCenter))
        painter.drawText(QRect(QPoint(self.indentation, 0), QSize(size.width() - self.indentation, size.height())), self.text, option)
        painter.setFont(oldFont)


class HorizontalLayout(object):
    """Aligns its children horizontally."""

    def __init__(self, document):
        self.children = []

    def width(self):
        if not self.children:
            return 0
        else:
            return sum([child.width() for child in self.children])

    def height(self):
        if not self.children:
            return 0
        else:
            return max([child.height() for child in self.children])

    def render(self, painter, size):
        painter.save()
        for child in self.children:
            child.render(painter, QSize(child.width(), size.height()))
            painter.translate(child.width(), 0)
        painter.restore()


class VerticalLayout(object):
    """Aligns its children vertically."""

    def __init__(self, document):
        self.document = document
        self.children = []

    def width(self):
        if not self.children:
            return 0
        else:
            return max([child.width() for child in self.children])

    def height(self):
        if not self.children:
            return 0
        else:
            return sum([child.height() for child in self.children])

    def render(self, painter, size):
        painter.save()
        for child in self.children:
            child.render(painter, QSize(size.width(), child.height()))
            painter.translate(0, child.height())
        painter.restore()

    def print_(self, printer):
        painter = QPainter(printer)

        pageNumber = 1
        self.document.renderPage(painter, pageNumber)

        y = self.document.headerHeight()
        for child in self.children:
            childHeight = child.height()
            if y != self.document.headerHeight() and y + childHeight > self.document.contentsSize().height() + self.document.footerHeight():
                y = self.document.headerHeight()
                printer.newPage()
                pageNumber += 1
                self.document.renderPage(painter, pageNumber)

            painter.save()
            painter.translate(0, y)
            child.render(painter, QSize(self.document.pageWidth, childHeight))
            painter.restore()

            y += childHeight

        painter.end()

    def childIndexAt(self, point):
        y = 0
        for index, child in enumerate(self.children):
            childHeight = child.height()
            if point.y() >= y and point.y() <= y + childHeight:
                return index
            y += childHeight

        return -1
