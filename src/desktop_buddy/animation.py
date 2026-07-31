import random
from typing import Optional

from PySide6.QtCore import QObject, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QApplication, QWidget


class Animator(QObject):
    def __init__(self, target: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._target = target
        self._anim: Optional[QPropertyAnimation] = None

    def _screen_x_bounds(self) -> tuple[int, int]:
        screen = QApplication.primaryScreen().availableGeometry()
        min_x = screen.left()
        max_x = screen.left() + screen.width() - self._target.width()
        if max_x < min_x:
            max_x = min_x
        return min_x, max_x

    def _clamp_x(self, x: int) -> int:
        min_x, max_x = self._screen_x_bounds()
        return max(min_x, min(x, max_x))

    def move_to(
        self,
        x: int,
        random: bool = False,
        ease_type: QEasingCurve.Type = QEasingCurve.Type.InOutQuad,
        ease_duration: int = 500,
    ) -> int:
        """
        Animate the target widget to the given x position.

        If `random` is True, `x` is ignored and a random on-screen x is chosen.
        Returns the actual destination x.
        """
        min_x, max_x = self._screen_x_bounds()

        if random:
            x = random.randint(min_x, max_x)
        else:
            x = self._clamp_x(x)

        if self._anim is not None:
            self._anim.stop()
            self._anim.deleteLater()

        anim = QPropertyAnimation(self._target, b"pos", self)
        anim.setStartValue(self._target.pos())
        anim.setEndValue(QPoint(x, self._target.y()))
        anim.setDuration(ease_duration)
        anim.setEasingCurve(QEasingCurve(ease_type))

        def _on_finished() -> None:
            if self._anim is anim:
                self._anim = None
            anim.deleteLater()

        anim.finished.connect(_on_finished)
        self._anim = anim
        anim.start()

        return x
