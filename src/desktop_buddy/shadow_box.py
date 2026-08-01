import argparse
import random
import signal
import sys
import time
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from desktop_buddy.sprite import Sprite


@dataclass(frozen=True)
class DurationRange:
    minimum: float
    maximum: float

    @classmethod
    def from_config(
        cls,
        value: object,
        default_minimum: float,
        default_maximum: float,
    ) -> "DurationRange":
        if isinstance(value, list) and len(value) == 2:
            minimum = float(value[0])
            maximum = float(value[1])
            return cls(min(minimum, maximum), max(minimum, maximum))

        return cls(default_minimum, default_maximum)

    def choose(self) -> float:
        return random.uniform(self.minimum, self.maximum)


@dataclass(frozen=True)
class ShadowBoxMotion:
    walk_speed: float
    run_speed: float
    idle_seconds: DurationRange
    walk_seconds: DurationRange
    run_seconds: DurationRange

    @classmethod
    def from_config(cls, config: dict[str, object]) -> "ShadowBoxMotion":
        walk_speed = float(config.get("walk_speed", 42.0))
        run_speed = float(config.get("run_speed", 90.0))
        idle_seconds = DurationRange.from_config(
            config.get("idle_seconds"),
            1.5,
            4.0,
        )
        walk_seconds = DurationRange.from_config(
            config.get("walk_seconds"),
            2.5,
            5.0,
        )
        run_seconds = DurationRange.from_config(
            config.get("run_seconds"),
            0.9,
            1.8,
        )
        return cls(
            walk_speed=walk_speed,
            run_speed=run_speed,
            idle_seconds=idle_seconds,
            walk_seconds=walk_seconds,
            run_seconds=run_seconds,
        )


