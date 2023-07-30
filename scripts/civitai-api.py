import requests
import json
import modules.scripts as scripts
import gradio as gr
from modules import script_callbacks
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
import os
from tqdm import tqdm
import time
import re
import io
from requests.exceptions import ConnectionError
from modules.shared import opts, cmd_opts
from modules.paths import models_path
import shutil
from html import escape
import hashlib
import subprocess
import multiprocessing
from multiprocessing import Process
import concurrent.futures
import blake3
import random

folders = {
    "Checkpoint": cmd_opts.ckpt_dir if cmd_opts.ckpt_dir else os.path.join(models_path, "Stable-diffusion"),
    "Hypernetwork": cmd_opts.hypernetwork_dir,
    "TextualInversion": cmd_opts.embeddings_dir,
    "AestheticGradient": "extensions/stable-diffusion-webui-aesthetic-gradients/aesthetic_embeddings",
    "LORA": cmd_opts.lora_dir,
    "LoCon": cmd_opts.lyco_dir 
        if "lyco_dir" in cmd_opts else cmd_opts.lyco_dir_backcompat if "lyco_dir_backcompat" in cmd_opts else os.path.join(models_path, "LyCORIS"),
    "VAE": cmd_opts.vae_dir 
        if cmd_opts.vae_dir else os.path.join(models_path, "VAE"),
    "Controlnet": os.path.join(os.path.join(cmd_opts.ckpt_dir, os.pardir), "ControlNet")
        if cmd_opts.ckpt_dir else os.path.join(models_path, "ControlNet"),
    "Poses": os.path.join(os.path.join(cmd_opts.ckpt_dir, os.pardir), "Poses")
        if cmd_opts.ckpt_dir else os.path.join(models_path, "Poses")
}


def random_user_agent():
    chrome = [
        "Chrome/113.0.0.0",
        "Chrome/114.0.0.0",
        "Chrome/115.0.0.0",
    ]

    browsers = [    
        "Edg/114.0.1823.82",
        "Edg/114.0.1823.41",
        "Edg/114.0.1823.8",
        "Edg/114.0.1823.79",
        "OPR/69.0",
        "OPR/99.0.0",
        "OPR/100.0.0.0",
        "OPRGX/104.0.4480.100"
    ]
    operating_systems = [
        "Windows NT 10.0; Win64; x64",
        "Windows NT 6.1; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_5",
        "Macintosh; Intel Mac OS X 10_14_6",
        "Macintosh; Intel Mac OS X 10_14_7",
        "X11; Ubuntu; Linux x86_64",
        "X11; Linux x86_64",
        "Windows NT 6.3; Win64; x64",
    ]

    random_chrome = random.choice(chrome)
    random_browser = random.choice(browsers)
    random_os = random.choice(operating_systems)

    user_agent = f'Mozilla/5.0 ({random_os}) AppleWebKit/537.36 (KHTML, like Gecko) {random_chrome} Safari/537.36 {random_browser}'

    return user_agent


# def_headers = {'User-Agent': 'Mozilla/5.0 (Windows 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 OPRGX/104.0.4480.100'}
def def_headers():
    return {'User-Agent': random_user_agent()}


api_url = "https://civitai.com/api/v1/models" 

models_data = None
json_info = None


def get_model_info_by_id(id, type:str, retry=False) -> dict:
    if not id:
        print("No id?") 
        return None

    civitai_endpoints = {
        "modelId": "https://civitai.com/api/v1/models/",
        "versionId": "https://civitai.com/api/v1/model-versions/",
    }

    api_url = civitai_endpoints[type]
    if not api_url:
        print("Invalid type specified")
        return None

    try:
        response = requests.get(api_url + str(id), headers=def_headers(), proxies=None)
        response.raise_for_status()

        content = response.json()
        if not content:
            print("Error: No content found")
            return None

        return content

    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 503:
            print("Error: 503 Service Unavailable")
            if retry == True:
                return None
            print("Retrying...")
            print("503 Service Unavailable error, retrying...")
            time.sleep(1)
            get_model_info_by_id(id, type, True)
    except requests.exceptions.RequestException as e:
        print("Request error:", e)
        return None

    except ValueError as ve:
        print("Parse response JSON failed")
        print(str(ve))
        print("Response:")
        print(response.text)
        return None

    except Exception as ex:
        print("Error:", ex)
        return None
    
