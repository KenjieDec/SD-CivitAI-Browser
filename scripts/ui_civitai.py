import gradio as gr
from modules import script_callbacks
import itertools
from modules.shared import opts
import re
import time
from scripts.civitai_api import *

def on_ui_tabs():
    with gr.Blocks() as civitai_interface:
        with gr.Row():
            with gr.Column(scale=2):
                content_type = gr.Dropdown(label='Content type:', choices=["Checkpoint", "TextualInversion", "LORA", "LoCon", "Poses", "Controlnet", "Hypernetwork", "AestheticGradient", "VAE"], value="Checkpoint", type="value")
            with gr.Column(scale=1,min_width=100):
                sort_type = gr.Dropdown(label='Sort List by:', choices=["Newest", "Most Downloaded", "Highest Rated", "Most Liked"], value="Highest Rated", type="value")
                show_nsfw = gr.Checkbox(label="NSFW content", value=True, default=True)
            with gr.Column(scale=1):
                period = gr.Dropdown(label='Period:', choices=["AllTime", "Year", "Month", "Week", "Day"], value="Month", type="value")
        with gr.Row():
            search_by = gr.Radio(label="Search by", choices=["None", "Model name", "User name", "Tag", "Url"], value="Model name")
            search_term = gr.Textbox(label="Search Term", visible=True, interactive=True, lines=1)
        with gr.Row():
            with gr.Column(scale=4):
                search = gr.Button(label="Search", value="Search")
            with gr.Column(scale=2,min_width=80):
                prev_button = gr.Button(value="Prev. Page", interactive=False)
            with gr.Column(scale=2,min_width=80):
                next_button = gr.Button(value="Next Page", interactive=False)
            with gr.Column(scale=1,min_width=80):
                limit = gr.Number(label='Limit', minimum=1, maximum=100, value=20, interactive=True, show_label=True)
            with gr.Column(scale=1,min_width=80):
                pages = gr.Textbox(label='Page', interactive=False, show_label=True)
        with gr.Row():
            list_html = gr.HTML()
        with gr.Row():
            current_model = gr.Textbox(label="Model", interactive=False, elem_id="quicksettings1", value=None)
            selected_model = gr.Textbox(label="Event text", elem_id="selected_model", visible=False, value="", interactive=True, lines=1)
            list_versions = gr.Dropdown(label="Versions", choices=[], interactive=False, elem_id="quicksettings", value=None)
        with gr.Row():
            trigger = gr.Textbox(label='Trigger Words', visible=False, value="None", interactive=False, lines=1)
            model_filename = gr.Textbox(label="Model Filename", choices=[], interactive=False, value=None)
            download_url = gr.Textbox(label="Download Url", interactive=False, value=None)
        with gr.Row():
            download_model = gr.Button(value="Download Model", interactive=False)
            save_model_in_new = gr.Checkbox(label="Save a model to a Folder with model name", value=False)
        with gr.Row():
            preview_image_html = gr.HTML()

        search_by.change(
            fn=showhide,
            inputs=search_by,
            outputs=search_term,
            show_progress=False
        )
        download_model.click(
            fn=download_file_thread,
            inputs=[
                download_url,
                model_filename,
                content_type,
                save_model_in_new,
                current_model,
            ],
            outputs=download_model
        )
        search.click(
            fn=update_model_list,
            inputs=[
                content_type,
                sort_type,
                period,
                search_by,
                search_term,
                show_nsfw, 
                limit
            ],
            outputs=[
                list_html,            
                prev_button,
                next_button,
                pages,
                limit
            ]
        )
        show_nsfw.change(
            fn=update_everything,
            #fn=update_model_info,
            inputs=[
                content_type,
                sort_type,
                period,
                search_by,
                search_term,
                show_nsfw,

                selected_model, 

                list_html,

                limit
            ],
            outputs=[
                list_html,            
                prev_button,
                next_button,
                pages,

                selected_model,

                trigger,

                limit
            ]
        )
        #current_model.change(
        #    fn = update_model_versions,
        #    inputs=[
        #        current_model,
        #    ],
        #    outputs=[
        #        list_versions,
        #    ]
        #)
        def update_models_dropdown2(model_name, show_nsfw, model_types, ret_versions, type):
            
            if ret_versions == "" or ret_versions is None or not ret_versions:
                return (
                            gr.Textbox.update(value=""), # Download URL
                            gr.Textbox.update(value=""), # trigger 

                            gr.Textbox.update(value=""), # Model FileName 
                            gr.Button.update(interactive=False), # Download Button

                            gr.HTML.update(visible=False), # Preview 
                            gr.HTML.update(), # Model List 

                            gr.Dropdown.update(interactive=False) # Versions List
                        )   
            start_time = time.time()
            (html, dum, filename) = update_model_info(model_name, ret_versions, show_nsfw, type)
            time_elapsed = time.time() - start_time
            print("Extracted models in", time_elapsed, "seconds")

            start_time = time.time()
            down_url = update_download_url(model_name, ret_versions, filename)
            time_elapsed = time.time() - start_time
            print("Extracted download url in", time_elapsed, "seconds")

            download = "Download Model"
            download_state = True

            return (
                        down_url, # Download URL
                        dum, # trigger 

                        filename, # Model FileName 
                        gr.Button.update(interactive=download_state, value=download), # Download Button

                        html, # Preview 
                        gr.HTML.update(visible=True), # Model List 

                        gr.Dropdown.update(interactive=True) # Versions List
                    )  
        list_versions.change(
            fn = update_models_dropdown2,
            inputs=[
                current_model,
                show_nsfw,
                content_type,
                list_versions,
                content_type
            ],
            outputs=[
                download_url,
                trigger,

                model_filename, 
                download_model,

                preview_image_html,
                list_html,
                list_versions,
            ]
        )
        next_button.click(
            fn=updatePage,
            inputs=[
                show_nsfw,
                next_button
            ],
            outputs=[
                # current_model,
                # list_versions,
                list_html,
                prev_button,
                next_button,
                pages
            ]
        )
        prev_button.click(
            fn=updatePage,
            inputs=[
                show_nsfw,
                prev_button
            ],
            outputs=[
                # current_model,
                # list_versions,
                list_html,
                prev_button,
                next_button,
                pages
            ]
        )

        def update_models_dropdown(model_name):
            if model_name == "":
                return (
                            gr.Textbox.update(value=""), # Model name
                            gr.Dropdown.update(value="", choices=[], interactive=False), # Versions
                            # gr.Textbox.update(value=""), # Download URL
                            gr.Textbox.update(value="", visible=False), # Trigger

                            # gr.Textbox.update(value="", interactive=False), # Model FileName
                            # gr.Button.update(interactive=False), # Download Button

                            # gr.HTML.update(value=None), # Preview
                            gr.HTML.update() # Model List 
                        )   
            start_time = time.time()
            ret_versions = update_model_versions(model_name, False)
            time_elapsed = time.time() - start_time
            print("Extracted model versions in", time_elapsed, "seconds")

            return (
                        gr.Textbox.update(value=model_name), # Model name 
                        ret_versions, # Versions
                        # down_url, # Download URL
                        gr.Textbox.update(value="", visible=False), # Trigger

                        # filename, # Model FileName 
                        # gr.Button.update(interactive=download_state, value=download), # Download Button

                        # html, # Preview 
                        gr.HTML.update(visible=False) # Model List 
                    )   
        
        selected_model.change(
            fn=update_models_dropdown,
            inputs=[
                selected_model,
            ],
            outputs=[
                current_model,
                list_versions,
                # download_url,
                trigger,

                # model_filename, 
                # download_model,

                # preview_image_html,
                list_html,
            ],
        )    
        return (civitai_interface, "CivBrowser", "civitai_interface"),

script_callbacks.on_ui_tabs(on_ui_tabs)
