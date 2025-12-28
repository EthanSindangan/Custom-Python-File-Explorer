import sys
import os
import shutil
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSizePolicy, QFileSystemModel, QTreeView, QListView,
    QSplitter, QLineEdit, QToolButton, QMenu, QAction, QMessageBox
)
from PyQt5.QtGui import (
    QPixmap, QIcon, QFont, QDesktopServices, QCursor, QDrag, 
    QKeySequence, QPainter, QLinearGradient, QColor
)
from PyQt5.QtCore import Qt, QSize, QUrl, QMimeData, QModelIndex

# --- textures ---
TEXTURE_DIR = os.path.join(os.path.dirname(__file__), "textures")
CLOSE_IMG = os.path.join(TEXTURE_DIR, "close.png")
MINIMIZE_IMG = os.path.join(TEXTURE_DIR, "minimize.png")
TITLEBAR_BG = os.path.join(TEXTURE_DIR, "titlebar_bg.png")  # New texture for title bar background
BUTTON_SIZE = 32  # keeps original titlebar buttons 32px (titlebar). Content buttons will be 40px.

# helper to load icons from user's texture folder without altering the textures
def load_icon(path, size=None):
    """Return QIcon from path if exists; otherwise return None.
    If size is provided, the pixmap will be scaled to that size."""
    if os.path.exists(path):
        pix = QPixmap(path)
        if not pix.isNull():
            if size is None:
                size = BUTTON_SIZE
            pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return QIcon(pix)
    return None


