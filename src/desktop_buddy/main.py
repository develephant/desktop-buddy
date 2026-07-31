import argparse
import sys
import time

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .sprite import Sprite


class ToyWindow(QWidget):
    def __init__(self, sprite_name: str = "default") -> None:
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self.sprite = Sprite(sprite_name)
        self.setFixedSize(*self.sprite.size())

        self._dragging = False
        self._drag_offset = QPoint()
        self._press_pos = QPoint()
        self._drag_threshold = 5

        self._last_time = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() - self.width() - 20,
            screen.height() - self.height() - 20,
        )

        self.show()

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now
        self.sprite.update(dt)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        base, base_pos = self.sprite.base()
        if base and not base.isNull():
            painter.drawPixmap(base_pos, base)

        painter.drawPixmap(QPoint(0, 0), self.sprite.current_frame())

        overlay, overlay_pos = self.sprite.overlay()
        if overlay and not overlay.isNull():
            painter.drawPixmap(overlay_pos, overlay)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._press_pos = event.pos()
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton:
            delta = (event.pos() - self._press_pos).manhattanLength()
            if not self._dragging and delta > self._drag_threshold:
                self._dragging = True
            if self._dragging:
                new_pos = event.globalPosition().toPoint() - self._drag_offset
                self.move(new_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if not self._dragging:
                self.sprite.set_state("happy")
            self._dragging = False

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction("Exit")
        action = menu.exec(event.globalPosition().toPoint())
        if action and action.text() == "Exit":
            self.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="desktop-buddy")
    parser.add_argument(
        "--sprite",
        default="default",
        help="Name of the sprite set to load from src/desktop_buddy/sprites/",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = ToyWindow(args.sprite)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
