"""Gradio front-end for creating and editing Desktop Buddy sprites."""

import tempfile

import gradio as gr
from PIL import Image

from . import sprite_io
from .canvas import editor_value_to_image, image_to_editor_value
from .project import SpriteProject

# Frames are always edited on a fixed-resolution working canvas, then
# nearest-neighbor downscaled to the project's chosen (smaller) square size
# on save -- this keeps freehand strokes from gr.ImageEditor usable at small
# sprite sizes without needing a custom pixel-grid canvas.
EDITOR_SCALE = 256
SIZE_CHOICES = ["32", "64", "128", "256"]


def _state_names(project: SpriteProject) -> list[str]:
    return list(project.states.keys())


def _thumbnails(project: SpriteProject, state_name: str | None) -> list[Image.Image]:
    if not state_name or state_name not in project.states:
        return []
    return list(project.states[state_name].frames)


def _pick_state(project: SpriteProject, preferred: str | None) -> str | None:
    if preferred and preferred in project.states:
        return preferred
    names = _state_names(project)
    return names[0] if names else None


def _editor_value_for(project: SpriteProject, state_name: str | None, frame_index: int) -> Image.Image:
    frames = project.states[state_name].frames if state_name in project.states else []
    if not frames:
        return image_to_editor_value(project.blank_frame(), EDITOR_SCALE)
    frame_index = max(0, min(frame_index, len(frames) - 1))
    return image_to_editor_value(frames[frame_index], EDITOR_SCALE)


def _refresh(project: SpriteProject, state_name: str | None, frame_index: int, message: str = ""):
    """Shared return bundle after any mutation: refreshes every dependent widget."""
    state_name = _pick_state(project, state_name)
    thumbs = _thumbnails(project, state_name)
    frame_index = max(0, min(frame_index, len(thumbs) - 1)) if thumbs else 0
    state_obj = project.states.get(state_name) if state_name else None
    return (
        project,
        state_name,
        frame_index,
        gr.update(choices=_state_names(project), value=state_name),
        thumbs,
        _editor_value_for(project, state_name, frame_index),
        state_obj.loop if state_obj else True,
        state_obj.fps if state_obj else None,
        message,
    )


def on_new_project(project: SpriteProject, name: str, size: str):
    size_i = int(size)
    project = SpriteProject(name=name.strip() or "my_pet", width=size_i, height=size_i)
    project.add_state("idle")
    return _refresh(project, "idle", 0, f"Started new project '{project.name}' at {size_i}x{size_i}.")


def on_load_sprite(project: SpriteProject, sprite_name: str):
    if not sprite_name:
        return _refresh(project, None, 0, "Pick a sprite to load first.")
    try:
        project = sprite_io.load_sprite(sprite_name)
    except (FileNotFoundError, OSError, ValueError) as exc:
        return _refresh(project, None, 0, f"Could not load '{sprite_name}': {exc}")
    return _refresh(project, project.default_state, 0, f"Loaded sprite '{sprite_name}'.")


def on_resize_canvas(project: SpriteProject, state_name: str, frame_index: int, size: str):
    project.resize_canvas(int(size))
    return _refresh(project, state_name, frame_index, f"Canvas resized to {size}x{size}.")


def on_add_state(project: SpriteProject, new_name: str, state_name: str, frame_index: int):
    try:
        project.add_state(new_name)
        return _refresh(project, new_name, 0, f"Added state '{new_name}'.")
    except ValueError as exc:
        return _refresh(project, state_name, frame_index, str(exc))


def on_delete_state(project: SpriteProject, state_name: str, frame_index: int):
    if not state_name:
        return _refresh(project, state_name, frame_index, "No state selected.")
    if len(project.states) <= 1:
        return _refresh(project, state_name, frame_index, "Keep at least one state.")
    project.remove_state(state_name)
    return _refresh(project, None, 0, f"Deleted state '{state_name}'.")


def on_select_state(project: SpriteProject, state_name: str):
    return _refresh(project, state_name, 0)


def on_select_frame(project: SpriteProject, state_name: str, evt: gr.SelectData):
    return _refresh(project, state_name, evt.index)


def on_add_frame(project: SpriteProject, state_name: str, frame_index: int):
    if not state_name:
        return _refresh(project, state_name, frame_index, "Add a state first.")
    project.add_frame(state_name)
    new_index = len(project.states[state_name].frames) - 1
    return _refresh(project, state_name, new_index, "Frame added.")


def on_duplicate_frame(project: SpriteProject, state_name: str, frame_index: int):
    if not state_name or not project.states.get(state_name):
        return _refresh(project, state_name, frame_index, "Nothing to duplicate.")
    project.duplicate_frame(state_name, frame_index)
    return _refresh(project, state_name, frame_index + 1, "Frame duplicated.")


def on_delete_frame(project: SpriteProject, state_name: str, frame_index: int):
    if not state_name:
        return _refresh(project, state_name, frame_index, "No state selected.")
    try:
        project.delete_frame(state_name, frame_index)
        return _refresh(project, state_name, frame_index, "Frame deleted.")
    except (ValueError, IndexError) as exc:
        return _refresh(project, state_name, frame_index, str(exc))


