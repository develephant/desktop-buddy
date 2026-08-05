"""Gradio front-end for creating Desktop Buddy sprite projects via folder import."""

import tempfile
from pathlib import Path

import gradio as gr
from PIL import Image

from . import sprite_io
from .project import SpriteProject

BUDDY_TYPES = ["static", "shadow-box"]
SIZE_CHOICES = ["32", "64", "128", "256"]


def on_create_project(buddy_name: str, buddy_type: str, canvas_size: str) -> tuple:
    """Initialize a new project with buddy type and name."""
    try:
        size = int(canvas_size)
        name = buddy_name.strip() or "my_buddy"
        
        project = SpriteProject(
            name=name,
            width=size,
            height=size,
            buddy_type=buddy_type,
        )
        
        msg = f"OK: Created '{name}' ({buddy_type}, {size}x{size})"
        return project, msg
    except Exception as exc:
        return SpriteProject(), f"Error: {exc}"


def on_detect_states(folder_path: str) -> tuple:
    """Scan folder for state subfolders."""
    try:
        if not folder_path:
            return [], "Select a folder first."
        
        states = sprite_io.auto_detect_states(folder_path)
        if not states:
            return [], "No state subfolders found. Expected: idle/, walk/, happy/, etc."
        
        msg = f"Found {len(states)} state(s): {', '.join(states)}"
        return states, msg
    except Exception as exc:
        return [], f"Error: {exc}"


def on_import_states(project: SpriteProject, folder_path: str, detected_states: list) -> tuple:
    """Import animation frames from folder structure."""
    try:
        if not folder_path:
            return project, "Select a folder first."
        
        if not detected_states:
            return project, "No states to import. Detect states first."
        
        results = sprite_io.import_from_folder(project, folder_path)
        
        state_list = "\n".join(
            f"  - {state}: {count} frame(s)"
            for state, count in sorted(results.items())
        )
        msg = f"Imported:\n{state_list}"
        
        return project, msg
    except Exception as exc:
        return project, f"Error: {exc}"


def on_set_state_fps(project: SpriteProject, state_name: str, fps: float | None) -> tuple:
    """Set FPS for a state."""
    try:
        if not state_name or state_name not in project.states:
            return project, "Select a state first."
        
        project.states[state_name].fps = fps
        msg = f"Set FPS for '{state_name}' to {fps or 'default'}."
        return project, msg
    except Exception as exc:
        return project, f"Error: {exc}"


def on_set_state_loop(project: SpriteProject, state_name: str, loop: bool) -> tuple:
    """Set loop toggle for a state."""
    try:
        if not state_name or state_name not in project.states:
            return project, "Select a state first."
        
        project.states[state_name].loop = loop
        loop_text = "loop enabled" if loop else "no loop"
        msg = f"Set '{state_name}' to {loop_text}."
        return project, msg
    except Exception as exc:
        return project, f"Error: {exc}"


def on_preview_state(project: SpriteProject, state_name: str) -> tuple:
    """Generate animated preview GIF for a state."""
    try:
        if not state_name or state_name not in project.states:
            return None, "Select a state first."
        
        state = project.states[state_name]
        fps = state.fps or project.fps or 8.0
        duration_ms = max(1, int(1000 / fps))
        
        frames = []
        for frame in state.frames:
            frame_copy = frame.copy() if frame else project.blank_frame()
            frames.append(frame_copy)
        
        if not frames:
            return None, "No frames in this state."
        
        tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
        frames[0].save(
            tmp.name,
            save_all=True,
            append_images=frames[1:] if len(frames) > 1 else [],
            duration=duration_ms,
            loop=0 if state.loop else 1,
            disposal=2,
        )
        
        msg = f"Preview: '{state_name}' at {fps:g} fps ({len(frames)} frame(s))."
        return tmp.name, msg
    except Exception as exc:
        return None, f"Error: {exc}"


def on_set_background(project: SpriteProject, bg_type: str, image) -> tuple:
    """Set day or night background."""
    try:
        if image is None:
            return project, "Select an image first."
        
        if isinstance(image, dict):
            image = image.get("composite") or image.get("background")
        
        img = Image.open(image) if isinstance(image, str) else image
        img = project._normalize(img)
        
        project.backgrounds[bg_type] = type(project.backgrounds[bg_type])(
            image=img,
            x=project.backgrounds[bg_type].x,
            y=project.backgrounds[bg_type].y,
        )
        
        msg = f"Set {bg_type} background."
        return project, msg
    except Exception as exc:
        return project, f"Error: {exc}"


