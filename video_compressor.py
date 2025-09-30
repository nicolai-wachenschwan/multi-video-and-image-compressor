import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import subprocess
import threading
import sys
import logging
from datetime import datetime, timezone
import json

# --- Optional Windows-specific imports for setting creation time ---
pywin32_available = False
if sys.platform == "win32":
    try:
        import win32file
        import pywintypes
        pywin32_available = True
    except ImportError:
        print("Note: 'pywin32' not found. File creation date (ctime) will not be set.")
        print("For this feature on Windows, run: pip install pywin32")

# --- Pillow import for image processing ---
try:
    from PIL import Image, ExifTags
except ImportError:
    messagebox.showerror(
        "Missing Library",
        "The 'Pillow' library is required for image processing.\n"
        "Please install it using: pip install Pillow"
    )
    sys.exit(1)


class FileProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Processor (Video & Image) V4.1")
        self.root.geometry("900x850")
        self.setup_file_logging()

        # --- GUI DEFINITION ---
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # -- Directories --
        dir_frame = ttk.LabelFrame(main_frame, text="Directories", padding=(10, 5))
        dir_frame.pack(fill=tk.X, pady=5)
        tk.Label(dir_frame, text="Source:", width=8).grid(row=0, column=0, sticky="w", pady=2)
        self.source_dir_entry = tk.Entry(dir_frame)
        self.source_dir_entry.grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(dir_frame, text="...", command=self.select_source_dir).grid(row=0, column=2)
        tk.Label(dir_frame, text="Target:", width=8).grid(row=1, column=0, sticky="w", pady=2)
        self.dest_dir_entry = tk.Entry(dir_frame)
        self.dest_dir_entry.grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(dir_frame, text="...", command=self.select_dest_dir).grid(row=1, column=2)
        dir_frame.columnconfigure(1, weight=1)

        # -- Video Settings --
        video_frame = ttk.LabelFrame(main_frame, text="Video Settings", padding=(10, 5))
        video_frame.pack(fill=tk.X, pady=5)
        tk.Label(video_frame, text="Compression (CRF):").grid(row=0, column=0, sticky="w", pady=2)
        self.crf_value = tk.IntVar(value=28)
        self.crf_scale = ttk.Scale(video_frame, from_=18, to=40, orient=tk.HORIZONTAL, variable=self.crf_value, command=self.update_crf_label)
        self.crf_scale.grid(row=0, column=1, sticky="ew", padx=5)
        self.crf_label = ttk.Label(video_frame, text="", width=40)
        self.crf_label.grid(row=0, column=2, sticky="w", padx=5)
        self.update_crf_label()
        tk.Label(video_frame, text="Resolution (Height):").grid(row=1, column=0, sticky="w", pady=2)
        self.resolution_var = tk.StringVar(value="Original")
        ttk.Combobox(video_frame, textvariable=self.resolution_var, values=["Original", "1080", "720", "480"], state="readonly").grid(row=1, column=1, sticky="ew", padx=5)
        video_frame.columnconfigure(1, weight=1)

        # -- Image Settings --
        image_frame = ttk.LabelFrame(main_frame, text="Image Settings", padding=(10, 5))
        image_frame.pack(fill=tk.X, pady=5)
        self.process_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(image_frame, text="Compress images", variable=self.process_images_var).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(image_frame, text="Compress if > (MB):").grid(row=1, column=0, sticky="w", pady=2)
        self.min_img_size_var = tk.DoubleVar(value=1.0)
        ttk.Entry(image_frame, textvariable=self.min_img_size_var, width=10).grid(row=1, column=1, sticky="w", padx=5)
        tk.Label(image_frame, text="Max Resolution (px):").grid(row=2, column=0, sticky="w", pady=2)
        self.img_resolution_var = tk.IntVar(value=1200)
        ttk.Entry(image_frame, textvariable=self.img_resolution_var, width=10).grid(row=2, column=1, sticky="w", padx=5)
        tk.Label(image_frame, text="JPG Quality (%):").grid(row=3, column=0, sticky="w", pady=2)
        self.img_quality_var = tk.IntVar(value=90)
        ttk.Entry(image_frame, textvariable=self.img_quality_var, width=10).grid(row=3, column=1, sticky="w", padx=5)

        # -- Timestamp Settings --
        timestamp_frame = ttk.LabelFrame(main_frame, text="Timestamp Settings", padding=(10, 5))
        timestamp_frame.pack(fill=tk.X, pady=5)
        self.use_earliest_date_var = tk.BooleanVar(value=False)
        # --- FIXED LINE --- Use anchor="w" for pack() instead of sticky="w"
        ttk.Checkbutton(timestamp_frame, text="Use earliest available date as creation date (from file metadata if possible)", variable=self.use_earliest_date_var).pack(anchor="w")

        # -- Actions & Progress --
        action_frame = ttk.Frame(main_frame, padding=(0, 10))
        action_frame.pack(fill=tk.X)
        self.start_button = tk.Button(action_frame, text="Start Processing", command=self.start_processing_thread, bg="#4CAF50", fg="white", font=('Helvetica', 10, 'bold'))
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        self.progress_bar = ttk.Progressbar(action_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # -- Log --
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=10)
        log_frame.pack(expand=True, fill=tk.BOTH, pady=5)
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10)
        self.log_text_widget.pack(expand=True, fill=tk.BOTH)

        self.video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v')
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')

    def setup_file_logging(self):
        log_dir = os.path.dirname(os.path.abspath(__file__))
        log_filename = f"processing_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        log_filepath = os.path.join(log_dir, log_filename)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(log_filepath, encoding='utf-8')])

    def log_to_gui(self, message):
        def append():
            self.log_text_widget.configure(state='normal')
            self.log_text_widget.insert(tk.END, message + '\n')
            self.log_text_widget.configure(state='disabled')
            self.log_text_widget.see(tk.END)
        self.root.after(0, append)

    def get_media_creation_date(self, filepath):
        """Tries to extract the internal 'creation date' from video or image metadata."""
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext in self.video_extensions:
                command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath]
                startupinfo = subprocess.STARTUPINFO() if sys.platform == "win32" else None
                if startupinfo: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(command, check=True, capture_output=True, text=True, startupinfo=startupinfo)
                metadata = json.loads(result.stdout)
                date_str = metadata.get('format', {}).get('tags', {}).get('creation_time')
                if date_str:
                    date_str = date_str.split('.')[0]
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            elif ext in self.image_extensions:
                with Image.open(filepath) as img:
                    exif_data = img.getexif()
                    if exif_data:
                        date_str = exif_data.get(36867) or exif_data.get(306)
                        if date_str:
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            logging.warning(f"Could not read metadata date from '{os.path.basename(filepath)}': {e}")
        return None

    def copy_file_timestamps(self, source, dest):
        """Copies timestamps (mtime, atime) and optionally ctime on Windows using the selected logic."""
        try:
            stat = os.stat(source)
            fs_creation_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
            fs_modification_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            fs_access_dt = datetime.fromtimestamp(stat.st_atime, tz=timezone.utc)

            final_creation_dt = fs_creation_dt
            final_modification_dt = fs_modification_dt
            final_access_dt = fs_access_dt

            if self.use_earliest_date_var.get():
                candidate_dates = [fs_creation_dt, fs_modification_dt, fs_access_dt]
                media_creation_dt = self.get_media_creation_date(source)
                if media_creation_dt:
                    candidate_dates.append(media_creation_dt.replace(tzinfo=timezone.utc))
                
                final_creation_dt = min(d for d in candidate_dates if d)
                self.log_to_gui(f"  -> Using earliest date found: {final_creation_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            os.utime(dest, (final_access_dt.timestamp(), final_modification_dt.timestamp()))
            
            if pywin32_available:
                try:
                    win_creation_time = pywintypes.Time(final_creation_dt)
                    win_access_time = pywintypes.Time(final_access_dt)
                    win_modification_time = pywintypes.Time(final_modification_dt)
                    
                    handle = win32file.CreateFile(dest, win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, 0, None)
                    win32file.SetFileTime(handle, win_creation_time, win_access_time, win_modification_time)
                    win32file.CloseHandle(handle)
                except Exception as e:
                    msg = f"  WARNING: Could not set creation date: {e}"
                    self.log_to_gui(msg); logging.warning(msg)
        except Exception as e:
            msg = f"  WARNING: Could not copy timestamps: {e}"
            self.log_to_gui(msg); logging.warning(msg)

    def update_crf_label(self, event=None):
        value = self.crf_value.get()
        desc = "(High Quality, large file)" if value <= 22 else "(Good Compromise)" if value <= 28 else "(High Compression, small file)"
        self.crf_label.config(text=f"Value: {value} {desc}")

    def select_source_dir(self):
        directory = filedialog.askdirectory(title="Source Directory")
        if directory: self.source_dir_entry.delete(0, tk.END); self.source_dir_entry.insert(0, directory)

    def select_dest_dir(self):
        directory = filedialog.askdirectory(title="Target Directory")
        if directory: self.dest_dir_entry.delete(0, tk.END); self.dest_dir_entry.insert(0, directory)

    def check_ffmpeg_tools(self):
        try:
            startupinfo = subprocess.STARTUPINFO() if sys.platform == "win32" else None
            if startupinfo: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, startupinfo=startupinfo)
            subprocess.run(["ffprobe", "-version"], check=True, capture_output=True, startupinfo=startupinfo)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError): return False

    def start_processing_thread(self):
        if not self.validate_inputs(): return
        self.start_button.config(state=tk.DISABLED, text="Analyzing...")
        threading.Thread(target=self.run_full_process, daemon=True).start()
        
    def validate_inputs(self):
        source_dir, dest_dir = self.source_dir_entry.get(), self.dest_dir_entry.get()
        if not all([source_dir, dest_dir]): messagebox.showerror("Error", "Source and Target must be selected."); return False
        if not os.path.isdir(source_dir): messagebox.showerror("Error", "Invalid source directory."); return False
        if source_dir == dest_dir: messagebox.showerror("Error", "Source and Target cannot be the same."); return False
        if not self.check_ffmpeg_tools():
            messagebox.showerror("Error", "FFmpeg/FFprobe not found.")
            self.log_to_gui("ERROR: FFmpeg/FFprobe could not be found."); logging.error("FFmpeg/FFprobe could not be found.")
            return False
        return True

    def run_full_process(self):
        self.log_to_gui("Starting scan...")
        logging.info("Starting scan...")
        files_to_process = self.scan_files(self.source_dir_entry.get())
        if not files_to_process:
            self.log_to_gui("No new files found to process.")
            logging.info("No new files found to process.")
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL, text="Start Processing"))
            return
        self.root.after(0, lambda: self.progress_bar.config(maximum=len(files_to_process)))
        self.root.after(0, lambda: self.start_button.config(text="Processing..."))
        self.process_files(files_to_process)
        self.log_to_gui("\nProcessing complete.")
        logging.info("Processing complete.")
        self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL, text="Start Processing"))
        self.root.after(0, lambda: self.progress_bar.config(value=0))

    def scan_files(self, source_dir):
        dest_dir, min_img_size_bytes, process_images = self.dest_dir_entry.get(), self.min_img_size_var.get() * 1024*1024, self.process_images_var.get()
        file_list = []
        for root, _, files in os.walk(source_dir):
            for filename in files:
                original_path, relative_path = os.path.join(root, filename), os.path.relpath(os.path.join(root, filename), source_dir)
                destination_path = os.path.join(dest_dir, relative_path)
                if os.path.exists(destination_path) or os.path.exists(f"{os.path.splitext(destination_path)[0]}.jpg"): continue
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.video_extensions: file_list.append(original_path)
                elif process_images and ext in self.image_extensions and os.path.getsize(original_path) > min_img_size_bytes: file_list.append(original_path)
        msg = f"{len(file_list)} new file(s) found to process."
        self.log_to_gui(msg); logging.info(msg)
        return file_list
        
    def process_files(self, file_list):
        for original_path in file_list:
            ext = os.path.splitext(original_path)[1].lower()
            if ext in self.video_extensions: self.process_single_video(original_path)
            elif ext in self.image_extensions: self.process_single_image(original_path)
            self.root.after(0, self.progress_bar.step)

    def get_video_height(self, video_path):
        try:
            command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=height', '-of', 'json', video_path]
            startupinfo = subprocess.STARTUPINFO() if sys.platform == "win32" else None
            if startupinfo: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(command, check=True, capture_output=True, text=True, startupinfo=startupinfo)
            return json.loads(result.stdout)['streams'][0]['height']
        except Exception as e: self.log_to_gui(f"  Could not get height of '{os.path.basename(video_path)}'."); logging.error(f"ffprobe error: {e}"); return None

    def process_single_video(self, original_path):
        source_dir, dest_dir = self.source_dir_entry.get(), self.dest_dir_entry.get()
        relative_path, destination_path = os.path.relpath(original_path, source_dir), os.path.join(dest_dir, os.path.relpath(original_path, source_dir))
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        self.log_to_gui(f"Video: '{relative_path}'")
        logging.info(f"Processing Video: '{relative_path}'")
        command = ['ffmpeg', '-i', original_path, '-vcodec', 'libx264', '-crf', str(self.crf_value.get()), '-preset', 'medium', '-map_metadata', '0', '-c:a', 'copy']
        target_height_str = self.resolution_var.get()
        if target_height_str != "Original":
            target_h, original_h = int(target_height_str), self.get_video_height(original_path)
            if original_h and original_h > target_h: self.log_to_gui(f"  -> Downscaling to {target_h}p."); command.extend(['-vf', f'scale=-2:{target_h}'])
        command.append(destination_path)
        try:
            startupinfo = subprocess.STARTUPINFO() if sys.platform == "win32" else None
            if startupinfo: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', startupinfo=startupinfo)
            self.copy_file_timestamps(original_path, destination_path); logging.info(f"SUCCESS on video '{relative_path}'.")
        except subprocess.CalledProcessError as e:
            msg = f"  ERROR on '{relative_path}': {e.stderr.strip()}"; self.log_to_gui(msg); logging.error(msg)
            if os.path.exists(destination_path): os.remove(destination_path)

    def process_single_image(self, original_path):
        source_dir, dest_dir = self.source_dir_entry.get(), self.dest_dir_entry.get()
        relative_path = os.path.relpath(original_path, source_dir)
        destination_path = os.path.join(dest_dir, f"{os.path.splitext(relative_path)[0]}.jpg")
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        self.log_to_gui(f"Image: '{relative_path}'")
        logging.info(f"Processing Image: '{relative_path}'")
        try:
            with Image.open(original_path) as img:
                exif_data = img.getexif()
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.thumbnail((self.img_resolution_var.get(), self.img_resolution_var.get()), Image.Resampling.LANCZOS)
                img.save(destination_path, 'jpeg', quality=self.img_quality_var.get(), exif=exif_data or b'', optimize=True)
                self.copy_file_timestamps(original_path, destination_path); logging.info(f"SUCCESS on image '{relative_path}'.")
        except Exception as e:
            msg = f"  ERROR on image '{relative_path}': {e}"; self.log_to_gui(msg); logging.error(msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = FileProcessorApp(root)
    root.mainloop()