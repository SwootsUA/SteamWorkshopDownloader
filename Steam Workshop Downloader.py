import requests
from bs4 import BeautifulSoup
import re
import subprocess
import tkinter as tk
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import json

prev_mod_link = None
user_home = os.path.expanduser("~")
config_file_path = os.path.join(user_home, "mod_downloader_config.json")
download_path = ''

def load_config():
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
            return {
                'steamcmd_directory': config.get('steamcmd_directory', ''),
                'is_download_folder': config.get('is_download_folder', False),
                'download_folder_entry': config.get('download_folder_entry', '')
            }
    except FileNotFoundError:
        return {
            'steamcmd_directory': '',
            'is_download_folder': False,
            'download_folder_entry': ''
        }

def save_config(steamcmd_directory = None, is_download_folder = None, download_folder_entry = None):
    try:
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        config = {}

    # Update the specific values if provided
    if steamcmd_directory is not None:
        config['steamcmd_directory'] = steamcmd_directory

    if is_download_folder is not None:
        config['is_download_folder'] = is_download_folder

    if download_folder_entry is not None:
        config['download_folder_entry'] = download_folder_entry

    # Save the updated configuration
    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file)

def clear_image():
    image_label.config(image=None)
    image_label.image = None

def set_image_status(text):
    image_status_label.config(text=text)