def on_set_foreground(project: SpriteProject, image) -> tuple:
    """Set foreground layer."""
    try:
        if image is None:
            return project, "Select an image first."
        
        if isinstance(image, dict):
            image = image.get("composite") or image.get("background")
        
        img = Image.open(image) if isinstance(image, str) else image
        img = project._normalize(img)
        
        project.foreground = type(project.foreground)(
            image=img,
            x=project.foreground.x,
            y=project.foreground.y,
        )
        
        msg = "Set foreground layer."
        return project, msg
    except Exception as exc:
        return project, f"Error: {exc}"


def on_set_icon(project: SpriteProject, icon_type: str, image) -> tuple:
    """Set icon file."""
    try:
        if image is None:
            project.icons[icon_type] = None
            msg = f"Cleared {icon_type} icon."
            return project, msg
        
        if isinstance(image, dict):
            image = image.get("composite") or image.get("background")
        
        img_path = image if isinstance(image, str) else str(image)
        project.icons[icon_type] = img_path
        
        msg = f"Set {icon_type} icon."
        return project, msg
    except Exception as exc:
        return project, f"Error: {exc}"


def on_export_sprite(project: SpriteProject) -> str:
    """Export project as sprite.json + PNGs."""
    try:
        if not project.states:
            return "No states to export. Import assets first."
        
        sprite_dir = sprite_io.export_sprite(project)
        msg = f"Exported to {sprite_dir}\n\nRun with:\nuv run desktop-buddy --sprite {project.name}"
        
        return msg
    except Exception as exc:
        return f"Export failed: {exc}"


def on_export_zip(project: SpriteProject) -> tuple:
    """Package as downloadable ZIP."""
    try:
        if not project.states:
            return None, "No states to export."
        
        data = sprite_io.export_zip(project)
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.write(data)
        tmp.close()
        
        frame_count = sum(len(s.frames) for s in project.states.values())
        msg = f"ZIP ready ({len(project.states)} state(s), {frame_count} frame(s))."
        
        return tmp.name, msg
    except Exception as exc:
        return None, f"Error: {exc}"