# ---------------- TitleBar and custom popup reused with minor changes ----------------
class TitleBar(QWidget):
    """Custom title bar with background texture and icon buttons."""
    def __init__(self, parent=None, title="Custom File Explorer"):
        super().__init__(parent)
        self._parent = parent

        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Load background texture
        self.background_texture = None
        if os.path.exists(TITLEBAR_BG):
            self.background_texture = QPixmap(TITLEBAR_BG)
        
        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 4, 0)
        layout.setSpacing(6)

        # Title label - now with styling that works well over the texture
        self.title_label = QLabel(title)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        
        # Style for better visibility over texture
        self.title_label.setStyleSheet("""
            QLabel {
                color: #252525;
                background: transparent;
                padding: 2px 8px;
                border-radius: 4px;
                /* You can also add font properties here as backup */
                font-family: "Noto Sans"; 
                font-size: 14px; 
            }
        """)
        
        layout.addWidget(self.title_label, 1)

        # Buttons (minimize and close same as before)
        self.min_btn = QPushButton()
        self.min_btn.setToolTip("Minimize")
        self._style_button(self.min_btn)
        min_icon = load_icon(MINIMIZE_IMG, BUTTON_SIZE)
        if min_icon:
            self.min_btn.setIcon(min_icon)
            self.min_btn.setIconSize(QSize(BUTTON_SIZE, BUTTON_SIZE))
        else:
            self.min_btn.setText("—")
        self.min_btn.clicked.connect(self.on_minimize)
        layout.addWidget(self.min_btn, 0, Qt.AlignRight)

        self.close_btn = QPushButton()
        self.close_btn.setToolTip("Close")
        self._style_button(self.close_btn)
        close_icon = load_icon(CLOSE_IMG, BUTTON_SIZE)
        if close_icon:
            self.close_btn.setIcon(close_icon)
            self.close_btn.setIconSize(QSize(BUTTON_SIZE, BUTTON_SIZE))
        else:
            self.close_btn.setText("✕")
        self.close_btn.clicked.connect(self.on_close)
        layout.addWidget(self.close_btn, 0, Qt.AlignRight)

        self.setLayout(layout)

        # For dragging
        self._drag_pos = None

    def paintEvent(self, event):
        """Override paintEvent to draw the background texture."""
        painter = QPainter(self)
        
        if self.background_texture and not self.background_texture.isNull():
            # Scale the texture to fill the entire title bar
            scaled_pixmap = self.background_texture.scaled(
                self.width(), self.height(),
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_pixmap)
        else:
            # Fallback gradient if no texture
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(100, 100, 100))
            gradient.setColorAt(1, QColor(60, 60, 60))
            painter.fillRect(self.rect(), gradient)
        
        painter.end()

    def _style_button(self, btn: QPushButton):
        btn.setFlat(True)
        btn.setFixedSize(BUTTON_SIZE + 8, BUTTON_SIZE + 8)
        btn.setCursor(Qt.PointingHandCursor)
        
        # Style buttons to look good over textured background
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0);
                border: 1px solid rgba(255, 255, 255, 0);
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0);
            }
        """)

    def on_minimize(self):
        if self._parent:
            self._parent.showMinimized()

    def on_close(self):
        if self._parent:
            self._parent.close()

    # Enable click-and-drag to move the window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and self._parent:
            delta = event.globalPos() - self._drag_pos
            self._parent.move(self._parent.pos() + delta)
            self._drag_pos = event.globalPos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


class CustomPopup(QWidget):
    def __init__(self):
        super().__init__()
        # Frameless window so we can use custom buttons
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        # Optional: Uncomment next line to make background translucent if your PNGs have transparency
        # self.setAttribute(Qt.WA_TranslucentBackground)

        self.setMinimumSize(900, 600)
        self.setWindowTitle("Custom File Explorer")

        # State for cut/copy
        self._clipboard_paths = []
        self._clipboard_is_cut = False

        self._build_ui()

    def toggle_view(self):
        """Switch between list view and icon (grid) view."""
        if hasattr(self, "list"):
            current_mode = self.list.viewMode()
            if current_mode == QListView.ListMode:
                self.list.setViewMode(QListView.IconMode)
                self.view_toggle.setToolTip("Switch to List View")
                self.view_toggle.setText("List")
            else:
                self.list.setViewMode(QListView.ListMode)
                self.view_toggle.setToolTip("Switch to Icon View")
                self.view_toggle.setText("Icons")

    def _build_ui(self):
        """Builds the UI. This method must be indented inside the CustomPopup class."""
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)  # Remove margins to let title bar texture go edge-to-edge
        v.setSpacing(0)

        # Title bar with texture
        self.titlebar = TitleBar(self, title="Custom File Explorer")
        v.addWidget(self.titlebar)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)

        # Top controls: back, up, address bar, view toggle
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        self.back_btn = QToolButton()
        self.back_btn.setText("◀")
        self.back_btn.setToolTip("Back")
        self.back_btn.clicked.connect(self.on_back)
        ctrl_row.addWidget(self.back_btn)

        self.up_btn = QToolButton()
        self.up_btn.setText("⬆")
        self.up_btn.setToolTip("Up")
        self.up_btn.clicked.connect(self.on_up)
        ctrl_row.addWidget(self.up_btn)

        self.address = QLineEdit()
        self.address.setReadOnly(False)
        self.address.returnPressed.connect(self.on_address_enter)
        ctrl_row.addWidget(self.address, 1)

        self.view_toggle = QToolButton()
        self.view_toggle.setText("Icons")
        self.view_toggle.setCheckable(True)
        self.view_toggle.clicked.connect(self.toggle_view)
        ctrl_row.addWidget(self.view_toggle)

        content_layout.addLayout(ctrl_row)

        # --- Top row: four 40x40 image buttons side-by-side ---
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        button_size = 40  # required size for these content buttons
        # Each button now has a tooltip associated with it
        buttons_info = [
            ("button1.png", "Cut File (can be pasted in this File Explorer and outside to your general File Explorer to be exported from here)"),
            ("button2.png", "Copy File (can be pasted in this File Explorer and outside to your general File Explorer to be exported from here)"),
            ("button3.png", "Delete File"),
            ("button4.png", "Paste File (paste from our internal clipboard or system clipboard)"),
        ]
        self.content_buttons = []

        # Copy
        path = os.path.join(TEXTURE_DIR, buttons_info[1][0])
        self.copy_btn = QPushButton()
        self.copy_btn.setFlat(True)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setFixedSize(button_size, button_size)
        self.copy_btn.setToolTip(buttons_info[1][1])
        icon = load_icon(path, button_size)
        if icon:
            self.copy_btn.setIcon(icon)
            self.copy_btn.setIconSize(QSize(button_size, button_size))
        else:
            self.copy_btn.setText("Copy")
        self.copy_btn.clicked.connect(self.on_copy)
        button_row.addWidget(self.copy_btn)

        # Delete
        path = os.path.join(TEXTURE_DIR, buttons_info[2][0])
        self.delete_btn = QPushButton()
        self.delete_btn.setFlat(True)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setFixedSize(button_size, button_size)
        self.delete_btn.setToolTip(buttons_info[2][1])
        icon = load_icon(path, button_size)
        if icon:
            self.delete_btn.setIcon(icon)
            self.delete_btn.setIconSize(QSize(button_size, button_size))
        else:
            self.delete_btn.setText("Del")
        self.delete_btn.clicked.connect(self.on_delete)
        button_row.addWidget(self.delete_btn)

        # Paste (now with button4.png)
        path = os.path.join(TEXTURE_DIR, buttons_info[3][0])
        self.paste_btn = QPushButton()
        self.paste_btn.setFlat(True)
        self.paste_btn.setCursor(Qt.PointingHandCursor)
        self.paste_btn.setFixedSize(button_size, button_size)
        self.paste_btn.setToolTip(buttons_info[3][1])
        icon = load_icon(path, button_size)
        if icon:
            self.paste_btn.setIcon(icon)
            self.paste_btn.setIconSize(QSize(button_size, button_size))
        else:
            self.paste_btn.setText("Paste")
        self.paste_btn.clicked.connect(self.on_paste)
        button_row.addWidget(self.paste_btn)

        # Add spacer
        button_row.addStretch()

        content_layout.addLayout(button_row)

        # Splitter with tree (left) and file view (right)
        splitter = QSplitter()

        # File system model and tree
        self.model = QFileSystemModel()
        self.model.setRootPath(str(Path.home()))

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(Path.home())))
        self.tree.setHeaderHidden(False)
        self.tree.setAnimated(False)
        self.tree.clicked.connect(self.on_tree_clicked)
        self.tree.setMinimumWidth(250)

        splitter.addWidget(self.tree)

        # Right side: list view
        self.list = QListView()
        self.list.setModel(self.model)
        self.list.setRootIndex(self.model.index(str(Path.home())))
        self.list.doubleClicked.connect(self.on_item_double_clicked)
        self.list.setSelectionMode(QListView.ExtendedSelection)

        splitter.addWidget(self.list)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter, 1)

        # Status row
        status_row = QHBoxLayout()
        self.status = QLabel("         ")
        status_row.addWidget(self.status)
        status_row.addStretch()
        content_layout.addLayout(status_row)

        content.setLayout(content_layout)
        content.setStyleSheet("""
            QWidget {
                border: 2px solid #535353;
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #a8a8a8,   /* top color */
                    stop: 1 #6d6d6d    /* bottom color */
                );
            }
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06); /* subtle hover highlight */
                border-radius: 6px;
            }
        """)

        v.addWidget(content, 1)

        self.setLayout(v)

        # tooltip style
        self.setStyleSheet("""
            QToolTip {
                background-color: #333333;
                color: white;
                border: 1px solid #222222;
                padding: 2px;
                font-size: 11pt;
                font-family: 'Noto Sans';
            }
        """)

        # initialize address
        self._current_path = str(Path.home())
        self.address.setText(self._current_path)

        # Keep track of history
        self._history = [self._current_path]
        self._history_index = 0

    # ---------------- Navigation ----------------
    def on_back(self):
        if self._history_index > 0:
            self._history_index -= 1
            self.go_to_path(self._history[self._history_index])

    def on_up(self):
        p = Path(self._current_path)
        if p.parent != p:
            self.go_to_path(str(p.parent))

    def on_address_enter(self):
        path = self.address.text().strip()
        if path:
            self.go_to_path(path)

    def go_to_path(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Path not found", f"The path does not exist:\n{path}")
            return
        idx = self.model.index(path)
        if not idx.isValid():
            QMessageBox.warning(self, "Invalid path", f"Cannot open path:\n{path}")
            return
        self._current_path = os.path.abspath(path)
        self.address.setText(self._current_path)
        self.list.setRootIndex(idx)
        self.tree.setCurrentIndex(idx)
        self.tree.expand(idx)
        # update history
        if self._history_index == -1 or self._history[self._history_index] != self._current_path:
            # trim forward history
            self._history = self._history[: self._history_index + 1]
            self._history.append(self._current_path)
            self._history_index = len(self._history) - 1
        self.status.setText(self._current_path)

    def on_tree_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        self.go_to_path(path)

    def on_item_double_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.go_to_path(path)
        else:
            # open file with default app
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ---------------- Cut / Copy / Paste / Delete ----------------
    def selected_paths(self):
        selection = self.list.selectionModel().selectedIndexes()
        paths = []
        seen = set()
        for idx in selection:
            p = self.model.filePath(idx)
            if p not in seen:
                paths.append(p)
                seen.add(p)
        return paths

    def on_copy(self):
        paths = self.selected_paths()
        if not paths:
            QMessageBox.information(self, "No selection", "Select files/folders to copy.")
            return
        self._clipboard_paths = paths
        self._clipboard_is_cut = False
        self._place_paths_in_system_clipboard(paths, cut=False)
        self.status.setText(f"Copied {len(paths)} items")

    def on_paste(self):
        import shutil
        from PyQt5.QtWidgets import QApplication, QMessageBox

        dest_dir = self._current_path
        if not os.path.isdir(dest_dir):
            QMessageBox.warning(self, "Invalid Target", "Current location is not a directory.")
            return

        cb = QApplication.clipboard()
        md = cb.mimeData()

        # --- SYSTEM CLIPBOARD HANDLING ---
        if md and md.hasUrls():
            urls = md.urls()
            paths = [u.toLocalFile() for u in urls if u.isLocalFile()]

            for src in paths:
                try:
                    if not os.path.exists(src):
                        continue

                    base = os.path.basename(src)
                    dest = os.path.join(dest_dir, base)

                    if os.path.abspath(src) == os.path.abspath(dest_dir):
                        QMessageBox.warning(self, "Paste Error", f"Cannot paste '{base}' into itself.")
                        continue

                    if os.path.exists(dest):
                        base_name, ext = os.path.splitext(base)
                        dest = os.path.join(dest_dir, f"{base_name}_copy{ext}")

                    if os.path.isdir(src):
                        shutil.copytree(src, dest)
                    else:
                        shutil.copy2(src, dest)

                except Exception as e:
                    QMessageBox.warning(self, "Paste Error", str(e))

            self.status.setText(f"Pasted {len(paths)} item(s) from system clipboard")
            root_index = self.model.setRootPath(dest_dir)
            self.list.setRootIndex(root_index)
            return

        # --- INTERNAL CLIPBOARD HANDLING ---
        if not getattr(self, "_clipboard_paths", []):
            QMessageBox.information(self, "Clipboard is empty", "Nothing to paste.")
            return

        clipboard_paths = self._clipboard_paths.copy()
        clipboard_is_cut = getattr(self, "_clipboard_is_cut", False)

        pasted_count = 0
        failed_paths = []  # Track which files failed to move

        for src in clipboard_paths:
            try:
                if not os.path.exists(src):
                    continue

                base = os.path.basename(src)
                dest = os.path.join(dest_dir, base)

                # Prevent recursive move
                if os.path.abspath(src) == os.path.abspath(dest_dir):
                    QMessageBox.warning(self, "Paste Error", f"Cannot paste '{base}' into itself.")
                    continue

                # Handle name conflicts
                if os.path.exists(dest):
                    base_name, ext = os.path.splitext(base)
                    dest = os.path.join(dest_dir, f"{base_name}_copy{ext}")

                # --- CUT OPERATION - MOVE AND DELETE ORIGINAL ---
                if clipboard_is_cut:
                    try:
                        # First try direct move
                        shutil.move(src, dest)
                        pasted_count += 1
                    except Exception as move_error:
                        # If direct move fails, try copy + delete as fallback
                        try:
                            if os.path.isdir(src):
                                shutil.copytree(src, dest)
                                shutil.rmtree(src)
                            else:
                                shutil.copy2(src, dest)
                                os.remove(src)
                            pasted_count += 1
                        except Exception as fallback_error:
                            failed_paths.append((src, str(fallback_error)))
                            QMessageBox.warning(self, "Cut/Paste Error", 
                                            f"Failed to move '{base}': {fallback_error}")
                # --- COPY OPERATION ---
                else:
                    if os.path.isdir(src):
                        shutil.copytree(src, dest)
                    else:
                        shutil.copy2(src, dest)
                    pasted_count += 1

            except Exception as e:
                failed_paths.append((src, str(e)))
                QMessageBox.warning(self, "Paste Error", str(e))

        #FIXED: Only clear clipboard for successful cut operations
        if clipboard_is_cut:
            if failed_paths:
                # Some files failed, only remove successful ones from clipboard
                successful_paths = [p for p in clipboard_paths if p not in [fp[0] for fp in failed_paths]]
                self._clipboard_paths = successful_paths
                self.status.setText(f"Paste partially completed ({pasted_count} item(s), {len(failed_paths)} failed)")
            else:
                # All files succeeded, clear clipboard completely
                self._clipboard_paths = []
                self._clipboard_is_cut = False
                self.status.setText(f"Cut/Paste completed ({pasted_count} item(s))")
        else:
            # For copy operations, don't clear clipboard (allow multiple pastes)
            self.status.setText(f"Paste completed ({pasted_count} item(s))")

        # Refresh model view
        root_index = self.model.setRootPath(dest_dir)
        self.list.setRootIndex(root_index)

    def on_delete(self):
        paths = self.selected_paths()
        if not paths:
            QMessageBox.information(self, "No selection", "Select files/folders to delete.")
            return
        ok = QMessageBox.question(self, "Delete?", f"Delete {len(paths)} items? This will permanently delete them.")
        if ok != QMessageBox.StandardButton.Yes:
            return
        for p in paths:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception as e:
                QMessageBox.warning(self, "Delete error", str(e))
        
        root_index = self.list.rootIndex()
        self.model.setRootPath(self.model.rootPath())
        self.list.setRootIndex(root_index)
        self.status.setText(f"Deleted {len(paths)} items")

    def _place_paths_in_system_clipboard(self, paths, cut=False):
        # Put local file URLs into system clipboard so user may paste to other apps / Explorer
        cb = QApplication.clipboard()
        md = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in paths]
        md.setUrls(urls)
        # For cut semantics some platforms use 'preferredAction' flags — we cannot guarantee cross-platform
        cb.setMimeData(md)
        # update status to indicate cross-app clipboard available
        if cut:
            self.status.setText("Placed items in clipboard (cut)")
        else:
            self.status.setText("Placed items in clipboard (copy)")

    # ---------------- Utilities ----------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.matches(QKeySequence.Copy):
            self.on_copy()
        elif event.matches(QKeySequence.Paste):
            self.on_paste()
        super().keyPressEvent(event)


# ---------------- run ----------------
def main():
    app = QApplication(sys.argv)

    # Ensure textures folder exists message if not
    if not os.path.isdir(TEXTURE_DIR):
        print(f"Warning: '{TEXTURE_DIR}' not found. Create a folder named 'textures' next to the script and add 'close.png' and 'minimize.png' (32x32) and button1/2/3.png (40x40).")

    w = CustomPopup()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()