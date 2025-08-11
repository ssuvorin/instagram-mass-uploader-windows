import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import random
import numpy as np
from datetime import datetime, timedelta
from moviepy.editor import VideoFileClip, CompositeVideoClip
import glob
from PIL import Image

class VideoUniquelizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Uniquelizer for TikTok & Instagram")
        self.root.geometry("600x850")

        # Variables
        self.input_folder = tk.StringVar()
        self.badge_video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.num_copies = tk.StringVar(value="3")
        self.badge_size = tk.StringVar(value="30")
        self.badge_position = tk.StringVar(value="top-right")
        self.resolution = tk.StringVar(value="9:16")
        self.badge_timing = tk.StringVar(value="start")
        self.status = tk.StringVar(value="Ready to process")
        self.fixed_position_var = tk.BooleanVar(value=True)
        self.random_position_var = tk.BooleanVar(value=False)

        # GUI Elements
        tk.Label(root, text="Input Folder (Videos):").pack(pady=5)
        tk.Entry(root, textvariable=self.input_folder, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_input_folder).pack()

        tk.Label(root, text="Badge Video (.mov):").pack(pady=5)
        tk.Entry(root, textvariable=self.badge_video_path, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_badge_video).pack()

        tk.Label(root, text="Output Directory:").pack(pady=5)
        tk.Entry(root, textvariable=self.output_dir, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_output_dir).pack()

        tk.Label(root, text="Number of Unique Copies per Video:").pack(pady=5)
        frame = tk.Frame(root)
        frame.pack()
        for val in ["3", "5", "15", "25"]:
            tk.Radiobutton(frame, text=val, variable=self.num_copies, value=val).pack(side=tk.LEFT)

        tk.Label(root, text="Badge Size (% of main video width):").pack(pady=5)
        tk.Entry(root, textvariable=self.badge_size, width=10).pack()

        # Position selection
        tk.Checkbutton(root, text="Fixed Position", variable=self.fixed_position_var, command=self.update_position_options).pack()
        self.position_menu = tk.OptionMenu(root, self.badge_position, "top-right",
                                         "top-left", "top-center", "top-right",
                                         "center-left", "center", "center-right",
                                         "bottom-left", "bottom-center", "bottom-right")
        self.position_menu.pack()
        tk.Checkbutton(root, text="Random Position", variable=self.random_position_var, command=self.update_position_options).pack()

        tk.Label(root, text="Badge Timing:").pack(pady=5)
        timing_options = ["start", "random"]
        tk.OptionMenu(root, self.badge_timing, *timing_options).pack()

        tk.Label(root, text="Output Resolution:").pack(pady=5)
        resolutions = ["1:1", "9:16", "16:9"]
        tk.OptionMenu(root, self.resolution, *resolutions).pack()

        tk.Button(root, text="Process Videos", command=self.process_videos).pack(pady=20)

        tk.Label(root, text="Status:").pack(pady=5)
        tk.Label(root, textvariable=self.status, wraplength=500).pack()

    def browse_input_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.input_folder.set(path)

    def browse_badge_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mov")])
        if path:
            self.badge_video_path.set(path)

    def browse_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def update_position_options(self):
        if self.random_position_var.get():
            self.fixed_position_var.set(False)
            self.position_menu.config(state="disabled")
        elif self.fixed_position_var.get():
            self.random_position_var.set(False)
            self.position_menu.config(state="normal")

    def modify_exif(self, output_path):
        """Modify EXIF metadata using exiftool"""
        try:
            random_date = (datetime.now() - timedelta(days=random.randint(1, 1000))).strftime("%Y:%m:%d %H:%M:%S")
            random_device = random.choice([
                "iPhone 12", "iPhone 12 Pro", "iPhone 12 Pro Max",
                "iPhone 13", "iPhone 13 mini", "iPhone 13 Pro", "iPhone 13 Pro Max",
                "iPhone 14", "iPhone 14 Plus", "iPhone 14 Pro", "iPhone 14 Pro Max",
                "iPhone 15", "iPhone 15 Plus", "iPhone 15 Pro", "iPhone 15 Pro Max",
                "iPhone SE (3rd Gen)",
                
                "Samsung Galaxy S21", "Samsung Galaxy S21 Ultra",
                "Samsung Galaxy S22", "Samsung Galaxy S22 Ultra",
                "Samsung Galaxy S23", "Samsung Galaxy S23 Ultra",
                "Samsung Galaxy S24", "Samsung Galaxy S24+", "Samsung Galaxy S24 Ultra",
                "Samsung Galaxy Note 20",
                "Samsung Galaxy Z Fold 4", "Samsung Galaxy Z Fold 5",
                "Samsung Galaxy Z Flip 4", "Samsung Galaxy Z Flip 5",
                "Samsung Galaxy A54", "Samsung Galaxy A34",
                
                "Google Pixel 6", "Google Pixel 6 Pro", "Google Pixel 6a",
                "Google Pixel 7", "Google Pixel 7 Pro", "Google Pixel 7a",
                "Google Pixel 8", "Google Pixel 8 Pro", "Google Pixel 8a",
                "Google Pixel Fold",
                
                "Sony Xperia 1 IV", "Sony Xperia 5 IV", "Sony Xperia 10 V",
                "Sony Xperia 1 V", "Sony Xperia 5 V", "Sony Xperia Pro-I", "Sony Xperia 1 VI",
                
                "Xiaomi 12T Pro", "Xiaomi 13", "Xiaomi 13 Pro", "Xiaomi 13 Ultra",
                "Xiaomi 14", "Xiaomi 14 Pro", "Xiaomi 14 Ultra",
                "Xiaomi Redmi Note 12", "Xiaomi Redmi Note 12 Pro",
                "Xiaomi Redmi Note 13", "Xiaomi Redmi Note 13 Pro",
                "Xiaomi Poco F5", "Xiaomi Poco F5 Pro", "Xiaomi Poco X6 Pro",
                
                "OnePlus 9", "OnePlus 9 Pro", "OnePlus 10 Pro", "OnePlus 10T",
                "OnePlus 11", "OnePlus 11R", "OnePlus 12", "OnePlus 12R",
                "OnePlus Nord 2T", "OnePlus Nord 3",
                
                "Huawei P50", "Huawei P50 Pro", "Huawei P60 Pro",
                "Huawei Mate 50", "Huawei Mate 50 Pro", "Huawei Mate 60 Pro",
                "Huawei Nova 10", "Huawei Nova 11",
                
                "Oppo Find X5", "Oppo Find X5 Pro", "Oppo Find X6 Pro", "Oppo Find X7 Ultra",
                "Oppo Reno 9", "Oppo Reno 10", "Oppo Reno 11", "Oppo A98",
                
                "Vivo X90", "Vivo X90 Pro", "Vivo X100", "Vivo X100 Pro",
                "Vivo Y78", "Vivo V29",
                
                "Nokia X30", "Nokia G60", "Nokia 8.3 5G",
                
                "ASUS Zenfone 9", "ASUS Zenfone 10", "ASUS ROG Phone 7", "ASUS ROG Phone 8",
                
                "Motorola Edge 30 Pro", "Motorola Edge 40", "Motorola Edge 40 Pro",
                "Motorola Razr 40", "Motorola Razr 40 Ultra",
                
                "Nothing Phone (1)", "Nothing Phone (2)", "Nothing Phone (2a)",
                
                "Honor Magic 5 Pro", "Honor Magic 6 Pro", "Honor Magic V2",
                
                "Realme GT 2 Pro", "Realme GT 5 Pro", "Realme 11 Pro+", "Realme 12 Pro+",
                
                "ZTE Axon 40 Ultra", "Nubia RedMagic 8 Pro",
                
                "Meizu 20 Pro", "Infinix Zero 30 5G", "Infinix Note 30 Pro",
                "Tecno Phantom X2 Pro", "Tecno Camon 20 Pro",
                
                "Lenovo Legion Phone Duel 2", "Black Shark 5 Pro",
                "iQOO 12", "iQOO 12 Pro",
                
                "Fairphone 5", "CAT S62 Pro", "Sharp Aquos R8 Pro", "HTC U23 Pro",
                "TCL 40 Pro 5G",
                
                # Также оставим несколько не-телефонов для разнообразия
                "Canon EOS R5", "Sony Alpha 7 IV", "DJI Pocket 3", "GoPro Hero 11", "Insta360 X3"
            ])
            random_gps = f"{random.uniform(-90, 90):.6f}{random.choice(['N', 'S'])} {random.uniform(-180, 180):.6f}{random.choice(['E', 'W'])}"

            subprocess.run([
                "exiftool",
                "-AllDates=" + random_date,
                "-Model=" + random_device,
                "-GPSCoordinates=" + random_gps,
                "-overwrite_original",
                output_path
            ], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to modify EXIF: {e}")
            return False
        return True

    def modify_hash(self, clip):
        """Slightly modify video to change hash with minimal noise"""
        def add_noise(image):
            noise = np.zeros(image.shape, dtype=np.uint8)
            mask = np.random.choice([0, 1], size=image.shape[:2], p=[0.99, 0.01])
            noise[mask == 1] = np.random.normal(0, 0.3, noise[mask == 1].shape).astype(np.uint8)
            return np.clip(image + noise, 0, 255)
        return clip.fl_image(add_noise)

    def resize_video(self, clip, aspect_ratio):
        """Resize video to specified aspect ratio with black bars if needed"""
        w, h = clip.size
        if w > 1280 or h > 720:
            scale = min(1280 / w, 720 / h)
            clip = clip.resize((int(w * scale), int(h * scale)))
            w, h = clip.size

        if aspect_ratio == "1:1":
            size = min(w, h)
            # Добавляем черные полосы вместо обрезки
            if w > h:
                new_h = size
                new_w = size
                padding_h = (w - h) // 2
                clip = clip.margin(top=padding_h, bottom=padding_h, opacity=0)
            else:
                new_w = size
                new_h = size
                padding_w = (h - w) // 2
                clip = clip.margin(left=padding_w, right=padding_w, opacity=0)
            return clip.resize((new_w, new_h))
        elif aspect_ratio == "9:16":
            new_h = h
            new_w = int(h * 9 / 16)
            if new_w > w:
                padding = (new_w - w) // 2
                clip = clip.margin(left=padding, right=padding, opacity=0)
            else:
                clip = clip.resize((new_w, new_h))
            return clip
        elif aspect_ratio == "16:9":
            new_w = w
            new_h = int(w * 9 / 16)
            if new_h > h:
                padding = (new_h - h) // 2
                clip = clip.margin(top=padding, bottom=padding, opacity=0)
            else:
                clip = clip.resize((new_w, new_h))
            return clip
        return clip

    def get_position_coordinates(self, main_size, badge_size, position):
        """Calculate badge position coordinates with padding"""
        main_w, main_h = main_size
        badge_w, badge_h = badge_size

        # Отступы 5% от ширины и высоты видео (можно настроить)
        padding_x = int(main_w * 0.05)
        padding_y = int(main_h * 0.05)

        # Позиции с учетом отступов
        position_map = {
            "top-left": (padding_x, padding_y),
            "top-center": ((main_w - badge_w) // 2, padding_y),
            "top-right": (main_w - badge_w - padding_x, padding_y),
            "center-left": (padding_x, (main_h - badge_h) // 2),
            "center": ((main_w - badge_w) // 2, (main_h - badge_h) // 2),
            "center-right": (main_w - badge_w - padding_x, (main_h - badge_h) // 2),
            "bottom-left": (padding_x, max(0, main_h - badge_h - padding_y)),
            "bottom-center": ((main_w - badge_w) // 2, max(0, main_h - badge_h - padding_y)),
            "bottom-right": (max(0, main_w - badge_w - padding_x), max(0, main_h - badge_h - padding_y))
        }
        return position_map.get(position, (0, 0))

    def process_videos(self):
        """Process videos: uniquelize, resize, and add badges with optimization"""
        try:
            input_folder = self.input_folder.get()
            badge_video = self.badge_video_path.get()
            output_dir = self.output_dir.get()
            num_copies = int(self.num_copies.get())
            badge_size_percent = float(self.badge_size.get())
            resolution = self.resolution.get()
            badge_timing = self.badge_timing.get()

            if not input_folder or not output_dir:
                messagebox.showerror("Error", "Please select input folder and output directory")
                return
            if not os.path.exists(input_folder):
                messagebox.showerror("Error", "Input folder does not exist")
                return
            if badge_size_percent <= 0 or badge_size_percent > 100:
                messagebox.showerror("Error", "Badge size must be between 1 and 100%")
                return

            os.makedirs(output_dir, exist_ok=True)

            # Get list of video files
            video_files = glob.glob(os.path.join(input_folder, "*.mp4")) + glob.glob(os.path.join(input_folder, "*.mov"))
            total_videos = len(video_files)
            processed_videos = 0

            if not video_files:
                messagebox.showerror("Error", "No video files found in input folder")
                return

            self.status.set(f"Processing 0/{total_videos} videos...")
            self.root.update()

            # Load badge video once if provided
            badge_clip_template = None
            if badge_video and os.path.exists(badge_video):
                badge_clip_template = VideoFileClip(badge_video, has_mask=True)

            # Process each video
            for video_path in video_files:
                main_clip = VideoFileClip(video_path)
                main_clip = self.resize_video(main_clip, resolution)
                main_w, main_h = main_clip.size
                main_duration = main_clip.duration

                # Prepare badge video for this main video
                badge_clip = None
                if badge_clip_template:
                    badge_scale = badge_size_percent / 100
                    badge_w = int(main_w * badge_scale)
                    badge_h = int(badge_w * (badge_clip_template.h / badge_clip_template.w))
                    badge_clip = badge_clip_template.resize((badge_w, badge_h))
                    badge_duration = badge_clip.duration

                    # Установка времени наложения бейджа
                    if badge_timing == "start":
                        badge_start_time = 0
                    else:  # random
                        badge_start_time = random.uniform(0, main_duration - badge_duration) if main_duration > badge_duration else 0
                    badge_clip = badge_clip.set_start(badge_start_time)
                    badge_clip = badge_clip.set_duration(min(badge_duration, main_duration - badge_start_time))

                # Create unique copies
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                for i in range(num_copies):
                    output_path = os.path.join(output_dir, f"{video_name}_unique_{i+1}.mp4")
                    modified_clip = self.modify_hash(main_clip)

                    if badge_clip:
                        # Выбор позиции
                        if self.random_position_var.get():
                            positions = ["top-left", "top-center", "top-right", "center-left", "center", "center-right", "bottom-left", "bottom-center", "bottom-right"]
                            random_position = random.choice(positions)
                            badge_pos = self.get_position_coordinates((main_w, main_h), (badge_w, badge_h), random_position)
                        else:
                            badge_pos = self.get_position_coordinates((main_w, main_h), (badge_w, badge_h), self.badge_position.get())
                        modified_clip = CompositeVideoClip([
                            modified_clip,
                            badge_clip.set_position(badge_pos)
                        ])

                    modified_clip.write_videofile(
                        output_path,
                        codec="libx264",
                        audio_codec="aac",
                        preset="ultrafast",
                        threads=2,
                        ffmpeg_params=["-crf", "23"]
                    )
                    self.modify_exif(output_path)

                    modified_clip.close()

                processed_videos += 1
                self.status.set(f"Processing {processed_videos}/{total_videos} videos...")
                self.root.update()

                main_clip.close()
                if badge_clip:
                    badge_clip.close()

            if badge_clip_template:
                badge_clip_template.close()

            self.status.set(f"Completed! Processed {total_videos} videos.")
            messagebox.showinfo("Success", f"Processed {total_videos} videos, each with {num_copies} unique copies.")

        except Exception as e:
            self.status.set("Error occurred")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoUniquelizerApp(root)
    root.mainloop()