def build_app() -> gr.Blocks:
    initial_project = SpriteProject()

    with gr.Blocks(title="Desktop Buddy Studio") as demo:
        gr.Markdown(
            "# Buddy Studio\n"
            "Create animation sequences from organized asset folders."
        )

        project_state = gr.State(initial_project)

        with gr.Tabs():
            # TAB 1: Project Setup
            with gr.Tab("Project Setup"):
                gr.Markdown("**1. Create a new Desktop Buddy project**")
                
                with gr.Group():
                    buddy_name_tb = gr.Textbox(
                        label="Buddy Name",
                        value="my_buddy",
                        placeholder="e.g., fluffy, sparky",
                    )
                    buddy_type_radio = gr.Radio(
                        label="Buddy Type",
                        choices=BUDDY_TYPES,
                        value="static",
                    )
                    canvas_size_dd = gr.Dropdown(
                        label="Canvas Size (square, px)",
                        choices=SIZE_CHOICES,
                        value="128",
                    )
                    create_btn = gr.Button("Create Project", variant="primary")
                
                setup_status = gr.Markdown("")
                
                create_btn.click(
                    on_create_project,
                    inputs=[buddy_name_tb, buddy_type_radio, canvas_size_dd],
                    outputs=[project_state, setup_status],
                )

            # TAB 2: Asset Import
            with gr.Tab("Import Assets"):
                gr.Markdown(
                    "**2. Point to a folder with state subfolders**\n\n"
                    "Expected structure:\n"
                    "```\n"
                    "assets/\n"
                    "  idle/\n"
                    "    frame_0.png\n"
                    "    frame_1.png\n"
                    "  walk/\n"
                    "    frame_0.png\n"
                    "    frame_1.png\n"
                    "```"
                )
                
                with gr.Group():
                    folder_path_tb = gr.Textbox(
                        label="Folder Path",
                        placeholder="/path/to/assets",
                        interactive=True,
                    )
                    with gr.Row():
                        detect_btn = gr.Button("Detect States")
                        import_btn = gr.Button("Import Frames", variant="primary")
                
                detected_states = gr.State([])
                detect_status = gr.Markdown("")
                import_status = gr.Markdown("")
                
                detected_states_display = gr.Textbox(
                    label="Detected States",
                    interactive=False,
                    lines=4,
                )
                
                def on_detect(folder_path):
                    states, msg = on_detect_states(folder_path)
                    return states, msg, ", ".join(states) if states else "(none)"
                
                detect_btn.click(
                    on_detect,
                    inputs=[folder_path_tb],
                    outputs=[detected_states, detect_status, detected_states_display],
                )
                
                import_btn.click(
                    on_import_states,
                    inputs=[project_state, folder_path_tb, detected_states],
                    outputs=[project_state, import_status],
                )

            # TAB 3: Configuration
            with gr.Tab("Configure"):
                gr.Markdown("**3. Configure animation settings and layers**")
                
                with gr.Group():
                    gr.Markdown("### Animation Settings")
                    state_dd = gr.Dropdown(
                        label="Select State",
                        choices=[],
                    )
                    
                    with gr.Row():
                        fps_num = gr.Number(
                            label="FPS (blank = default 8)",
                            value=None,
                        )
                        loop_cb = gr.Checkbox(label="Loop", value=True)
                    
                    with gr.Row():
                        apply_fps_btn = gr.Button("Apply FPS")
                        apply_loop_btn = gr.Button("Apply Loop")
                        preview_btn = gr.Button("Preview")
                    
                    preview_img = gr.Image(label="Preview", interactive=False)
                    preview_status = gr.Markdown("")
                
                config_status = gr.Markdown("")

                with gr.Group():
                    gr.Markdown("### Backgrounds")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("**Day Background**")
                            day_bg_img = gr.Image(
                                label="Upload Day BG",
                                type="pil",
                                image_mode="RGBA",
                            )
                            apply_day_btn = gr.Button("Set Day BG")
                        
                        with gr.Column():
                            gr.Markdown("**Night Background**")
                            night_bg_img = gr.Image(
                                label="Upload Night BG",
                                type="pil",
                                image_mode="RGBA",
                            )
                            apply_night_btn = gr.Button("Set Night BG")

                with gr.Group():
                    gr.Markdown("### Foreground")
                    fg_img = gr.Image(
                        label="Upload Foreground",
                        type="pil",
                        image_mode="RGBA",
                    )
                    apply_fg_btn = gr.Button("Set Foreground")

                apply_fps_btn.click(
                    on_set_state_fps,
                    inputs=[project_state, state_dd, fps_num],
                    outputs=[project_state, config_status],
                )
                
                apply_loop_btn.click(
                    on_set_state_loop,
                    inputs=[project_state, state_dd, loop_cb],
                    outputs=[project_state, config_status],
                )
                
                preview_btn.click(
                    on_preview_state,
                    inputs=[project_state, state_dd],
                    outputs=[preview_img, preview_status],
                )
                
                apply_day_btn.click(
                    lambda p, img: on_set_background(p, "day", img),
                    inputs=[project_state, day_bg_img],
                    outputs=[project_state, config_status],
                )
                
                apply_night_btn.click(
                    lambda p, img: on_set_background(p, "night", img),
                    inputs=[project_state, night_bg_img],
                    outputs=[project_state, config_status],
                )
                
                apply_fg_btn.click(
                    on_set_foreground,
                    inputs=[project_state, fg_img],
                    outputs=[project_state, config_status],
                )

            # TAB 4: Build & Export
            with gr.Tab("Build & Export"):
                gr.Markdown("**4. Add icons and export your buddy**")
                
                with gr.Group():
                    gr.Markdown("### Icon Files")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("**Small Icon**")
                            small_icon = gr.Image(label="16x16", type="pil")
                            apply_small_btn = gr.Button("Set Small")
                        
                        with gr.Column():
                            gr.Markdown("**Medium Icon**")
                            medium_icon = gr.Image(label="32x32", type="pil")
                            apply_medium_btn = gr.Button("Set Medium")
                        
                        with gr.Column():
                            gr.Markdown("**Large Icon**")
                            large_icon = gr.Image(label="64x64", type="pil")
                            apply_large_btn = gr.Button("Set Large")

                with gr.Group():
                    gr.Markdown("### Export")
                    
                    with gr.Row():
                        export_btn = gr.Button("Export to Sprites", variant="primary")
                        download_btn = gr.Button("Download ZIP")
                    
                    export_status = gr.Markdown("")
                    download_file = gr.File(label="Download", interactive=False)

                apply_small_btn.click(
                    lambda p, img: on_set_icon(p, "small", img),
                    inputs=[project_state, small_icon],
                    outputs=[project_state],
                )
                
                apply_medium_btn.click(
                    lambda p, img: on_set_icon(p, "medium", img),
                    inputs=[project_state, medium_icon],
                    outputs=[project_state],
                )
                
                apply_large_btn.click(
                    lambda p, img: on_set_icon(p, "large", img),
                    inputs=[project_state, large_icon],
                    outputs=[project_state],
                )
                
                export_btn.click(
                    on_export_sprite,
                    inputs=[project_state],
                    outputs=[export_status],
                )
                
                download_btn.click(
                    on_export_zip,
                    inputs=[project_state],
                    outputs=[download_file, export_status],
                )

    return demo


def main() -> None:
    demo = build_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        footer_links=[],
    )


if __name__ == "__main__":
    main()