def calculate_sha256(filename):
    sha256 = blake3.blake3()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

            
def scan_model(model_types, model_name, file_name):
    print("Scanning Files")
    def get_folder_size(folder_path):
        total_size = 0
        byte_to_gb = 1/(1024**3)  # Conversion factor from bytes to GB

        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                total_size += os.path.getsize(file_path)

        folder_size_in_gb = total_size * byte_to_gb
        return folder_size_in_gb
    for model_type, model_folder in folders.items():
        if model_type not in model_types:
            continue
        for root, dirs, files in os.walk(model_folder, followlinks=True):
            for filename in files:
                if(len(files) > 5 or get_folder_size(root) > 10): return False # Just skip, it's quite useless
                if(file_name == filename): return True
                # check ext
                item = os.path.join(root, filename)
                base, ext = os.path.splitext(item)
                if ext in (".bin", ".pt", ".safetensors", ".ckpt"):
                    # ignore vae file
                    if len(base) > 4:
                        if base[-4:] == ".vae":
                            # find .vae
                            print("This is a vae file: " + filename)
                            continue
                    print(f"Checking {filename}")
                
                    start_time = time.time()

                    num_threads = os.cpu_count() or 1
                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as pool:
                        future = pool.submit(calculate_sha256, item)
                        hash = future.result()
                    time_elapsed = time.time() - start_time
                    print("Extracted model hash in", time_elapsed, "seconds")

                    # use this sha256 to get model info from civitai
                    model_info = requests.get(f"https://civitai.com/api/v1/model-versions/by-hash/{hash}", headers=def_headers(), proxies=None)
                    if not model_info.ok:
                        model_info = None

                    try:
                        model_info = model_info.json()
                    except Exception:
                        model_info = None

                    if not model_info or model_info is None:
                        return False
                    # delay 1 second for ti
                    if model_type == "TextualInversion":
                        time.sleep(1)
                    
                    if model_info:
                        if "modelId" in model_info.keys():
                            time.sleep(1)
                            modelId = model_info["modelId"]
                            model = get_model_info_by_id(modelId, "modelId")
                            if model or model is not None:
                                if model_name in model["name"]:
                                    print(f"Skipping download, This model was found in {root} as {filename}")
                                    return True
                            else:
                                return False
                            