class ShadowBoxWindow(QWidget):
    def __init__(self, sprite_name: str = "shadow_box") -> None:
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

        self._motion = ShadowBoxMotion.from_config(self.sprite.shadow_box_config())
        self._state_names = {
            "idle": self.sprite.first_available_state("idle"),
            "walk": self.sprite.first_available_state("walk", "idle"),
            "run": self.sprite.first_available_state("run", "walk", "idle"),
            "fall": self.sprite.first_available_state("fall", "drag", "idle"),
            "hurt": self.sprite.first_available_state(
                "hurt",
                "happy",
                "excited",
                "idle",
            ),
        }

        first_frame = self.sprite.current_frame()
        self._actor_x = float(self.sprite.actor_start_x(first_frame))
        self._facing_right = self.sprite.starts_facing_right()
        self._active_behavior = "idle"
        self._behavior_remaining = 0.0
        self._hurt_remaining = 0.0
        self._resume_behavior = "idle"
        self._resume_remaining = 0.0

        self._dragging = False
        self._drag_offset = QPoint()
        self._press_pos = QPoint()
        self._drag_threshold = 5
        self._press_on_sprite = False

        self._last_time = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        self._move_to_corner()
        self._queue_behavior("idle")
        self.show()

    def _move_to_corner(self) -> None:
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x_position = screen_geometry.width() - self.width() - 20
        y_position = screen_geometry.height() - self.height() - 20
        self.move(x_position, y_position)

    def _display_frame(self):
        return self.sprite.current_frame(facing_left=not self._facing_right)

    def _actor_position(self, frame) -> QPoint:
        x_position = int(round(self._actor_x))
        y_position = self.sprite.actor_y(frame)
        return QPoint(x_position, y_position)

    def _actor_rect(self) -> QRect:
        frame = self._display_frame()
        position = self._actor_position(frame)
        return QRect(position, frame.size())

    def _queue_behavior(self, behavior: str) -> None:
        self._active_behavior = behavior

        if behavior == "walk":
            duration = self._motion.walk_seconds.choose()
            state_name = self._state_names["walk"]
        elif behavior == "run":
            duration = self._motion.run_seconds.choose()
            state_name = self._state_names["run"]
        else:
            duration = self._motion.idle_seconds.choose()
            state_name = self._state_names["idle"]

        self._behavior_remaining = duration
        self.sprite.set_state(state_name)
        self._turn_back_into_bounds()

    def _turn_back_into_bounds(self) -> None:
        frame = self._display_frame()
        min_x, max_x = self.sprite.actor_bounds(frame)
        current_x = int(round(self._actor_x))
        if current_x <= min_x:
            self._facing_right = True
            return

        if current_x >= max_x:
            self._facing_right = False

    def _choose_next_behavior(self) -> None:
        roll = random.random()
        if roll < 0.35:
            self._queue_behavior("idle")
            return

        if roll < 0.8:
            self._queue_behavior("walk")
            return

        self._queue_behavior("run")

    def _begin_hurt(self) -> None:
        self._resume_behavior = self._active_behavior
        self._resume_remaining = max(self._behavior_remaining, 0.25)
        self._hurt_remaining = self.sprite.state_duration(self._state_names["hurt"]) or 0.6
        self.sprite.set_state(self._state_names["hurt"])

    def _resume_after_hurt(self) -> None:
        behavior = self._resume_behavior
        remaining = self._resume_remaining
        self._resume_behavior = "idle"
        self._resume_remaining = 0.0

        self._active_behavior = behavior
        self._behavior_remaining = remaining
        self.sprite.set_state(self._state_names[behavior])

    def _move_actor(self, dt: float) -> None:
        if self._active_behavior == "walk":
            speed = self._motion.walk_speed
        else:
            speed = self._motion.run_speed

        direction = 1.0 if self._facing_right else -1.0
        next_x = self._actor_x + (speed * dt * direction)

        frame = self._display_frame()
        min_x, max_x = self.sprite.actor_bounds(frame)

        if next_x <= min_x:
            self._actor_x = float(min_x)
            self._facing_right = True
            return

        if next_x >= max_x:
            self._actor_x = float(max_x)
            self._facing_right = False
            return

        self._actor_x = next_x

    def _update_behavior(self, dt: float) -> None:
        if self._dragging:
            if self.sprite.state != self._state_names["fall"]:
                self.sprite.set_state(self._state_names["fall"])
            return

        if self._hurt_remaining > 0:
            self._hurt_remaining = max(0.0, self._hurt_remaining - dt)
            if self._hurt_remaining == 0:
                self._resume_after_hurt()
            return

        self._behavior_remaining -= dt
        if self._active_behavior in {"walk", "run"}:
            self._move_actor(dt)

        if self._behavior_remaining <= 0:
            self._choose_next_behavior()

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now
        self._update_behavior(dt)
        self.sprite.update(dt)
        self.update()

    def _paint_fallback_box(self, painter: QPainter) -> None:
        outer_rect = self.rect().adjusted(8, 8, -8, -8)
        inner_rect = outer_rect.adjusted(12, 12, -12, -12)
        back_rect = inner_rect.adjusted(10, 10, -10, -10)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.drawRoundedRect(outer_rect.adjusted(4, 8, 4, 10), 20, 20)

        frame_color = QColor(110, 81, 56, 240)
        panel_color = QColor(43, 31, 24, 225)
        accent_color = QColor(187, 156, 118, 120)

        painter.setBrush(frame_color)
        painter.drawRoundedRect(outer_rect, 20, 20)

        painter.setBrush(panel_color)
        painter.drawRoundedRect(inner_rect, 14, 14)

        pen = QPen(accent_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(back_rect, 10, 10)

        shelf_top = back_rect.bottom() - 18
        shelf_color = QColor(82, 59, 42, 230)
        painter.setPen(Qt.NoPen)
        painter.setBrush(shelf_color)
        painter.drawRoundedRect(
            QRect(back_rect.left() + 16, shelf_top, back_rect.width() - 32, 12),
            6,
            6,
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        base_layer, base_position = self.sprite.base()
        if base_layer and not base_layer.isNull():
            painter.drawPixmap(base_position, base_layer)
        else:
            self._paint_fallback_box(painter)

        frame = self._display_frame()
        actor_position = self._actor_position(frame)
        painter.drawPixmap(actor_position, frame)

        overlay_layer, overlay_position = self.sprite.overlay()
        if overlay_layer and not overlay_layer.isNull():
            painter.drawPixmap(overlay_position, overlay_layer)

        painter.end()

    def _is_sprite_hit(self, position: QPoint) -> bool:
        actor_rect = self._actor_rect()
        if not actor_rect.contains(position):
            return False

        frame = self._display_frame()
        local_x = position.x() - actor_rect.x()
        local_y = position.y() - actor_rect.y()
        image = frame.toImage()
        pixel_color = image.pixelColor(local_x, local_y)
        return pixel_color.alpha() > 0

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return

        self._dragging = False
        self._press_pos = event.pos()
        self._press_on_sprite = self._is_sprite_hit(event.pos())
        self._drag_offset = (
            event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not event.buttons() & Qt.LeftButton:
            return

        distance = (event.pos() - self._press_pos).manhattanLength()
        if not self._dragging and distance > self._drag_threshold:
            self._dragging = True
            self._hurt_remaining = 0.0
            self.sprite.set_state(self._state_names["fall"])

        if not self._dragging:
            return

        new_position = event.globalPosition().toPoint() - self._drag_offset
        self.move(new_position)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return

        if self._dragging:
            self._dragging = False
            self._queue_behavior("idle")
            return

        if self._press_on_sprite and self._is_sprite_hit(event.pos()):
            self._begin_hurt()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction("Exit")
        action = menu.exec(event.globalPos())
        if action and action.text() == "Exit":
            QApplication.quit()


def main() -> None:
    parser = argparse.ArgumentParser(prog="desktop-buddy-shadow-box")
    parser.add_argument(
        "--sprite",
        default="shadow_box",
        help="Name of the sprite set to load from src/desktop_buddy/sprites/",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = ShadowBoxWindow(args.sprite)

    def _sigint_handler(signum, frame) -> None:
        app.quit()

    signal.signal(signal.SIGINT, _sigint_handler)

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
