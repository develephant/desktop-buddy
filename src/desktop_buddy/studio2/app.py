"""Gradio front-end for Desktop Buddy Studio 2."""

import os
from pathlib import Path

import gradio as gr

from .project import Studio2Project
from .sprite_io import build_exe, import_sprite_directory, render_frame, render_gif, save_sprite
from desktop_buddy.studio.project import SpriteProject


def _resolve_source_root(file_list: list[str] | None) -> Path:
    """Best-effort resolution of the directory selected by a gr.File(directory)."""
    if not file_list:
        raise ValueError("No sprites directory selected.")

    paths = [Path(p) for p in file_list if Path(p).is_file()]
    if not paths:
        return Path(file_list[0])

    # If a manifest is in the list, its parent is the root.
    for p in paths:
        if p.name.lower() in ("sprite.json", "sprites.json"):
            return p.parent

    common = Path(os.path.commonpath([str(p) for p in paths]))
    if (common / "sprite.json").is_file() or (common / "sprites.json").is_file():
        return common

    # If the common directory contains subdirectories, it's likely the selected root.
    if any(p.is_dir() for p in common.iterdir()):
        return common

    # Otherwise the common directory is a single state subfolder; step up one level.
    return common.parent


def _load_help() -> str:
    help_path = Path(__file__).with_name("help.md")
    if help_path.is_file():
        return help_path.read_text(encoding="utf-8")
    return "Help file not found."


def on_import_and_save(
    name: str,
    kind: str,
    sprites_files: list[str] | None,
    icon_file: str | None,
    sprites_path_text: str,
) -> tuple:
    """Import a sprites directory, save it into the project, and seed the Sprites tab."""
    if sprites_files:
        source = _resolve_source_root(sprites_files)
    elif sprites_path_text.strip():
        source = Path(sprites_path_text.strip())
    else:
        raise gr.Error("Select a sprites directory or enter its path.")

    studio = import_sprite_directory(source, name or source.name, kind)
    if icon_file:
        studio.icon_path = icon_file

    sprite_dir = save_sprite(studio)
    first_state = studio.project.default_state
    state_data = studio.project.states[first_state]

    preview = render_frame(studio, first_state, 0)
    return (
        studio,
        gr.update(choices=list(studio.project.states.keys()), value=first_state),
        gr.update(maximum=max(0, len(state_data.frames) - 1), value=0),
        gr.update(value=state_data.fps or studio.project.fps),
        gr.update(value=state_data.loop),
        preview,
        f"Saved **{studio.project.name}** to `{sprite_dir}`.",
    )


def on_state_change(studio: Studio2Project, state_name: str) -> tuple:
    if not state_name or state_name not in studio.project.states:
        return None, gr.update(), gr.update(), gr.update()

    state_data = studio.project.states[state_name]
    preview = render_frame(studio, state_name, 0)
    return (
        preview,
        gr.update(maximum=max(0, len(state_data.frames) - 1), value=0),
        gr.update(value=state_data.fps or studio.project.fps),
        gr.update(value=state_data.loop),
    )


def on_frame_change(studio: Studio2Project, state_name: str, frame_index: int) -> Path:
    return render_frame(studio, state_name, frame_index)


def on_prev(frame_index: int) -> gr.update:
    return gr.update(value=max(0, frame_index - 1))


def on_next(studio: Studio2Project, state_name: str, frame_index: int) -> gr.update:
    frame_count = len(studio.project.states[state_name].frames) if state_name in studio.project.states else 1
    return gr.update(value=min(max(0, frame_count - 1), frame_index + 1))


def on_play(studio: Studio2Project, state_name: str) -> str:
    return render_gif(studio, state_name)


def on_stop(studio: Studio2Project, state_name: str) -> Path:
    return render_frame(studio, state_name, 0)


def on_fps_change(studio: Studio2Project, state_name: str, fps: float) -> tuple:
    if state_name in studio.project.states:
        studio.project.states[state_name].fps = float(fps)
    return studio, f"FPS for `{state_name}` set to {fps}."


def on_loop_change(studio: Studio2Project, state_name: str, loop: bool) -> tuple:
    if state_name in studio.project.states:
        studio.project.states[state_name].loop = bool(loop)
    return studio, f"Loop for `{state_name}` set to {loop}."