def on_move_frame(project: SpriteProject, state_name: str, frame_index: int, delta: int):
    if not state_name:
        return _refresh(project, state_name, frame_index, "No state selected.")
    new_index = project.move_frame(state_name, frame_index, delta)
    return _refresh(project, state_name, new_index)


def on_save_frame(project: SpriteProject, state_name: str, frame_index: int, editor_value):
    if not state_name:
        return _refresh(project, state_name, frame_index, "No state selected.")
    image = editor_value_to_image(editor_value, project.width)
    project.set_frame(state_name, frame_index, image)
    return _refresh(project, state_name, frame_index, "Frame saved.")


def on_apply_state_settings(
    project: SpriteProject, state_name: str, frame_index: int, loop: bool, fps: float | None
):
    if not state_name or state_name not in project.states:
        return _refresh(project, state_name, frame_index, "No state selected.")
    state = project.states[state_name]
    state.loop = bool(loop)
    state.fps = float(fps) if fps else None
    return _refresh(project, state_name, frame_index, f"Updated '{state_name}' settings.")


def on_set_default_state(project: SpriteProject, state_name: str, frame_index: int):
    if not state_name:
        return _refresh(project, state_name, frame_index, "No state selected.")
    project.default_state = state_name
    return _refresh(project, state_name, frame_index, f"Default state set to '{state_name}'.")


def on_apply_statics(
    project: SpriteProject,
    state_name: str,
    frame_index: int,
    base_img,
    base_x,
    base_y,
    overlay_img,
    overlay_x,
    overlay_y,
):
    project.set_static("base", base_img, int(base_x or 0), int(base_y or 0))
    project.set_static("overlay", overlay_img, int(overlay_x or 0), int(overlay_y or 0))
    return _refresh(project, state_name, frame_index, "Static layers updated.")