def get_game_and_workshop_ids(workshop_url):
    try:
        # Send a GET request to the provided URL
        response = requests.get(workshop_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the HTML content of the page
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the link with the text "Store Page"
            store_link = soup.find('a', {'class': 'btnv6_blue_hoverfade btn_medium', 'data-appid': True})

            if store_link:
                # Extract the game ID from the data-appid attribute
                game_id = store_link['data-appid']

                # Extract the Workshop item ID from the URL
                match = re.search(r'/filedetails/\?id=(\d+)', workshop_url)

                if match:
                    workshop_id = match.group(1)
                    return game_id, workshop_id
        else:
            print(f"Failed to retrieve content. Status code: {response.status_code}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return None, None

def download_workshop_item(steamcmdpath, game_id, item_id, install_dir = None):
    if install_dir is None:
        steamcmd_args = [
            "+login anonymous",
            f"+workshop_download_item {game_id} {item_id}",
            "+quit",
        ]
    else:
        steamcmd_args = [
            "+login anonymous",
            f"+force_install_dir {install_dir}",
            f"+workshop_download_item {game_id} {item_id}",
            "+quit",
        ]

    try:
        result = subprocess.run([steamcmdpath + "/steamcmd.exe"] + steamcmd_args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        
        # Extract and display success message and path
        success_match = re.search(r'Success\. Downloaded item \d+ to "(.+?)"', result.stdout)
        if success_match:
            global download_path
            print(f"Success. Downloaded item {item_id} to {success_match.group(1)}")

            download_path = success_match.group(1)
            print(download_path)
            set_download_status(f"Success. Downloaded item {item_id} to {download_path}")
        else:
            print("SteamCMD completed successfully, but success message not found.")
            set_download_status("SteamCMD completed successfully, but success message not found.")
        
        # Display error message, if any
        if result.stderr:
            print(f"SteamCMD encountered an error: {result.stderr}")
            set_download_status(f"SteamCMD encountered an error: {result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"SteamCMD encountered an error: {e.returncode}")
        set_download_status(f"SteamCMD encountered an error: {e.returncode}")

def choose_download_dir():
    download_dir = filedialog.askdirectory()
    if download_dir:
        dowload_folder_entry.configure(state=tk.NORMAL)
        dowload_folder_entry.delete(0, tk.END)
        dowload_folder_entry.insert(0, download_dir)
        dowload_folder_entry.configure(state=tk.DISABLED)
        save_config(download_folder_entry=download_dir)

def choose_steamcmd_dir():
    steamcmd_dir = filedialog.askdirectory()
    if steamcmd_dir:
        steamcmd_dir_entry.configure(state=tk.NORMAL)
        steamcmd_dir_entry.delete(0, tk.END)
        steamcmd_dir_entry.insert(0, steamcmd_dir)
        steamcmd_dir_entry.configure(state=tk.DISABLED)
        save_config(steamcmd_directory=steamcmd_dir)

def download_image(mod_link):
    global prev_mod_link
    try:
        # Set status to "Searching Image"
        set_image_status("Searching Image")

        # Set up Chrome in headless mode
        options = Options()
        options.headless = True

        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(mod_link)

        # Wait for the image to load (adjust the timeout as needed)
        wait = WebDriverWait(driver, 10)
        image = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "workshopItemPreviewImageEnlargeable")))

        # Get the image source
        img_src = image.get_attribute("src")
        print(f"Preview Image URL: {img_src}")

        # Download and save the image
        save_path = os.path.join(tempfile.gettempdir(), "steamcmd_mod_image_preview.jpg")
        with open(save_path, 'wb') as image_file:
            image_content = requests.get(img_src).content
            image_file.write(image_content)
        print(f"Image saved to: {save_path}")

        # Display the image in the Tkinter window
        image = Image.open(save_path)
        image.thumbnail((300, 300))  # Scale the image to fit within a 300x300 pixel area
        imgtk = ImageTk.PhotoImage(image)

        image_label.config(image=imgtk)
        image_label.image = imgtk

        # Set status to empty
        set_image_status("")

        # Close the Selenium driver
        driver.quit()

        prev_mod_link = mod_link  # Update the previous link

    except Exception as e:
        print(f"Error while fetching or parsing the page: {e}")
        set_image_status("Image not found" + e)

def on_mod_link_entry_change(event):
    mod_link = mod_link_entry.get()
    
    # Define a regex pattern to match URLs with "steamcommunity.com" and "?id=" followed by a number
    url_pattern = r'(https?://)?(.*steamcommunity\.com.*)\?id=\d+'

    if re.match(url_pattern, mod_link):
        print(f"Valid URL entered: {mod_link}")

        # Check if the new link is the same as the previous one
        if mod_link == prev_mod_link:
            print("Link has not changed; skipping image download.")
            return

        # Create a new thread to download the image
        download_image_thread = threading.Thread(target=download_image, args=(mod_link,))
        download_image_thread.start()
        
        # Set status to "Searching Image"
        clear_image()
        set_image_status("Searching Image")
    else:
        print(f"Not a valid URL: {mod_link}")
        set_image_status("Incorrect link")

def toggle_select_folder_button():
    save_config(is_download_folder=is_download_folder.get())
    if is_download_folder.get() == 1:
        dowload_folder_frame.pack(padx=10, fill=tk.X)
    else:
        dowload_folder_frame.forget()

def set_download_status(text):
    download_status.delete(0, tk.END)
    download_status.insert(0, text)

def download_mod(mod_link, steamcmdpath, directory):
    game_id, item_id = get_game_and_workshop_ids(mod_link)

    if game_id and item_id:
        if directory == '' or is_download_folder.get() == 0:
            download_workshop_item(steamcmdpath, game_id, item_id)
        else:
            download_workshop_item(steamcmdpath, game_id, item_id, directory)
    else:
        set_download_status('game id not found')

def download_mod_button():
    mod_link = mod_link_entry.get()
    steamcmdpath = steamcmd_dir_entry.get()
    directory = dowload_folder_entry.get()

    if steamcmdpath == '' or None:
        set_download_status('SteamCMD path is Empty')
        return

    download_mod_thread = threading.Thread(target=download_mod, args=(mod_link, steamcmdpath, directory,))
    download_mod_thread.start()

    set_download_status('Downloading mod...')

def open_mod_dir():
    if download_path != '' and download_path != None:
        os.system(f"explorer.exe \"{download_path}\"")

if __name__ == "__main__":
    window = tk.Tk()
    window.title("Mod Downloader")
    window.geometry("700x400")

    mod_link_frame = tk.Frame(window)
    mod_link_frame.pack(padx=10, fill=tk.X)

    mod_link_label = tk.Label(mod_link_frame, text="Mod Link:")
    mod_link_label.pack(side=tk.LEFT)

    mod_link_entry = tk.Entry(mod_link_frame)
    mod_link_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

    # Bind the KeyRelease event to the Mod Link Entry
    mod_link_entry.bind("<KeyRelease>", on_mod_link_entry_change)

    steamcmd_frame = tk.Frame(window)
    steamcmd_frame.pack(padx=10, fill=tk.X)

    steamcmd_dir_label = tk.Label(steamcmd_frame, text="SteamCMD Directory:")
    steamcmd_dir_label.pack(side=tk.LEFT)

    initial_steamcmd_dir = load_config()['steamcmd_directory']
    steamcmd_dir_entry = tk.Entry(steamcmd_frame, disabledbackground="light gray")
    steamcmd_dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
    steamcmd_dir_entry.delete(0, tk.END)
    steamcmd_dir_entry.insert(0, initial_steamcmd_dir)
    steamcmd_dir_entry.configure(state=tk.DISABLED)

    choose_steamcmd_button = tk.Button(steamcmd_frame, text="...", command=choose_steamcmd_dir)
    choose_steamcmd_button.pack(side=tk.LEFT)

    download_folder_container = tk.Frame(window)
    download_folder_container.pack(fill=tk.X)
    
    dowload_folder_frame = tk.Frame(download_folder_container)

    dowload_folder_label = tk.Label(dowload_folder_frame, text="Custom download folder:")
    dowload_folder_label.pack(side=tk.LEFT)

    initial_download_dir = load_config()['download_folder_entry']
    dowload_folder_entry = tk.Entry(dowload_folder_frame, disabledbackground="light gray")
    dowload_folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
    dowload_folder_entry.delete(0, tk.END)
    dowload_folder_entry.insert(0, initial_download_dir)
    dowload_folder_entry.configure(state=tk.DISABLED)

    choose_dowload_folder_button = tk.Button(dowload_folder_frame, text="...", command=choose_download_dir)
    choose_dowload_folder_button.pack(side=tk.LEFT)

    is_download_folder = tk.IntVar()
    is_download_folder.set(load_config()['is_download_folder'])
    check_box = tk.Checkbutton(window, text='Custom download folder', variable=is_download_folder, onvalue=1, offvalue=0, command=toggle_select_folder_button)
    check_box.pack()

    toggle_select_folder_button()   

    buttons_frame = tk.Frame(window)
    buttons_frame.pack(fill=tk.X)

    download_button = tk.Button(buttons_frame, text="Download Mod", command=download_mod_button)
    download_button.pack()

    open_mod_folder = tk.Button(buttons_frame, text="Open Mod Folder", command=open_mod_dir)
    open_mod_folder.pack()

    download_status = tk.Entry(window)
    download_status.pack(pady=10, fill=tk.X)

    image_label = tk.Label(window)
    image_label.pack()

    image_status_label = tk.Label(window, text="", fg="blue")
    image_status_label.pack()

    window.mainloop()