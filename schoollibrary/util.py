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

import rendering


class TitleAndDescriptionDelegate(QItemDelegate):
    """A delegate for displaying read only rich text."""

    DescriptionRole = Qt.UserRole + 1

    def createEditor(self, parent, option, index):
        """No editor is used."""
        return None

    def paint(self, painter, option, index):
        self._index = index
        self._option = option
        super(TitleAndDescriptionDelegate, self).paint(painter, option, index)

    def createLayout(self, rect, option, index):
        boldFont = QApplication.font()
        boldFont.setBold(True)

        document = rendering.Document(QApplication.font(), rect.width(), 1000)

        layout = rendering.VerticalLayout(document)

        if option.state & QStyle.State_Selected:
            # Use a contrasting color if selected.
            foregroundData = option.palette.color(QPalette.Normal, QPalette.HighlightedText)
        else:
            foregroundData = index.data(Qt.ForegroundRole)
            if not foregroundData:
                foregroundData = option.palette.color(QPalette.Normal, QPalette.Text)

        displayData = index.data(Qt.DisplayRole)
        if displayData:
            layout.children.append(
                rendering.BorderedBox(
                    document,
                    child=rendering.TextBox(document, displayData, rect.width() - 10, font=boldFont, textColor=foregroundData),
                    borders=rendering.BorderedBox.NoBorders,
                    margins=QMargins(5, 5, 5, 2)))

        descriptionData = index.data(TitleAndDescriptionDelegate.DescriptionRole)
        if descriptionData:
            layout.children.append(
                rendering.BorderedBox(
                    document,
                    child=rendering.TextBox(document, descriptionData, rect.width() - 10, textColor=foregroundData),
                    borders=rendering.BorderedBox.NoBorders,
                    margins=QMargins(5, 2, 5, 5)))

        return layout

    def drawDisplay(self, painter, option, rect, text):
        # Draw the document.
        painter.translate(rect.topLeft())
        self.createLayout(rect, self._option, self._index).render(painter, rect.size())
        painter.translate(-rect.topLeft())

    def sizeHint(self, option, index):
        inheritedHint = super(TitleAndDescriptionDelegate, self).sizeHint(option, index)

        # Take all the width we get, vary the height.
        if inheritedHint.width() < option.rect.width():
            width = option.rect.width()
        else:
            width = inheritedHint.width()

        # Compute the height.
        height = self.createLayout(QRect(QPoint(0, 0), QPoint(width - 50, 0)), option, index).height()
        height = max(inheritedHint.height(), height)

        return QSize(width, height)
