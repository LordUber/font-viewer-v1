import sys
import os
import zipfile
import tempfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QListWidget, QListWidgetItem,
    QFileDialog, QWidget, QGridLayout, QScrollArea,
    QPlainTextEdit, QAction, QMessageBox, QToolBar,
    QLabel, QLineEdit, QCheckBox
)
from PyQt5.QtGui import QFontDatabase, QFont, QFontMetrics, QIntValidator, QKeySequence, QIcon
from PyQt5.QtCore import Qt, QStandardPaths

# Subclass QPlainTextEdit so Ctrl+C clears the text box instead of copying
class ClearableTextEdit(QPlainTextEdit):
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.clear()
        else:
            super().keyPressEvent(event)

# Supported font extensions
FONT_EXTS = ('.ttf', '.otf')
ARCHIVE_EXT = '.zip'
ASCII_RANGE = range(32, 127)  # printable ASCII

class FontPreviewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Font Previewer")
        self.setWindowIcon(QIcon(r"C:\Users\Me\dev\font-previewer\fv_icon.ico"))

        # Resize to 90% of screen
        screen = QApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * 0.9)
        h = int(screen.height() * 0.9)
        x = (screen.width() - w) // 2 + screen.x()
        y = (screen.height() - h) // 2 + screen.y()
        self.setGeometry(x, y, w, h)

        # Menu
        fileMenu = self.menuBar().addMenu("File")
        openFolder = QAction("Open Folder…", self)
        openFolder.triggered.connect(self.open_folder)
        fileMenu.addAction(openFolder)
        helpMenu = self.menuBar().addMenu("Help")
        aboutAction = QAction("About", self)
        aboutAction.triggered.connect(self.show_about)
        helpMenu.addAction(aboutAction)

        # Toolbar
        tb = QToolBar("Font Controls", self)
        self.addToolBar(tb)
        tb.addWidget(QLabel("Size:"))
        self.sizeEdit = QLineEdit("46")
        self.sizeEdit.setMaximumWidth(50)
        self.sizeEdit.setValidator(QIntValidator(1, 500, self))
        self.sizeEdit.editingFinished.connect(self.update_font_settings)
        tb.addWidget(self.sizeEdit)
        self.boldCheck = QCheckBox("Bold")
        self.boldCheck.stateChanged.connect(self.update_font_settings)
        tb.addWidget(self.boldCheck)
        self.italicCheck = QCheckBox("Italic")
        self.italicCheck.stateChanged.connect(self.update_font_settings)
        tb.addWidget(self.italicCheck)
        tb.addWidget(QLabel(" Alt code:"))
        self.altCodeEdit = QLineEdit()
        self.altCodeEdit.setMaximumWidth(50)
        self.altCodeEdit.setValidator(QIntValidator(0, 1114111, self))
        self.altCodeEdit.editingFinished.connect(self.insert_alt_code_symbol)
        tb.addWidget(self.altCodeEdit)

        # Splitters
        outer = QSplitter(Qt.Horizontal)
        self.setCentralWidget(outer)
        self.fileList = QListWidget()
        self.fileList.itemClicked.connect(self.on_file_clicked)
        outer.addWidget(self.fileList)

        rightSplit = QSplitter(Qt.Vertical)
        outer.addWidget(rightSplit)
        outer.setStretchFactor(1, 3)

        # Preview area
        self.previewWidget = QWidget()
        self.previewWidget.setStyleSheet("background-color:white;")
        self.previewLayout = QGridLayout(self.previewWidget)
        self.previewScroll = QScrollArea()
        self.previewScroll.setStyleSheet("background-color:white;")
        self.previewScroll.setWidgetResizable(True)
        self.previewScroll.setWidget(self.previewWidget)
        rightSplit.addWidget(self.previewScroll)

        # Text entry
        self.textEdit = ClearableTextEdit()
        self.textEdit.setPlaceholderText("Type here…")
        self.textEdit.textChanged.connect(self.on_text_changed)
        rightSplit.addWidget(self.textEdit)

        rightSplit.setStretchFactor(0, 1)
        rightSplit.setStretchFactor(1, 1)
        rightSplit.setSizes([h//2, h//2])

        # Default folder
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        fonts_dir = os.path.join(docs, 'fonts')
        self.currentFolder = fonts_dir if os.path.isdir(fonts_dir) else docs

        self.currentFont = QApplication.font()
        self.currentFontSize = 44

        self.load_folder(self.currentFolder)
        self.textEdit.setFocus()

    def show_about(self):
        QMessageBox.about(self, "About Font Previewer",
                          '<div align="center">'
                          '   <a href="https://github.com/LordUber">(c) Mathias Nagy</a><br>'
                          'Released under MIT license<br>'
                          '23 April 2025 </div>')

    def open_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Font Folder", self.currentFolder)
        if d:
            self.load_folder(d)

    def load_folder(self, folder):
        self.currentFolder = folder
        self.fileList.clear()
        for fn in sorted(os.listdir(folder), key=str.lower):
            if fn.lower().endswith(FONT_EXTS) or fn.lower().endswith(ARCHIVE_EXT):
                item = QListWidgetItem(fn)
                full = os.path.join(folder, fn)
                if fn.lower().endswith(ARCHIVE_EXT):
                    try:
                        with zipfile.ZipFile(full) as z:
                            has = any(n.lower().endswith(FONT_EXTS) for n in z.namelist())
                        item.setToolTip(full if has else "no fonts in here")
                    except zipfile.BadZipFile:
                        item.setToolTip("invalid zip")
                else:
                    item.setToolTip(full)
                self.fileList.addItem(item)

    def on_file_clicked(self, item):
        path = os.path.join(self.currentFolder, item.text())
        if path.lower().endswith(ARCHIVE_EXT):
            try:
                with zipfile.ZipFile(path) as z:
                    fonts = [n for n in z.namelist() if n.lower().endswith(FONT_EXTS)]
                    if not fonts:
                        QMessageBox.information(self, "No Fonts", "no fonts in here")
                        return
                    data = z.read(fonts[0])
            except zipfile.BadZipFile:
                QMessageBox.warning(self, "Error", "Invalid ZIP archive")
                return
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(fonts[0])[1])
            tmp.write(data); tmp.close()
            path = tmp.name
        self.load_font(path)

    def load_font(self, path):
        # Clear preview
        while self.previewLayout.count():
            w = self.previewLayout.takeAt(0).widget()
            if w: w.deleteLater()
        fid = QFontDatabase.addApplicationFont(path)
        if fid < 0:
            QMessageBox.warning(self, "Error", "Failed to load font."); return
        fams = QFontDatabase.applicationFontFamilies(fid)
        if not fams:
            QMessageBox.warning(self, "Error", "No font family found."); return
        self.currentFont = QFont(fams[0], self.currentFontSize)
        self.apply_style_flags()
        self.render_preview()
        self.textEdit.setFont(self.currentFont)
        self.textEdit.setFocus()

    def insert_alt_code_symbol(self):
        code = self.altCodeEdit.text()
        if code:
            try:
                ch = chr(int(code))
                self.textEdit.insertPlainText(ch)
            except:
                QMessageBox.warning(self, "Invalid Code", f"Invalid alt code: {code}")

    def render_preview(self):
        # Clear any existing widgets
        while self.previewLayout.count():
            w = self.previewLayout.takeAt(0).widget()
            if w:
                w.deleteLater()

        fm = QFontMetrics(self.currentFont)
        default_font = QApplication.font()
        ref_font = QFont(default_font.family(), 14)
        cols = 10

        # 1) Core ASCII characters
        for idx, code in enumerate(ASCII_RANGE):
            ch = chr(code)
            r = (idx // cols) * 2
            c = idx % cols

            # Reference label with code
            lbl_ref = QLabel(f"{ch} ({code})")
            lbl_ref.setFont(ref_font)
            self.previewLayout.addWidget(
                lbl_ref, r, c, 1, 1, Qt.AlignBottom | Qt.AlignHCenter
            )

            # Font glyph only if supported
            if fm.inFontUcs4(code):
                lbl_gly = QLabel(ch)
                lbl_gly.setFont(self.currentFont)
            else:
                lbl_gly = QLabel("")
            self.previewLayout.addWidget(
                lbl_gly, r+1, c, 1, 1, Qt.AlignTop | Qt.AlignHCenter
            )

        # 2) “Other Unicode” separator
        sep_row = ((len(ASCII_RANGE) + cols - 1) // cols) * 2
        sep = QLabel("Other Unicode")
        sep.setAlignment(Qt.AlignCenter)
        self.previewLayout.addWidget(sep, sep_row, 0, 1, cols)

        # 3) Extended block U+007F–U+0400 (127–1024)
        for j, code in enumerate(range(127, 1025)):
            ch = chr(code)
            r = sep_row + 1 + (j // cols) * 2
            c = j % cols

            lbl_ref_o = QLabel(f"{ch} ({code})")
            lbl_ref_o.setFont(ref_font)
            self.previewLayout.addWidget(
                lbl_ref_o, r, c, 1, 1, Qt.AlignBottom | Qt.AlignHCenter
            )

            if fm.inFontUcs4(code):
                lbl_gly_o = QLabel(ch)
                lbl_gly_o.setFont(self.currentFont)
            else:
                lbl_gly_o = QLabel("")
            self.previewLayout.addWidget(
                lbl_gly_o, r+1, c, 1, 1, Qt.AlignTop | Qt.AlignHCenter
            )

    def update_font_settings(self):
        try:
            sz = int(self.sizeEdit.text())
            if sz > 0: self.currentFontSize = sz
        except:
            pass
        self.apply_style_flags()
        self.currentFont.setPointSize(self.currentFontSize)
        self.render_preview()
        self.textEdit.setFont(self.currentFont)

    def apply_style_flags(self):
        self.currentFont.setBold(self.boldCheck.isChecked())
        self.currentFont.setItalic(self.italicCheck.isChecked())

    def on_text_changed(self):
        if self.textEdit.verticalScrollBar().maximum() > 0:
            self.textEdit.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FontPreviewer()
    win.show()
    sys.exit(app.exec_())
