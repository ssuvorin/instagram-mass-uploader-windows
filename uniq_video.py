import sys
import os
import subprocess
import random
import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QHBoxLayout, QVBoxLayout, QComboBox, QCheckBox, QTextEdit, QSpinBox, QProgressBar
)
from PySide6.QtGui import QFont
from pathlib import Path

class VideoProcessor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Видео Уникализатор")
        self.setMinimumSize(800, 1000)
        font = QFont("Arial", 10)

        layout = QVBoxLayout()

        # Входная папка
        self.input_folder_btn = QPushButton("Выбрать папку с видео")
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        self.input_folder_label = QLabel("Не выбрана")
        layout.addWidget(QLabel("Папка с исходными видео:"))
        layout.addWidget(self.input_folder_btn)
        layout.addWidget(self.input_folder_label)

        # Выходная папка
        self.output_folder_btn = QPushButton("Папка для сохранения")
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        self.output_folder_label = QLabel("Не выбрана")
        layout.addWidget(QLabel("Папка для вывода видео:"))
        layout.addWidget(self.output_folder_btn)
        layout.addWidget(self.output_folder_label)

        # Формат видео
        layout.addWidget(QLabel("Формат выходного видео:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["1:1 (1080x1080)", "9:16 (1080x1920)", "16:9 (1920x1080)"])
        layout.addWidget(self.format_combo)

        # Текст
        layout.addWidget(QLabel("Текст для наложения:"))
        self.text_input = QLineEdit()
        layout.addWidget(self.text_input)

        hlayout_text = QHBoxLayout()
        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(10, 200)
        self.font_size_input.setValue(27)
        hlayout_text.addWidget(QLabel("Размер текста:"))
        hlayout_text.addWidget(self.font_size_input)
        layout.addLayout(hlayout_text)

        self.text_checkbox = QCheckBox("Добавить текст (случайная позиция и анимация)")
        layout.addWidget(self.text_checkbox)

        # Бейдж
        self.badge_btn = QPushButton("Загрузить бейдж (png/gif/mp4/mov)")
        self.badge_btn.clicked.connect(self.select_badge_file)
        self.badge_label = QLabel("Не выбран")
        layout.addWidget(self.badge_btn)
        layout.addWidget(self.badge_label)

        self.badge_checkbox = QCheckBox("Добавить бейдж (случайная позиция и масштаб)")
        layout.addWidget(self.badge_checkbox)

        # Количество копий
        layout.addWidget(QLabel("Количество уникальных копий на 1 видео:"))
        self.unique_count_input = QSpinBox()
        self.unique_count_input.setRange(1, 50)
        self.unique_count_input.setValue(3)
        layout.addWidget(self.unique_count_input)

        # Фильтры
        self.cut_checkbox = QCheckBox("Микросрез (0.1-0.3 сек)")
        self.contrast_checkbox = QCheckBox("Повышение контраста (1.0-1.2)")
        self.color_checkbox = QCheckBox("Сдвиг оттенков (-10..10)")
        self.noise_checkbox = QCheckBox("Добавить шум (5-15)")
        self.brightness_checkbox = QCheckBox("Рандомная яркость/насыщенность (0.01-0.1/0.8-1.2)")
        self.crop_checkbox = QCheckBox("Случайная обрезка краёв (95-99%)")
        self.zoompan_checkbox = QCheckBox("Случайное масштабирование (1.0-1.2x)")
        self.emoji_checkbox = QCheckBox("Добавить случайные эмодзи (1-3)")
        layout.addWidget(self.cut_checkbox)
        layout.addWidget(self.contrast_checkbox)
        layout.addWidget(self.color_checkbox)
        layout.addWidget(self.noise_checkbox)
        layout.addWidget(self.brightness_checkbox)
        layout.addWidget(self.crop_checkbox)
        layout.addWidget(self.zoompan_checkbox)
        layout.addWidget(self.emoji_checkbox)

        # Кнопка запуска
        self.start_btn = QPushButton("\ud83d\ude80 Старт обработки")
        self.start_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.start_btn)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        layout.addWidget(QLabel("Прогресс обработки:"))
        layout.addWidget(self.progress_bar)

        # Лог
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с видео")
        if folder:
            self.input_folder_label.setText(folder)
            self.log_output.append(f"Выбрана папка с видео: {folder}")

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if folder:
            self.output_folder_label.setText(folder)
            self.log_output.append(f"Выбрана папка для вывода: {folder}")

    def select_badge_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Выберите файл бейджа", "", "Media Files (*.png *.gif *.mp4 *.mov)")
        if file:
            self.badge_label.setText(file)
            self.log_output.append(f"Выбран бейдж: {file}")

    def calc_position(self, is_text=False, video_w=1080, video_h=1920, badge_w=399, badge_h=225):
        positions = [
            "верх-лево", "верх-центр", "верх-право",
            "центр-лево", "центр-центр", "центр-право",
            "низ-лево", "низ-центр", "низ-право"
        ]
        pos = random.choice(positions)
        position_coords = {
            "верх-лево": (0.05 * video_w, 0.05 * video_h),
            "верх-центр": ((video_w - badge_w) / 2, 0.05 * video_h),
            "верх-право": (max(0, video_w - badge_w - 0.05 * video_w), 0.05 * video_h),
            "центр-лево": (0.05 * video_w, (video_h - badge_h) / 2),
            "центр-центр": ((video_w - badge_w) / 2, (video_h - badge_h) / 2),
            "центр-право": (max(0, video_w - badge_w - 0.05 * video_w), (video_h - badge_h) / 2),
            "низ-лево": (0.05 * video_w, max(0, video_h - badge_h - 0.05 * video_h)),
            "низ-центр": ((video_w - badge_w) / 2, max(0, video_h - badge_h - 0.05 * video_h)),
            "низ-право": (max(0, video_w - badge_w - 0.05 * video_w), max(0, video_h - badge_h - 0.05 * video_h))
        }
        x, y = position_coords[pos]
        if is_text and self.text_checkbox.isChecked():
            directions = [
                ("t*20", "0"), ("-t*20", "0"), ("0", "t*20"), ("0", "-t*20"),
                ("t*20", "t*20"), ("-t*20", "t*20"), ("t*20", "-t*20"), ("-t*20", "-t*20")
            ]
            move_x, move_y = random.choice(directions)
            x_str = f"{x}+{move_x}" if move_x != "0" else str(x)
            y_str = f"{y}+{move_y}" if move_y != "0" else str(y)
            x_str = x_str.replace("+-", "-")
            y_str = y_str.replace("+-", "-")
        else:
            x_str, y_str = str(x), str(y)
        self.log_output.append(f"Позиция {'текста' if is_text else 'бейджа'}: x={x_str}, y={y_str}, позиция={pos}")
        return x_str, y_str, pos

    def random_metadata(self):
        now = datetime.datetime.now()
        random_days = random.randint(-180, 0)
        creation_time = now + datetime.timedelta(days=random_days)
        devices = [
            ("Canon", "EOS R5"), ("Sony", "Alpha 7 IV"), ("Apple", "iPhone 14 Pro"),
            ("Samsung", "S23 Ultra"), ("DJI", "Pocket 3"), ("GoPro", "Hero 11")
        ]
        make, model = random.choice(devices)
        comments = ["Shot on my phone", "Fun moment", "Quick capture"]
        comment = random.choice(comments)
        artists = ["AlexV", "SkyCam", "VlogStar"]
        artist = random.choice(artists)
        return [
            "-metadata", f"title=Video {random.randint(1000, 9999)}",
            "-metadata", f"encoder=FFmpeg {random.randint(4, 5)}.{random.randint(0, 9)}",
            "-metadata", f"artist={artist}",
            "-metadata", f"comment={comment}",
            "-metadata", f"make={make}",
            "-metadata", f"model={model}",
            "-metadata", f"creation_time={creation_time.isoformat()}"
        ]

    def start_processing(self):
        self.log_output.append("\nНачата обработка...")
        input_folder = self.input_folder_label.text()
        output_folder = self.output_folder_label.text()
        badge_file = self.badge_label.text()

        if not Path(input_folder).exists() or not Path(output_folder).exists():
            self.log_output.append("\u274c Укажи папки для входа и выхода!")
            return

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_output.append("\u274c FFmpeg не найден в системе! Убедитесь, что он установлен и добавлен в PATH.")
            return

        if badge_file and not Path(badge_file).exists():
            self.log_output.append(f"\u274c Файл бейджа не найден: {badge_file}")
            badge_file = None
        elif badge_file and self.badge_checkbox.isChecked():
            self.log_output.append(f"Выбран бейдж: {badge_file}")
            try:
                result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(badge_file).replace('\\', '/')], capture_output=True, text=True)
                self.log_output.append(f"Информация о бейдже: {result.stdout}")
                if badge_file.endswith(".gif") and "alpha" not in result.stdout.lower():
                    self.log_output.append("\u26a0 GIF без альфа-канала, используется colorkey=0x000000")
                    try:
                        hist_check = subprocess.run(["ffmpeg", "-i", str(badge_file).replace('\\', '/'), "-vf", "histogram", "-frames:v", "1", "-f", "null", "-"], capture_output=True, text=True)
                        self.log_output.append(f"Проверка цвета фона GIF: {hist_check.stderr}")
                    except subprocess.CalledProcessError as e:
                        self.log_output.append(f"\u274c Ошибка проверки фона GIF: {e.stderr}")
            except subprocess.CalledProcessError as e:
                self.log_output.append(f"\u274c Ошибка проверки бейджа: {e.stderr}")

        video_files = list(Path(input_folder).glob("*.mp4"))
        total_tasks = len(video_files) * self.unique_count_input.value()
        self.progress_bar.setMaximum(total_tasks)
        current_task = 0

        for file in video_files:
            try:
                result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file).replace('\\', '/')], capture_output=True, text=True)
                self.log_output.append(f"Информация о видео {file.name}: {result.stderr}")
                duration = 12.63  # Значение по умолчанию
                try:
                    duration = float(result.stdout.strip())
                except (ValueError, IndexError):
                    self.log_output.append(f"\u26a0 Не удалось определить длительность, используется 12.63 сек")
            except subprocess.CalledProcessError as e:
                self.log_output.append(f"\u274c Ошибка проверки видео {file.name}: {e.stderr}")
                continue

            for i in range(self.unique_count_input.value()):
                current_task += 1
                output_file = Path(output_folder) / f"{file.stem}_v{i+1}.mp4"
                status_msg = f"Обработка {file.name}, копия {i+1}/{self.unique_count_input.value()}"
                self.log_output.append(status_msg)
                print(f"[{datetime.datetime.now()}] {status_msg}")
                
                cmd = self.build_ffmpeg_command(file, output_file, badge_file, duration)
                try:
                    self.log_output.append(f"Команда FFmpeg: {' '.join(cmd)}")
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    self.log_output.append(f"FFmpeg: {result.stdout}")
                    self.log_output.append(f"\u2705 Готово: {output_file.name}")
                    print(f"[{datetime.datetime.now()}] Готово: {output_file.name}")
                except subprocess.CalledProcessError as e:
                    self.log_output.append(f"\u274c Ошибка FFmpeg: {e.stderr}")
                    print(f"[{datetime.datetime.now()}] Ошибка FFmpeg: {e.stderr}")
                except Exception as e:
                    self.log_output.append(f"\u274c Общая ошибка: {str(e)}")
                    print(f"[{datetime.datetime.now()}] Общая ошибка: {str(e)}")

                self.progress_bar.setValue(current_task)
                QApplication.processEvents()

        self.log_output.append("\u2705 Обработка завершена!")
        print(f"[{datetime.datetime.now()}] Обработка завершена!")

    def build_ffmpeg_command(self, input_path, output_path, badge_file, duration):
        filters = []
        fmt = self.format_combo.currentText()
        video_w, video_h = (1080, 1080) if "1:1" in fmt else (1080, 1920) if "9:16" in fmt else (1920, 1080)
        
        # Применение фильтров
        if self.cut_checkbox.isChecked():
            trim_value = random.uniform(0.1, 0.3)
            filters.append(f"trim=start={trim_value},setpts=PTS-STARTPTS")
            self.log_output.append(f"Добавлен фильтр микросреза (trim=start={trim_value})")

        if self.contrast_checkbox.isChecked():
            contrast_value = random.uniform(1.0, 1.2)
            filters.append(f"eq=contrast={contrast_value}")
            self.log_output.append(f"Добавлен фильтр контраста (eq=contrast={contrast_value})")

        if self.color_checkbox.isChecked():
            hue_value = random.uniform(-10, 10)
            filters.append(f"hue=h={hue_value}")
            self.log_output.append(f"Добавлен фильтр сдвига оттенков (hue=h={hue_value})")

        if self.noise_checkbox.isChecked():
            noise_value = random.randint(5, 15)
            filters.append(f"noise=alls={noise_value}:allf=t")
            self.log_output.append(f"Добавлен фильтр шума (noise=alls={noise_value}:allf=t)")

        if self.brightness_checkbox.isChecked():
            brightness_value = random.uniform(0.01, 0.1)
            saturation_value = random.uniform(0.8, 1.2)
            filters.append(f"eq=brightness={brightness_value}:saturation={saturation_value}")
            self.log_output.append(f"Добавлен фильтр яркости/насыщенности (eq=brightness={brightness_value}:saturation={saturation_value})")

        if self.crop_checkbox.isChecked():
            crop_w = random.uniform(0.95, 0.99)
            crop_h = random.uniform(0.95, 0.99)
            crop_x = random.uniform(0, video_w * 0.05)
            crop_y = random.uniform(0, video_h * 0.05)
            filters.append(f"crop=iw*{crop_w}:ih*{crop_h}:{crop_x}:{crop_y}")
            self.log_output.append(f"Добавлен фильтр обрезки краёв (crop=iw*{crop_w}:ih*{crop_h}:{crop_x}:{crop_y})")

        if self.zoompan_checkbox.isChecked():
            zoom_value = random.uniform(1.0, 1.2)
            zoom_start = random.uniform(0, duration - 1)
            zoom_duration = random.uniform(0.5, 2.0)
            filters.append(f"zoompan=z='zoom+{zoom_value-1}':d={int(zoom_duration*25)}:s={video_w}x{video_h}:enable='between(t,{zoom_start},{zoom_start+zoom_duration})'")
            self.log_output.append(f"Добавлен фильтр масштабирования (zoompan=z='zoom+{zoom_value-1}':d={int(zoom_duration*25)}:enable='between(t,{zoom_start},{zoom_start+zoom_duration})')")

        # Масштабирование и padding
        filters.append(f"scale={video_w}:{video_h}:force_original_aspect_ratio=decrease,pad={video_w}:{video_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1")

        badge_scale = random.uniform(0.3, 0.5) if self.badge_checkbox.isChecked() else 0.45
        badge_w = 1443 * badge_scale if badge_file and badge_file.endswith(".gif") else 888 * badge_scale
        badge_h = 612 * badge_scale if badge_file and badge_file.endswith(".gif") else 500 * badge_scale

        text_filters = []
        if self.text_checkbox.isChecked():
            safe_text = self.text_input.text().strip().replace("'", "'\\''").replace(':', '\\:').replace(',', '\\,').replace('=', '\\=')
            if safe_text:
                colors = ["#FFFFFF", "#FFFF00", "#FF0000", "#00FF00", "#0000FF"]
                text_color = random.choice(colors)
                x, y, pos = self.calc_position(is_text=True, video_w=video_w, video_h=video_h, badge_w=0, badge_h=0)
                fontfile = "fonts/arial.ttf"
                if not Path(fontfile).exists():
                    self.log_output.append(f"\u274c Шрифт {fontfile} не найден, текст не будет добавлен!")
                else:
                    text_filters.append(f"drawtext=text='{safe_text}':fontfile='{fontfile}':fontsize={self.font_size_input.value()}:fontcolor={text_color}:x={x}:y={y}")
                    self.log_output.append(f"Добавлен {'анимированный' if self.text_checkbox.isChecked() else 'статичный'} текст: '{safe_text}' в позицию ({x}, {y}), цвет={text_color}, позиция={pos}")

        if self.emoji_checkbox.isChecked():
            emoji_list = ['🦁', '🌟', '🔥', '[PARTY]', '⭐']
            num_emojis = random.randint(1, 3)
            emoji_filters = []
            emoji_fontfile = "fonts/NotoColorEmoji.ttf"
            if not Path(emoji_fontfile).exists():
                self.log_output.append(f"\u274c Шрифт для эмодзи {emoji_fontfile} не найден! Скачайте NotoColorEmoji.ttf с https://fonts.google.com/noto/specimen/Noto+Color+Emoji")
            else:
                for _ in range(num_emojis):
                    emoji = random.choice(emoji_list)
                    emoji_x = random.uniform(0, video_w * 0.8)
                    emoji_y = random.uniform(0, video_h * 0.8)
                    emoji_start = random.uniform(0, duration - 0.5)
                    emoji_duration = random.uniform(0.1, 0.5)
                    emoji_filters.append(f"drawtext=text='{emoji}':fontfile='{emoji_fontfile}':fontsize=48:fontcolor=#FFFFFF:x={emoji_x}:y={emoji_y}:enable='between(t,{emoji_start},{emoji_start+emoji_duration})'")
                    self.log_output.append(f"Добавлен эмодзи '{emoji}' в позицию (x={emoji_x}, y={emoji_y}) с длительностью {emoji_duration} сек")
                text_filters.extend(emoji_filters)

        filters.extend(text_filters)

        cmd = ["ffmpeg", "-y", "-i", str(input_path).replace('\\', '/')]

        if badge_file and Path(badge_file).exists() and self.badge_checkbox.isChecked():
            loop_flag = ["-stream_loop", "-1"] if badge_file.endswith(".gif") else []
            cmd += loop_flag + ["-i", str(badge_file).replace('\\', '/')]
            x, y, pos = self.calc_position(is_text=False, video_w=video_w, video_h=video_h, badge_w=badge_w, badge_h=badge_h)
            badge_filters = f"scale=iw*{badge_scale}:ih*{badge_scale},colorkey=0x000000:0.1:0.1,format=rgba[logo]"
            filter_complex = f"[0:v]{','.join(filters)}[bg];[1:v]{badge_filters};[bg][logo]overlay={x}:{y}:shortest=1"
            cmd += ["-filter_complex", filter_complex]
            self.log_output.append(f"Добавлен бейдж: '{badge_file}' в позицию ({x}, {y}) с масштабом {badge_scale*100:.1f}%, позиция={pos}")
            self.log_output.append(f"Размер бейджа после масштабирования: ~{int(badge_w)}x{int(badge_h)} пикселей")
        else:
            if badge_file and self.badge_checkbox.isChecked():
                self.log_output.append(f"\u274c Бейдж не добавлен, файл недоступен: {badge_file}")
                self.log_output.append("Попробуйте конвертировать бейдж: ffmpeg -i <badge_file> -c:v libx264 -c:a aac badge_converted.mp4")
            cmd += ["-vf", ",".join(filters)]

        cmd += self.random_metadata()
        cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", str(output_path)]
        return cmd

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoProcessor()
    window.show()
    sys.exit(app.exec())