def on_preview(project: SpriteProject, state_name: str):
    if not state_name or not project.states.get(state_name):
        return None, "Select a state with at least one frame first."

    state = project.states[state_name]
    fps = state.fps or project.fps or 8.0
    duration_ms = max(1, int(1000 / fps))

    base = project.statics.get("base")
    overlay = project.statics.get("overlay")
    composed = []
    for frame in state.frames:
        canvas = Image.new("RGBA", project.size, (0, 0, 0, 0))
        if base and base.image is not None:
            canvas.alpha_composite(base.image, (base.x, base.y))
        canvas.alpha_composite(frame, (0, 0))
        if overlay and overlay.image is not None:
            canvas.alpha_composite(overlay.image, (overlay.x, overlay.y))
        composed.append(canvas)

    tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
    composed[0].save(
        tmp.name,
        save_all=True,
        append_images=composed[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )
    return tmp.name, f"Previewing '{state_name}' at {fps:g} fps."


def on_export_to_sprites(project: SpriteProject):
    try:
        sprite_dir = sprite_io.export_sprite(project)
    except ValueError as exc:
        return f"Export failed: {exc}", gr.update()
    message = f"Exported to `{sprite_dir}`. Run with `uv run desktop-buddy --sprite {project.name}`."
    return message, gr.update(choices=sprite_io.list_sprites())


def on_export_zip(project: SpriteProject):
    try:
        data = sprite_io.export_zip(project)
    except ValueError as exc:
        return None, f"Export failed: {exc}"
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.write(data)
    tmp.close()
    frame_count = sum(len(s.frames) for s in project.states.values())
    return tmp.name, f"Zip ready with {frame_count} frame(s)."


def build_app() -> gr.Blocks:
    initial_project = SpriteProject()
    initial_project.add_state("idle")

    with gr.Blocks(title="Create-A-Buddy Studio") as demo:
        gr.Markdown("# 🐾 Create-A-Buddy Studio\nDesign, animate, and export Desktop Buddy sprites.")

        project_state = gr.State(initial_project)
        active_state_name = gr.State("idle")
        active_frame_index = gr.State(0)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Project")
                sprite_name_tb = gr.Textbox(label="Sprite Name", value=initial_project.name)
                size_dd = gr.Dropdown(label="Canvas Size (square, px)", choices=SIZE_CHOICES, value="128")
                with gr.Row():
                    new_project_btn = gr.Button("New Project")
                    resize_btn = gr.Button("Resize Canvas")

                gr.Markdown("### Load Existing")
                load_dd = gr.Dropdown(label="Sprite", choices=sprite_io.list_sprites())
                load_btn = gr.Button("Load")

                gr.Markdown("### States")
                state_dd = gr.Dropdown(
                    label="Active State", choices=_state_names(initial_project), value="idle"
                )
                new_state_tb = gr.Textbox(label="New state name", placeholder="happy, sleep, nap...")
                with gr.Row():
                    add_state_btn = gr.Button("+ Add")
                    delete_state_btn = gr.Button("Delete")
                default_state_btn = gr.Button("Set as Default")
                loop_cb = gr.Checkbox(label="Loop", value=True)
                fps_num = gr.Number(label="FPS override (blank = global)", value=None)
                apply_state_btn = gr.Button("Apply State Settings")
                status_md = gr.Markdown("")

            with gr.Column(scale=3):
                with gr.Tab("Frames"):
                    gallery = gr.Gallery(
                        label="Frames (click to edit)",
                        columns=8,
                        height=140,
                        allow_preview=False,
                    )
                    with gr.Row():
                        add_frame_btn = gr.Button("+ Frame")
                        duplicate_frame_btn = gr.Button("Duplicate")
                        delete_frame_btn = gr.Button("Delete")
                        move_left_btn = gr.Button("◀ Move Left")
                        move_right_btn = gr.Button("Move Right ▶")
                    editor = gr.ImageEditor(
                        label="Frame Editor",
                        type="pil",
                        image_mode="RGBA",
                        value=image_to_editor_value(initial_project.blank_frame(), EDITOR_SCALE),
                        height=EDITOR_SCALE + 60,
                    )
                    save_frame_btn = gr.Button("💾 Save to Frame", variant="primary")

                with gr.Tab("Preview"):
                    preview_btn = gr.Button("▶ Play Active State")
                    preview_img = gr.Image(label="Preview", interactive=False)

                with gr.Tab("Statics"):
                    gr.Markdown("Optional non-animated layers drawn behind/in front of every frame.")
                    with gr.Row():
                        with gr.Column():
                            base_img = gr.Image(label="Base layer", type="pil", image_mode="RGBA")
                            base_x = gr.Number(label="Base X", value=0)
                            base_y = gr.Number(label="Base Y", value=0)
                        with gr.Column():
                            overlay_img = gr.Image(label="Overlay layer", type="pil", image_mode="RGBA")
                            overlay_x = gr.Number(label="Overlay X", value=0)
                            overlay_y = gr.Number(label="Overlay Y", value=0)
                    apply_statics_btn = gr.Button("Apply Static Layers")

                with gr.Tab("Export"):
                    gr.Markdown(
                        "Export writes PNG frames + `sprite.json` matching the format "
                        "`desktop_buddy.sprite.Sprite` expects."
                    )
                    export_btn = gr.Button("Export into src/desktop_buddy/sprites/<name>/", variant="primary")
                    export_status = gr.Markdown("")
                    download_btn = gr.Button("Prepare ZIP Download")
                    download_file = gr.File(label="Download", interactive=False)

        refresh_outputs = [
            project_state,
            active_state_name,
            active_frame_index,
            state_dd,
            gallery,
            editor,
            loop_cb,
            fps_num,
            status_md,
        ]

        new_project_btn.click(
            on_new_project, inputs=[project_state, sprite_name_tb, size_dd], outputs=refresh_outputs
        )
        resize_btn.click(
            on_resize_canvas,
            inputs=[project_state, active_state_name, active_frame_index, size_dd],
            outputs=refresh_outputs,
        )
        load_btn.click(on_load_sprite, inputs=[project_state, load_dd], outputs=refresh_outputs)
        add_state_btn.click(
            on_add_state,
            inputs=[project_state, new_state_tb, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        delete_state_btn.click(
            on_delete_state,
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        state_dd.change(on_select_state, inputs=[project_state, state_dd], outputs=refresh_outputs)
        gallery.select(
            on_select_frame, inputs=[project_state, active_state_name], outputs=refresh_outputs
        )
        add_frame_btn.click(
            on_add_frame,
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        duplicate_frame_btn.click(
            on_duplicate_frame,
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        delete_frame_btn.click(
            on_delete_frame,
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        move_left_btn.click(
            lambda project, state_name, frame_index: on_move_frame(project, state_name, frame_index, -1),
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        move_right_btn.click(
            lambda project, state_name, frame_index: on_move_frame(project, state_name, frame_index, 1),
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        save_frame_btn.click(
            on_save_frame,
            inputs=[project_state, active_state_name, active_frame_index, editor],
            outputs=refresh_outputs,
        )
        apply_state_btn.click(
            on_apply_state_settings,
            inputs=[project_state, active_state_name, active_frame_index, loop_cb, fps_num],
            outputs=refresh_outputs,
        )
        default_state_btn.click(
            on_set_default_state,
            inputs=[project_state, active_state_name, active_frame_index],
            outputs=refresh_outputs,
        )
        apply_statics_btn.click(
            on_apply_statics,
            inputs=[
                project_state,
                active_state_name,
                active_frame_index,
                base_img,
                base_x,
                base_y,
                overlay_img,
                overlay_x,
                overlay_y,
            ],
            outputs=refresh_outputs,
        )
        preview_btn.click(on_preview, inputs=[project_state, active_state_name], outputs=[preview_img, status_md])
        export_btn.click(on_export_to_sprites, inputs=[project_state], outputs=[export_status, load_dd])
        download_btn.click(on_export_zip, inputs=[project_state], outputs=[download_file, export_status])

    return demo


def main() -> None:
    demo = build_app()
    demo.launch()


if __name__ == "__main__":
    main()