def download_file(url, file_name, path, model_types, model_name):

    command = f"aria2c --log-level=error -q -c -x 16 -s 16 -k 1M {url} -d {path} -o {file_name}"
    
    try:
        # Check if aria2c is installed and available
        subprocess.run(["aria2c", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        max_retry_attempts = 3
        retry_count = 0
        while retry_count < max_retry_attempts:
        
            start_time = time.time()

            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate()
            
            time_elapsed = time.time() - start_time


            if process.returncode == 0:
                print(f"{file_name} downloaded successfully.")
                print("Time elapsed:", time_elapsed, "seconds")
                retry_count = 3 
                return True
            else:
                print(f"Error downloading {file_name}. Try again...")
                retry_count += 1
        return False


    except (subprocess.CalledProcessError, FileNotFoundError):
        print("aria2c is not installed or not available on the system.")
        print("Falling back to using requests for downloading...")

        # Fallback method using requests
        try:
            response = requests.get(url, stream=True, headers=def_headers(), proxies=None)
            response.raise_for_status()

            req = urllib.request.Request(url, headers=def_headers())
            with urllib.request.urlopen(req) as response:
                response = requests.get(url, stream=True, headers=def_headers(), proxies=None)
                file_size = int(response.headers.get('Content-Length', 0))
                with open(f"{path}", "wb") as f:
                    with tqdm(response, 'content', total=file_size, unit='B', unit_scale=True) as pbar:
                        for data in response.iter_content(chunk_size=16384):
                            f.write(data)
                            pbar.update(len(data))

            print(f"{file_name} downloaded successfully.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {file_name}: \n{e}")
            return False

def chkfldr(content_type, use_new_folder, model_name = ""):
    folder = folders[content_type]   
    if not os.path.exists(folder): os.makedirs(folder)
        
    escapechars = { " ": r"_",
                    "(": r"",
                    ")": r"",
                    "|": r"",
                    ":": r"",
                    ",": r"_",
                    "<": r"",
                    ">": r"",
                    "!": r"",
                    "?": r"",
                    ".": r"_",
                    "&": r"_and_",
                    "*": r"_",
                    "\"": r"",
                    "\\": r""}
    if use_new_folder:
        model_folder = os.path.join(folder, model_name.maketrans(escapechars))
        if not os.path.exists(model_folder):
            os.makedirs(model_folder)
    else:
        model_folder = os.path.join(folder)
        if not os.path.exists(model_folder):
            os.makedirs(model_folder)
    print(f"Model Path:{model_folder}")
    return model_folder

def download_file_thread(url, file_name, content_type, use_new_folder, model_name):
    model_folder = chkfldr(content_type, use_new_folder, model_name)
    path = os.path.join(model_folder)
    
    print(f"Downloading {model_name}")
    download = download_file(url, file_name, path, content_type, model_name)

    return gr.Button.update(interactive = not download)

def api_search(content_type, sort_type, period, search_by, search_term=None, limit=20):
    query = {'limit': limit, 'types': content_type, 'sort': sort_type, 'period': period}
    if (search_by not in ["Url", "None"]) and search_term:
        #search_term = search_term.replace(" ","%20")
        match search_by:
            case "User name":
                query.update({'username': search_term })
            case "Tag":
                query.update({'tag': search_term })
            case _:
                query.update({'query': search_term })
        return request_civit_api(f"{api_url}", query )
    else:
        match search_by:
            case "None":
                query.update({'query': "" })
            case "Url":
                pattern = r'(?:https?://)?(?:www\.)?civitai\.com/(?:models|api/download/models)/(\d+)'
                url = search_term
                try:
                    response = requests.head(url)
                    if not response.ok:
                        if response.status_code == 404:
                            # this is not a civitai model
                            query.update({'query': "Website doesn't exist" })
                        else:
                            print("Get error code: " + str(response.status_code))
                            print(response.text)
                            query.update({'query': "Website doesn't exist" })
                except requests.exceptions.RequestException:
                    query.update({'query': "Website doesn't exist" })
                # Search for the pattern in the URL
                match = re.search(pattern, url)
                if match:
                    match = match.group(1)
                else:
                    query.update({'query': "Website doesn't exist" })
                
                isit_versionId = get_model_info_by_id(match, "versionId")
                if not isit_versionId or isit_versionId == None:
                    isit_modelId = get_model_info_by_id(match, "modelId")
                if not isit_modelId or isit_modelId == None:
                    query.update({'query': "Website doesn't exist" })
                if(isit_versionId):
                    getModelInfo = get_model_info_by_id(isit_versionId["modelId"])
                    query.update({'query': getModelInfo["name"] })
                if(isit_modelId):
                    query.update({'query': isit_modelId["name"] })
        return request_civit_api(f"{api_url}", query )

def model_list_html(models_data, model_dict, allow_nsfw):
    HTML = '''<div class="column civlistParent">
    <div class="column civmodellist" data-mouse-down-at="0" data-prev-percentage="0">'''
    imgtag = ""
    for item in models_data['items']:
        if item['name'] in model_dict:
            model_name = escape(item["name"].replace("'", "\\'"), quote=True)
            nsfw = None
            modelVersions = item['modelVersions']
            images = item["modelVersions"][0]["images"]
            isNSFW = (images[0]['nsfw'] not in ["None", "Soft"]) or item['nsfw'] is True
            if modelVersions and len(images) > 0:
                if (isNSFW not in ["None", "Soft"]) and not allow_nsfw:
                    nsfw = 'civcardnsfw'
                imgtag = f'<img src="{images[0]["url"]}"></img>'
            else:
                imgtag = '<img src="./file=html/card-no-preview.png"></img>'

            HTML += f'<figure class="civmodelcard {nsfw}" onclick="select_model(\'{model_name}\')">' \
                    + imgtag \
                    + (f'<figcaption class="nsfwFig">NSFW</figcaption>' if isNSFW else '') \
                    + f'<figcaption class="nameFig">{item["name"]}</figcaption></figure>'

    HTML += '''</div>
    </div>'''
    return HTML

def updatePage(show_nsfw, button):
    global models_data

    isNext = True if button == "Next Page" else False
    if isNext:
        next_page = models_data['metadata']['nextPage']
        models_data = request_civit_api(next_page)
    else:
        prev_page = models_data['metadata']['prevPage']
        models_data = request_civit_api(prev_page) if prev_page is not None else None

    if models_data is None:
        return

    hasPrev, hasNext, pages = pagecontrol(models_data)
    model_dict = {item['name']: item['name'] for item in models_data['items']}

    HTML = model_list_html(models_data, model_dict, show_nsfw)

    return (
        # gr.Textbox.update(value=None), # Model Name
        # gr.Dropdown.update(choices=[], value=None), # Versions
        gr.HTML.update(value=HTML), # List HTML
        gr.Button.update(interactive=hasPrev), # Prev Button
        gr.Button.update(interactive=hasNext), # Next Button
        gr.Textbox.update(value=pages) # Pages count
    )

def pagecontrol(models_data):
    pages = f"{models_data['metadata']['currentPage']}/{models_data['metadata']['totalPages']}"
    hasNext = 'nextPage' in models_data['metadata']
    hasPrev = 'prevPage' in models_data['metadata']
    return hasPrev, hasNext, pages

def update_model_list(content_type, sort_type, period, search_by, search_term, show_nsfw, limit = 20):
    global models_data

    if limit < 0:
        limit = 20
    elif limit > 100:
        limit = 100
    
    models_data = api_search(content_type, sort_type, period, search_by, search_term, limit)
    if models_data is None:
        return None

    hasPrev, hasNext, pages = pagecontrol(models_data)

    model_dict = {item['name']: item['name'] for item in models_data['items']}

    HTML = model_list_html(models_data, model_dict, show_nsfw)

    return (
        gr.HTML.update(value=HTML, visible=True), # Model List
        gr.Button.update(interactive=hasPrev), # Previous Button
        gr.Button.update(interactive=hasNext), # Next Button
        gr.Textbox.update(value=pages), # Page list
        gr.Number.update(value=limit)
    )

# My head hurts thinking about how to implement this code:
def get_model_gallery(versionId):
    try:
        parameters = urllib.parse.urlencode({ 'modelVersionId': versionId, 'sort':"Newest" }, quote_via=urllib.parse.quote)
        
        # Make a GET request to the API
        response = requests.get("https://civitai.com/api/v1/images", params=parameters, timeout=30, headers=def_headers(), proxies=None)
        response.raise_for_status()

        response.encoding = "utf-8"  # response.apparent_encoding
        data = json.loads(response.text)
        return data

    except requests.exceptions.RequestException as e:
        print("Request error: ", e)
        return None

def update_model_versions(model_name=None, inter=True):
    if model_name is not None:
        global models_data
        versions_dict = {}
        for item in models_data['items']:
            if item['name'] == model_name:
                for model in item['modelVersions']:
                    versions_dict[model['name']] = item["name"]
        return gr.Dropdown.update(choices=[k for k, v in versions_dict.items()], value=f'{next(iter(versions_dict.keys()), None)}', interactive=inter)
    else:
        return gr.Dropdown.update(choices=[], value=None)

def update_download_url(model_name=None, model_version=None, model_filename=None):
    if model_filename:
        global models_data
        
        down_url = ""
        
        for item in models_data['items']:
            if item['name'] == model_name:
                for model in item['modelVersions']:
                    if model['name'] == model_version:
                        for file in model['files']:
                            down_url = file['downloadUrl']

        return gr.Textbox.update(value=down_url)
    else:
        return gr.Textbox.update(value=None)

def update_model_info(model_name=None, model_version=None, showNsfw=True, content_type="Checkpoint"):

    print(f"First: {content_type}")
    match content_type:
        case "TextualInversion":
            content_type = "Textual Inversion"
        case "AestheticGradient":
            content_type = "Aesthetic Gradient"
    
    print(f"Second: {content_type}")
    if model_name and model_version:
        global models_data
        trigger_words = "None"
        dl_dict = {}
        allownsfw = showNsfw
        data = { 
            "./file=html/card-no-preview.png": {
                "prompts": "None",
                "neg_prompts": "None",
                "steps": "None",
                "seed": "None",
                "sampler": "None",
                "cfg_scale": "None",
                "clip_skip": "None",
            }
        }
        triggerVisible = False
        for item in models_data['items']:
            if item['name'] == model_name:
                for model in item['modelVersions']:
                    
                    if model['name'] == model_version:
                        if model['trainedWords']:
                            trigger_words = ", ".join(model['trainedWords'])
                            triggerVisible = True
                            if trigger_words is None or trigger_words == "":
                                triggerVisible = False

                        for file in model['files']:
                            dl_dict[file['name']] = file['downloadUrl']

                        for img_dict in model["images"]:
                            if "url" in img_dict.keys():
                                img_url = img_dict["url"]
                                
                                if "meta" in img_dict.keys() and img_dict["meta"] is not None:
                                    # Get the 'meta' dictionary from img_dict
                                    meta_data = img_dict["meta"]
                                    
                                    # Create the desired structure with handling missing keys
                                    data[f"{img_url}"] = {
                                        "prompts": meta_data.get("prompt", "None"),
                                        "neg_prompts": meta_data.get("negativePrompt", "None"),
                                        "steps": meta_data.get("steps", "None"),
                                        "seed": meta_data.get("seed", "None"),
                                        "sampler": meta_data.get("sampler", "None"),
                                        "cfg_scale": meta_data.get("cfgScale", "None"),
                                        "clip_skip": meta_data.get("Clip skip", "None"),
                                    }
                                else:
                                    # If 'meta' doesn't exist or is None, set all values to None
                                    data[f"{img_url}"] = {
                                        "prompts": "None",
                                        "neg_prompts": "None",
                                        "steps": "None",
                                        "seed": "None",
                                        "sampler": "None",
                                        "cfg_scale": "None",
                                        "clip_skip": "None",
                                    }
                        
                        for pic in model['images']:
                            if "meta" in pic.keys() and pic["meta"] is not None:
                                # Get the 'meta' dictionary from img_dict
                                meta_data = pic["meta"]

                                # Create the desired structure with handling missing keys
                                data[f"{pic['url']}"] = {
                                    "prompts": meta_data.get("prompt", "None"),
                                    "neg_prompts": meta_data.get("negativePrompt", "None"),
                                    "steps": meta_data.get("steps", "None"),
                                    "seed": meta_data.get("seed", "None"),
                                    "sampler": meta_data.get("sampler", "None"),
                                    "cfg_scale": meta_data.get("cfgScale", "None"),
                                    "clip_skip": meta_data.get("Clip skip", "None"),
                                }
                            else:
                                # If 'meta' doesn't exist or is None, set all values to None
                                data[f"{pic['url']}"] = {
                                    "prompts": "None",
                                    "neg_prompts": "None",
                                    "steps": "None",
                                    "seed": "None",
                                    "sampler": "None",
                                    "cfg_scale": "None",
                                    "clip_skip": "None",
                                }
                        startHtml = """<html>
                        <head>
                        <title>Civitai Previews</title>
                        </head>
                        <body>"""

                        endHtml = """

                        <!-- Add more image-container divs as needed -->

                        </body>
                        </html>"""

                        currentHtml = startHtml
                        currentHtml = currentHtml + f'''  <div class="image-container">
                            <div class="image-container-in">
                            <div class="image-slider">
                                <div class="images">
                                    '''
                        currentImageNumber = 1
                        firstImage = "./file=html/card-no-preview.png"
                        for pic in model['images']:
                            nsfw = ""
                            if (pic['nsfw'] not in ["None", "Soft"]) and not allownsfw:
                                nsfw = 'civnsfw'
                            if currentImageNumber < 2:
                                currentHtml = currentHtml + f'<img src={pic["url"]} alt="Image {currentImageNumber}" class="active {nsfw}"  style="animation: 0.7s ease 0s 1 normal forwards running slideInRight;">' + """
                                """
                                firstImage = pic["url"]
                            else:
                                currentHtml = currentHtml + f'<img src={pic["url"]} alt="Image {currentImageNumber}" class="{nsfw}">' + """
                                """
                            currentImageNumber += 1
                        currentHtml = currentHtml + f'''</div>
                                
                                <div class="prev-btn" onclick="prevSlide(this, {data})" style="opacity: 0;">
                                    <svg xmlns="http://www.w3.org/2000/svg">
                                        <path d="M15 6l-6 6l6 6" class="outside"></path>
                                        <path d="M15 6l-6 6l6 6" class="inside"></path>
                                    </svg>
                                </div>
                                <div class="next-btn" onclick="nextSlide(this, {data})" style="opacity: 0;">
                                    <svg xmlns="http://www.w3.org/2000/svg">
                                        <path d="M9 6l6 6l-6 6" class="outside"></path>
                                        <path d="M9 6l6 6l-6 6" class="inside"></path>
                                    </path></svg>
                                </div>
                            </div>
                            </div>

                            <div class="text">

                            <div class="startPoint">

                                <div class="divider-container">
                                <div class="divider-label">Resources Used</div>
                                </div>
                                <div class="base">
                                <div class="resource-container">
                                    <a class="resource-link" href="https://civitai.com/models/{item["id"]}" target="_blank">
                                    <div class="resource-details">
                                        <div class="resource-in-details">
                                        <div class="text-heading">{model_name}</div>
                                        <div class="badge-container">
                                            <div class="badge">{content_type}</div>
                                        </div>
                                        </div>
                                    </div>
                                    </a>
                                </div>
                                </div>
                                <div class="divider-container">
                                <div class="divider-label">Generation Data </div>
                                </div>

                                <div class="base">
                                <div class="prompt-container">
                                    <div class="inside-pc">

                                    <div class="stack-container">
                                        <div class="group-container">
                                        <div class="text-heading">Prompt</div>
                                        <div class="badge-container">
                                            <span class="badge-text">txt2img</span>
                                        </div>
                                        <button class="copy-button" type="button" onclick="handleCopyButtonClick(this)">
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="copy-svg">
                                                <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"></path>
                                                <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2"></path>
                                            </svg>
                                        </button>
                                        </div>

                                        <pre class="code-block">{data[firstImage]["prompts"]}</pre>
                                    </div>

                                    <div class="stack-container">
                                        <div class="group-container">
                                        <div class="text-heading">Negative prompt</div>
                                        <button class="copy-button" type="button" onclick="handleCopyButtonClick(this)">
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="copy-svg">
                                                <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"></path>
                                                <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2"></path>
                                            </svg>
                                        </button>
                                        </div>
                                        <pre class="code-block">{data[firstImage]["neg_prompts"]}</pre>
                                    </div>

                                    <div class="group-container">
                                        <div class="text-heading">Sampler</div>
                                        <code class="code-text">{data[firstImage]["sampler"]}</code>
                                    </div>

                                    <div class="group-container">
                                        <div class="text-heading">Model</div>
                                        <code class="code-text">{model_name}</code>
                                    </div>

                                    <div class="grid-container">
                                        <div class="group-container">
                                        <div class="text-heading">CFG scale</div>
                                        <code class="code-text">{data[firstImage]["cfg_scale"]}</code>
                                        </div>
                                        <div class="group-container">
                                        <div class="text-heading">Steps</div>
                                        <code class="code-text">{data[firstImage]["steps"]}</code>
                                        </div>
                                        <div class="group-container">
                                        <div class="text-heading">Seed</div>
                                        <code class="code-text">{data[firstImage]["seed"]}</code>
                                        </div>
                                        <div class="group-container">
                                        <div class="text-heading">Clip skip</div>
                                        <code class="code-text">{data[firstImage]["clip_skip"]}</code>
                                        </div>
                                    </div>

                                    <button class="copy-data-button" type="button" data-button="true" onclick="handleCopyDataButtonClick(this)">
                                        <div class="button-inner">
                                        <span class="button-inner-inner">
                                            <div class="button-label">
                                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="data-copy-svg">
                                                    <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"></path>
                                                    <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2"></path>
                                                </svg>
                                                Copy Generation Data
                                            </div>
                                        </span>
                                        </div>
                                    </button>

                                    </div>
                                </div>
                                </div>
                            </div>
                            </div>
                        </div>'''

                        currentHtml = currentHtml + endHtml
        return  (
                    gr.HTML.update(value=currentHtml),
                    gr.Textbox.update(value=trigger_words, visible=triggerVisible),
                    gr.Textbox.update(value=next(iter(dl_dict.keys()), None), interactive=True)
                )   
    else:       
        
        return  ( 
                    gr.HTML.update(value=None),
                    gr.Textbox.update(value=None),
                    gr.Dropdown.update(choices=[], value=None) 
                )


def request_civit_api(api_url=None, parameters=None):
    try:
        if parameters is not None:
            parameters = urllib.parse.urlencode(parameters, quote_via=urllib.parse.quote)
        
        # Make a GET request to the API
        response = requests.get(api_url, params=parameters, timeout=30, headers=def_headers(), proxies=None)
        response.raise_for_status()

        response.encoding = "utf-8"  # response.apparent_encoding
        data = json.loads(response.text)
        return data

    except requests.exceptions.RequestException as e:
        print("Request error: ", e)
        return None


def update_everything(content_type, sort_type, period, search_by, search_term, show_nsfw, selected_model, list, limit = 20):
    if not list:
        return (
            gr.HTML.update(), # Model List
            gr.Button.update(), # Previous Button
            gr.Button.update(), # Next Button
            gr.Textbox.update(), # Page list

            gr.Textbox.update(), # Model Name

            gr.Textbox.update(), # Trigger Words

            gr.Number.update() # Image Limit
        )
    
    (list, prev, next, pages, limitButton) = update_model_list(content_type, sort_type, period, search_by, search_term, show_nsfw, limit)
    return (
            list, 
            prev, 
            next, 
            pages, 

            gr.Textbox.update(value=""), 

            gr.Textbox.update(value="", visible=False), 

            limitButton
        )


def showhide(search_by):
    return gr.Textbox.update(visible=(search_by != "None"))

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
        return (civitai_interface, "CivitAI", "civitai_interface"),

script_callbacks.on_ui_tabs(on_ui_tabs)