def on_save(studio: Studio2Project) -> str:
    sprite_dir = save_sprite(studio)
    return f"Saved **{studio.project.name}** to `{sprite_dir}`."


def on_build(studio: Studio2Project) -> str:
    exe_path = build_exe(studio)
    return f"Built `{exe_path}`."


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Desktop Buddy Studio 2") as demo:
        studio = gr.State(Studio2Project(SpriteProject()))

        with gr.Tabs():
            with gr.Tab("Buddy"):
                gr.Markdown("## Buddy Settings")
                with gr.Row():
                    name_tb = gr.Textbox(label="Buddy Name", value="my_pet", scale=1)
                    type_dd = gr.Dropdown(
                        label="Buddy Type",
                        choices=["desktop_buddy", "shadow_box"],
                        value="desktop_buddy",
                        scale=1,
                    )
                with gr.Row():
                    sprites_file = gr.File(
                        label="Add Sprites Directory",
                        file_count="directory",
                        scale=1,
                    )
                    icon_file = gr.File(
                        label="Add Icon File",
                        file_count="single",
                        file_types=[".ico"],
                        scale=1,
                    )
                sprites_path_text = gr.Textbox(
                    label="Or enter sprites directory path",
                    placeholder="E:\\Projects\\...\\my_buddy",
                    scale=1,
                )
                save_buddy_btn = gr.Button("Save Desktop Buddy", variant="primary")
                buddy_status = gr.Markdown("")

            with gr.Tab("Sprites"):
                with gr.Row():
                    with gr.Column(scale=2):
                        preview_img = gr.Image(
                            label="Sprite Preview",
                            type="filepath",
                            image_mode="RGBA",
                            height=400,
                        )
                        with gr.Row():
                            prev_btn = gr.Button("◀ Prev")
                            play_btn = gr.Button("▶ Play")
                            stop_btn = gr.Button("Stop")
                            next_btn = gr.Button("Next ▶")
                        frame_slider = gr.Slider(
                            label="Frame",
                            minimum=0,
                            maximum=1,
                            step=1,
                            value=0,
                        )
                    with gr.Column(scale=1):
                        state_dd = gr.Dropdown(label="Sprite State", choices=[])
                        fps_slider = gr.Slider(
                            label="Sprite FPS",
                            minimum=1,
                            maximum=30,
                            step=1,
                            value=8,
                        )
                        loop_cb = gr.Checkbox(label="Loop", value=True)
                        save_sprites_btn = gr.Button("Save Desktop Buddy", variant="primary")
                        build_btn = gr.Button("Build Desktop Buddy", variant="primary")
                        sprites_status = gr.Markdown("")

            with gr.Tab("Help"):
                gr.Markdown(_load_help())

        save_buddy_btn.click(
            on_import_and_save,
            inputs=[name_tb, type_dd, sprites_file, icon_file, sprites_path_text],
            outputs=[
                studio,
                state_dd,
                frame_slider,
                fps_slider,
                loop_cb,
                preview_img,
                buddy_status,
            ],
        )

        state_dd.change(
            on_state_change,
            inputs=[studio, state_dd],
            outputs=[preview_img, frame_slider, fps_slider, loop_cb],
        )

        frame_slider.change(
            on_frame_change,
            inputs=[studio, state_dd, frame_slider],
            outputs=preview_img,
        )

        prev_btn.click(on_prev, inputs=frame_slider, outputs=frame_slider)
        next_btn.click(on_next, inputs=[studio, state_dd, frame_slider], outputs=frame_slider)
        play_btn.click(on_play, inputs=[studio, state_dd], outputs=preview_img)
        stop_btn.click(on_stop, inputs=[studio, state_dd], outputs=preview_img)

        fps_slider.change(
            on_fps_change,
            inputs=[studio, state_dd, fps_slider],
            outputs=[studio, buddy_status],
        )
        loop_cb.change(
            on_loop_change,
            inputs=[studio, state_dd, loop_cb],
            outputs=[studio, buddy_status],
        )

        save_sprites_btn.click(on_save, inputs=studio, outputs=sprites_status)
        build_btn.click(on_build, inputs=studio, outputs=sprites_status)

    return demo


def main() -> None:
    demo = build_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7862,
        footer_links=[],
    )


if __name__ == "__main__":
    main()
