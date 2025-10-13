#!/usr/bin/env python
"""
Асинхронный модуль для уникализации видео в bulk upload tasks
Интегрирует логику из uniq_video.py в async версию
"""

import os
import sys
import asyncio
import subprocess
import random
import datetime
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import time
import logging

# В начале файла добавляем импорт Windows совместимости
try:
    from .windows_compatibility import run_subprocess_windows, get_windows_temp_dir, is_windows
except ImportError:
    # Fallback если модуль не найден
    def run_subprocess_windows(cmd, timeout=300, cwd=None, capture_output=True, text=True):
        return subprocess.run(cmd, timeout=timeout, cwd=cwd, capture_output=capture_output, text=text)
    
    def get_windows_temp_dir():
        return tempfile.gettempdir()
    
    def is_windows():
        import platform
        return platform.system().lower() == "windows"

@dataclass
class UniqueVideoConfig:
    """Конфигурация для уникализации видео"""
    # Фильтры
    cut_enabled: bool = True
    contrast_enabled: bool = True
    color_enabled: bool = True
    # Шум резко увеличивает итоговый битрейт при CRF — отключаем по умолчанию
    noise_enabled: bool = False
    brightness_enabled: bool = True
    crop_enabled: bool = True
    zoompan_enabled: bool = True
    emoji_enabled: bool = False
    
    # Текст
    text_enabled: bool = True
    text_content: str = ""
    text_font_size: int = 27
    
    # Бейдж
    badge_enabled: bool = True
    badge_file_path: str = ""
    
    # Формат видео
    video_format: str = "9:16"  # "1:1", "9:16", "16:9"

    # Параметры кодирования (читаются из окружения при импорте, можно переопределить в рантайме)
    crf: int = field(default_factory=lambda: int(os.getenv("VIDEO_CRF", "27")))
    preset: str = field(default_factory=lambda: os.getenv("VIDEO_PRESET", "medium"))
    audio_bitrate: str = field(default_factory=lambda: os.getenv("VIDEO_AUDIO_BITRATE", "96k"))
    pix_fmt: str = field(default_factory=lambda: os.getenv("VIDEO_PIX_FMT", "yuv420p"))
    profile: str = field(default_factory=lambda: os.getenv("VIDEO_PROFILE", "high"))
    level: str = field(default_factory=lambda: os.getenv("VIDEO_LEVEL", "4.1"))
    
    @classmethod
    def create_random_config(cls, account_username: str = "") -> 'UniqueVideoConfig':
        """Создать случайную конфигурацию уникализации"""
        return cls(
            cut_enabled=random.choice([True, False]),
            contrast_enabled=random.choice([True, False]),
            color_enabled=random.choice([True, False]),
            # Отключаем шум — главная причина «тяжёлых» файлов при CRF
            noise_enabled=False,
            brightness_enabled=random.choice([True, False]),
            crop_enabled=random.choice([True, False]),
            zoompan_enabled=False,  # Отключаем zoompan - он медленный
            emoji_enabled=False,    # Отключаем эмодзи - они тоже медленные
            text_enabled=False,     # Отключаем наложение текста с никнеймом
            text_content="",        # Пустой текст
            text_font_size=random.randint(20, 35),
            badge_enabled=False,  # Отключаем бейдж по умолчанию для bulk upload
            video_format="9:16"  # Instagram format
        )

class AsyncVideoUniquifier:
    """Асинхронный уникализатор видео"""
    
    def __init__(self, config: Optional[UniqueVideoConfig] = None):
        self.config = config or UniqueVideoConfig()
        self.temp_files = []
    
    async def uniquify_video_async(self, input_path: str, account_username: str, 
                                 copy_number: int = 1) -> str:
        """
        Асинхронно создать уникальную версию видео для аккаунта
        
        Args:
            input_path: путь к исходному видео
            account_username: имя пользователя аккаунта
            copy_number: номер копии (для случая когда одно видео используется несколько раз)
            
        Returns:
            путь к уникализированному видео
        """
        # Создаем случайную конфигурацию для каждого аккаунта
        unique_config = UniqueVideoConfig.create_random_config(account_username)
        
        # Генерируем уникальное имя файла
        input_path_obj = Path(input_path)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{input_path_obj.stem}_{account_username}_{timestamp}_v{copy_number}.mp4"
        
        # Создаем временный файл для результата
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, output_filename)
        
        # Запускаем FFmpeg асинхронно
        try:
            # Python 3.9+
            success = await asyncio.to_thread(
                self._process_video_sync, input_path, output_path, unique_config, account_username
            )
        except AttributeError:
            # Fallback для Python < 3.9
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(
                None, self._process_video_sync, input_path, output_path, unique_config, account_username
            )
        
        if success and os.path.exists(output_path):
            self.temp_files.append(output_path)
            return output_path
        else:
            raise Exception(f"Failed to create unique video for account {account_username}")
    
    def _process_video_sync(self, input_path: str, output_path: str, 
                           config: UniqueVideoConfig, account_username: str) -> bool:
        """Синхронная обработка видео с помощью FFmpeg"""
        # Проверяем наличие входного файла
        if not os.path.exists(input_path):
            print(f"[FAIL] [UNIQUIFY] Input file does not exist: {input_path}")
            return False
        
        file_size = os.path.getsize(input_path)
        print(f"[FOLDER] [UNIQUIFY] Input file: {os.path.basename(input_path)} ({file_size} bytes)")
        
        # Проверяем доступность FFmpeg
        if not check_ffmpeg_availability():
            print(f"[FAIL] FFmpeg not found! Please install FFmpeg and add it to PATH.")
            print(f"[FALLBACK] Copying original file without uniquification")
            
            # Fallback: просто копируем оригинальный файл
            try:
                import shutil
                shutil.copy2(input_path, output_path)
                if os.path.exists(output_path):
                    print(f"[OK] [FALLBACK] Copied original file: {os.path.basename(output_path)}")
                    return True
                else:
                    print(f"[FAIL] [FALLBACK] Failed to copy original file")
                    return False
            except Exception as e:
                print(f"[FAIL] [FALLBACK] Error copying file: {e}")
                return False
        
        try:
            # Получаем длительность видео
            duration = self._get_video_duration(input_path)
            
            # Строим команду FFmpeg
            cmd = self._build_ffmpeg_command(input_path, output_path, config, duration, account_username)
            
            print(f"[VIDEO] [UNIQUIFY] Processing video for {account_username}...")
            print(f"[TOOL] [UNIQUIFY] FFmpeg command: {' '.join(cmd[:8])}... (truncated)")  # Показываем только начало команды
            
            # Выполняем команду с таймаутом
            start_time = time.time()
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 минут максимум на обработку
            )
            processing_time = time.time() - start_time
            
            # Проверяем что выходной файл создан
            if os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                print(f"[OK] [UNIQUIFY] Successfully created unique video: {os.path.basename(output_path)} ({output_size} bytes, took {processing_time:.1f}s)")
                return True
            else:
                print(f"[FAIL] [UNIQUIFY] Output file was not created: {output_path}")
                return False
            
        except subprocess.TimeoutExpired:
            print(f"⏰ [UNIQUIFY] FFmpeg timeout (>300s) for {account_username}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] [UNIQUIFY] FFmpeg error: {e.stderr}")
            return False
        except Exception as e:
            print(f"[FAIL] [UNIQUIFY] General error: {str(e)}")
            return False
    
    def _get_video_duration(self, video_path: str) -> float:
        """Получить длительность видео"""
        try:
            print(f"[SEARCH] [UNIQUIFY] Getting video duration for: {os.path.basename(video_path)}")
            
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                print(f"⏱️  [UNIQUIFY] Video duration: {duration:.2f}s")
                return duration
            else:
                print(f"[WARN] [UNIQUIFY] ffprobe failed: {result.stderr}")
                return 12.63
                
        except subprocess.TimeoutExpired:
            print(f"⏰ [UNIQUIFY] ffprobe timeout, using default duration 12.63s")
            return 12.63
        except (subprocess.CalledProcessError, ValueError):
            print(f"[WARN] [UNIQUIFY] Could not determine video duration, using default 12.63s")
            return 12.63
        except Exception as e:
            print(f"[WARN] [UNIQUIFY] Unexpected error getting duration: {e}, using default 12.63s")
            return 12.63
    
    def _build_ffmpeg_command(self, input_path: str, output_path: str, 
                             config: UniqueVideoConfig, duration: float, 
                             account_username: str) -> List[str]:
        """Построить команду FFmpeg для уникализации"""
        filters = []
        
        # Определяем размеры видео
        video_w, video_h = self._get_video_dimensions(config.video_format)
        
        # Применяем фильтры уникализации
        if config.cut_enabled:
            trim_value = random.uniform(0.1, 0.3)
            filters.append(f"trim=start={trim_value},setpts=PTS-STARTPTS")
            print(f"🔪 [UNIQUIFY] Added cut filter: trim=start={trim_value}")
        
        if config.contrast_enabled:
            contrast_value = random.uniform(1.0, 1.2)
            filters.append(f"eq=contrast={contrast_value}")
            print(f"🔆 [UNIQUIFY] Added contrast filter: eq=contrast={contrast_value}")
        
        if config.color_enabled:
            hue_value = random.uniform(-10, 10)
            filters.append(f"hue=h={hue_value}")
            print(f"🌈 [UNIQUIFY] Added color filter: hue=h={hue_value}")
        
        if config.noise_enabled:
            # Делаем шум очень мягким, чтобы не раздувать битрейт
            noise_value = random.randint(1, 3)
            filters.append(f"noise=alls={noise_value}:allf=t")
            print(f"📺 [UNIQUIFY] Added mild noise filter: noise=alls={noise_value}")
        
        if config.brightness_enabled:
            brightness_value = random.uniform(0.01, 0.1)
            saturation_value = random.uniform(0.8, 1.2)
            filters.append(f"eq=brightness={brightness_value}:saturation={saturation_value}")
            print(f"💡 [UNIQUIFY] Added brightness/saturation filter")
        
        if config.crop_enabled:
            crop_w = random.uniform(0.95, 0.99)
            crop_h = random.uniform(0.95, 0.99)
            crop_x = random.uniform(0, video_w * 0.05)
            crop_y = random.uniform(0, video_h * 0.05)
            filters.append(f"crop=iw*{crop_w}:ih*{crop_h}:{crop_x}:{crop_y}")
            print(f"✂️ [UNIQUIFY] Added crop filter")
        
        if config.zoompan_enabled:
            zoom_value = random.uniform(1.0, 1.2)
            zoom_duration = random.uniform(0.5, 2.0)
            # Убираем enable параметр так как zoompan его не поддерживает
            filters.append(f"zoompan=z='zoom+{zoom_value-1}':d={int(zoom_duration*25)}:s={video_w}x{video_h}")
            print(f"[SEARCH] [UNIQUIFY] Added zoom/pan filter: zoom={zoom_value:.3f}, duration={zoom_duration:.1f}s")
        
        # Масштабирование и padding
        filters.append(f"scale={video_w}:{video_h}:force_original_aspect_ratio=decrease,pad={video_w}:{video_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1")
        
        # Добавляем текст
        text_filters = []
        if config.text_enabled and config.text_content.strip():
            safe_text = self._escape_text(config.text_content.strip())
            if safe_text:
                colors = ["#FFFFFF", "#FFFF00", "#FF0000", "#00FF00", "#0000FF"]
                text_color = random.choice(colors)
                x, y = self._calculate_text_position(video_w, video_h)
                
                # Используем встроенный шрифт
                text_filters.append(f"drawtext=text='{safe_text}':fontsize={config.text_font_size}:fontcolor={text_color}:x={x}:y={y}")
                print(f"[TEXT] [UNIQUIFY] Added text: '{safe_text}' at ({x}, {y}), color={text_color}")
        
        # Добавляем эмодзи
        if config.emoji_enabled:
            emoji_list = ['🦁', '🌟', '🔥', '[PARTY]', '⭐']
            num_emojis = random.randint(1, 3)
            for _ in range(num_emojis):
                emoji = random.choice(emoji_list)
                emoji_x = random.uniform(0, video_w * 0.8)
                emoji_y = random.uniform(0, video_h * 0.8)
                emoji_start = random.uniform(0, max(0.1, duration - 0.5))
                emoji_duration = random.uniform(0.1, 0.5)
                
                text_filters.append(f"drawtext=text='{emoji}':fontsize=48:fontcolor=#FFFFFF:x={emoji_x}:y={emoji_y}:enable='between(t,{emoji_start},{emoji_start+emoji_duration})'")
                print(f"😀 [UNIQUIFY] Added emoji '{emoji}' at ({emoji_x}, {emoji_y})")
        
        filters.extend(text_filters)
        
        # Строим команду
        cmd = ["ffmpeg", "-y", "-i", input_path]
        cmd += ["-vf", ",".join(filters)]
        cmd += self._random_metadata(account_username)
        cmd += [
            "-c:v", "libx264",
            "-preset", str(config.preset),
            "-crf", str(config.crf),
            "-pix_fmt", str(config.pix_fmt),
            "-profile:v", str(config.profile),
            "-level", str(config.level),
            "-c:a", "aac",
            "-b:a", str(config.audio_bitrate),
            "-movflags", "+faststart",
            output_path,
        ]
        
        return cmd
    
    def _get_video_dimensions(self, video_format: str) -> Tuple[int, int]:
        """Получить размеры видео по формату"""
        if "1:1" in video_format:
            return 1080, 1080
        elif "9:16" in video_format:
            return 1080, 1920
        elif "16:9" in video_format:
            return 1920, 1080
        else:
            return 1080, 1920  # По умолчанию Instagram format
    
    def _escape_text(self, text: str) -> str:
        """Экранировать текст для FFmpeg"""
        return text.replace("'", "'\\''").replace(':', '\\:').replace(',', '\\,').replace('=', '\\=')
    
    def _calculate_text_position(self, video_w: int, video_h: int) -> Tuple[str, str]:
        """Вычислить позицию текста"""
        positions = [
            ("верх-лево", (0.05 * video_w, 0.05 * video_h)),
            ("верх-центр", ((video_w - 200) / 2, 0.05 * video_h)),
            ("верх-право", (max(0, video_w - 200 - 0.05 * video_w), 0.05 * video_h)),
            ("центр-лево", (0.05 * video_w, (video_h - 50) / 2)),
            ("центр-центр", ((video_w - 200) / 2, (video_h - 50) / 2)),
            ("центр-право", (max(0, video_w - 200 - 0.05 * video_w), (video_h - 50) / 2)),
            ("низ-лево", (0.05 * video_w, max(0, video_h - 50 - 0.05 * video_h))),
            ("низ-центр", ((video_w - 200) / 2, max(0, video_h - 50 - 0.05 * video_h))),
            ("низ-право", (max(0, video_w - 200 - 0.05 * video_w), max(0, video_h - 50 - 0.05 * video_h)))
        ]
        
        pos_name, (x, y) = random.choice(positions)
        
        # Добавляем движение текста
        directions = [
            ("t*20", "0"), ("-t*20", "0"), ("0", "t*20"), ("0", "-t*20"),
            ("t*20", "t*20"), ("-t*20", "t*20"), ("t*20", "-t*20"), ("-t*20", "-t*20")
        ]
        move_x, move_y = random.choice(directions)
        
        x_str = f"{x}+{move_x}" if move_x != "0" else str(x)
        y_str = f"{y}+{move_y}" if move_y != "0" else str(y)
        x_str = x_str.replace("+-", "-")
        y_str = y_str.replace("+-", "-")
        
        print(f"[LOCATION] [UNIQUIFY] Text position: {pos_name}, x={x_str}, y={y_str}")
        return x_str, y_str
    
    def _random_metadata(self, account_username: str) -> List[str]:
        """Генерировать случайные метаданные"""
        now = datetime.datetime.now()
        random_days = random.randint(-180, 0)
        creation_time = now + datetime.timedelta(days=random_days)
        
        devices = [
            ("Apple", "iPhone 12"), ("Apple", "iPhone 12 Pro"), ("Apple", "iPhone 12 Pro Max"),
            ("Apple", "iPhone 13"), ("Apple", "iPhone 13 mini"), ("Apple", "iPhone 13 Pro"), ("Apple", "iPhone 13 Pro Max"),
            ("Apple", "iPhone 14"), ("Apple", "iPhone 14 Plus"), ("Apple", "iPhone 14 Pro"), ("Apple", "iPhone 14 Pro Max"),
            ("Apple", "iPhone 15"), ("Apple", "iPhone 15 Plus"), ("Apple", "iPhone 15 Pro"), ("Apple", "iPhone 15 Pro Max"),
            ("Apple", "iPhone SE (3rd Gen)"),
            
            ("Samsung", "Galaxy S21"), ("Samsung", "Galaxy S21 Ultra"),
            ("Samsung", "Galaxy S22"), ("Samsung", "Galaxy S22 Ultra"),
            ("Samsung", "Galaxy S23"), ("Samsung", "Galaxy S23 Ultra"),
            ("Samsung", "Galaxy S24"), ("Samsung", "Galaxy S24+"), ("Samsung", "Galaxy S24 Ultra"),
            ("Samsung", "Galaxy Note 20"),
            ("Samsung", "Galaxy Z Fold 4"), ("Samsung", "Galaxy Z Fold 5"),
            ("Samsung", "Galaxy Z Flip 4"), ("Samsung", "Galaxy Z Flip 5"),
            ("Samsung", "Galaxy A54"), ("Samsung", "Galaxy A34"),
            
            ("Google", "Pixel 6"), ("Google", "Pixel 6 Pro"), ("Google", "Pixel 6a"),
            ("Google", "Pixel 7"), ("Google", "Pixel 7 Pro"), ("Google", "Pixel 7a"),
            ("Google", "Pixel 8"), ("Google", "Pixel 8 Pro"), ("Google", "Pixel 8a"),
            ("Google", "Pixel Fold"),
            
            ("Sony", "Xperia 1 IV"), ("Sony", "Xperia 5 IV"), ("Sony", "Xperia 10 V"),
            ("Sony", "Xperia 1 V"), ("Sony", "Xperia 5 V"), ("Sony", "Xperia Pro-I"), ("Sony", "Xperia 1 VI"),
            
            ("Xiaomi", "12T Pro"), ("Xiaomi", "13"), ("Xiaomi", "13 Pro"), ("Xiaomi", "13 Ultra"),
            ("Xiaomi", "14"), ("Xiaomi", "14 Pro"), ("Xiaomi", "14 Ultra"),
            ("Xiaomi", "Redmi Note 12"), ("Xiaomi", "Redmi Note 12 Pro"),
            ("Xiaomi", "Redmi Note 13"), ("Xiaomi", "Redmi Note 13 Pro"),
            ("Xiaomi", "Poco F5"), ("Xiaomi", "Poco F5 Pro"), ("Xiaomi", "Poco X6 Pro"),
            
            ("OnePlus", "9"), ("OnePlus", "9 Pro"), ("OnePlus", "10 Pro"), ("OnePlus", "10T"),
            ("OnePlus", "11"), ("OnePlus", "11R"), ("OnePlus", "12"), ("OnePlus", "12R"),
            ("OnePlus", "Nord 2T"), ("OnePlus", "Nord 3"),
            
            ("Huawei", "P50"), ("Huawei", "P50 Pro"), ("Huawei", "P60 Pro"),
            ("Huawei", "Mate 50"), ("Huawei", "Mate 50 Pro"), ("Huawei", "Mate 60 Pro"),
            ("Huawei", "Nova 10"), ("Huawei", "Nova 11"),
            
            ("Oppo", "Find X5"), ("Oppo", "Find X5 Pro"), ("Oppo", "Find X6 Pro"), ("Oppo", "Find X7 Ultra"),
            ("Oppo", "Reno 9"), ("Oppo", "Reno 10"), ("Oppo", "Reno 11"), ("Oppo", "A98"),
            
            ("Vivo", "X90"), ("Vivo", "X90 Pro"), ("Vivo", "X100"), ("Vivo", "X100 Pro"),
            ("Vivo", "Y78"), ("Vivo", "V29"),
            
            ("Nokia", "X30"), ("Nokia", "G60"), ("Nokia", "8.3 5G"),
            
            ("ASUS", "Zenfone 9"), ("ASUS", "Zenfone 10"), ("ASUS", "ROG Phone 7"), ("ASUS", "ROG Phone 8"),
            
            ("Motorola", "Edge 30 Pro"), ("Motorola", "Edge 40"), ("Motorola", "Edge 40 Pro"),
            ("Motorola", "Razr 40"), ("Motorola", "Razr 40 Ultra"),
            
            ("Nothing", "Phone (1)"), ("Nothing", "Phone (2)"), ("Nothing", "Phone (2a)"),
            
            ("Honor", "Magic 5 Pro"), ("Honor", "Magic 6 Pro"), ("Honor", "Magic V2"),
            
            ("Realme", "GT 2 Pro"), ("Realme", "GT 5 Pro"), ("Realme", "11 Pro+"), ("Realme", "12 Pro+"),
            
            ("ZTE", "Axon 40 Ultra"), ("Nubia", "RedMagic 8 Pro"),
            
            ("Meizu", "20 Pro"), ("Infinix", "Zero 30 5G"), ("Infinix", "Note 30 Pro"),
            ("Tecno", "Phantom X2 Pro"), ("Tecno", "Camon 20 Pro"),
            
            ("Lenovo", "Legion Phone Duel 2"), ("Black Shark", "5 Pro"),
            ("iQOO", "12"), ("iQOO", "12 Pro"),
            
            ("Fairphone", "5"), ("CAT", "S62 Pro"), ("Sharp", "Aquos R8 Pro"), ("HTC", "U23 Pro"),
            ("TCL", "40 Pro 5G"),
            
            # Non-phone devices kept for variety
            ("Canon", "EOS R5"), ("Sony", "Alpha 7 IV"), ("DJI", "Pocket 3"), ("GoPro", "Hero 11"), ("Insta360", "X3")
        ]
        make, model = random.choice(devices)
        
        comments = [f"Shot by {account_username}", "Fun moment", "Quick capture", f"From @{account_username}"]
        comment = random.choice(comments)
        
        artists = [account_username, "Creator", "VideoMaker"]
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
    
    async def cleanup_temp_files_async(self) -> None:
        """Асинхронно очистить временные файлы уникализации с проверкой на shutdown"""
        def cleanup():
            for file_path in self.temp_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        print(f"[DELETE] [UNIQUIFY] Cleaned up temp file: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"[WARN] [UNIQUIFY] Could not delete temp file {file_path}: {str(e)}")
            self.temp_files.clear()
        
        # Запускаем очистку асинхронно с проверкой на shutdown
        try:
            # Проверяем, что event loop еще работает
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                print("[WARN] [UNIQUIFY] Event loop is closed, skipping async cleanup")
                cleanup()  # Выполняем синхронно
                return
            
            # Python 3.9+
            await asyncio.to_thread(cleanup)
        except AttributeError:
            # Fallback для Python < 3.9
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    await loop.run_in_executor(None, cleanup)
                else:
                    cleanup()  # Выполняем синхронно
            except RuntimeError as e:
                if "cannot schedule new futures after shutdown" in str(e):
                    print("[WARN] [UNIQUIFY] Event loop shutdown detected, using sync cleanup")
                    cleanup()  # Выполняем синхронно
                else:
                    raise
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e):
                print("[WARN] [UNIQUIFY] Event loop shutdown detected, using sync cleanup")
                cleanup()  # Выполняем синхронно
            else:
                raise

# Глобальный экземпляр для использования в async задачах
_global_uniquifier = None

async def get_video_uniquifier() -> AsyncVideoUniquifier:
    """Получить глобальный экземпляр уникализатора"""
    global _global_uniquifier
    if _global_uniquifier is None:
        _global_uniquifier = AsyncVideoUniquifier()
    return _global_uniquifier

async def uniquify_video_for_account(input_path: str, account_username: str, 
                                   copy_number: int = 1) -> str:
    """
    Удобная функция для уникализации видео для конкретного аккаунта
    
    Args:
        input_path: путь к исходному видео
        account_username: имя пользователя аккаунта
        copy_number: номер копии
        
    Returns:
        путь к уникализированному видео
    """
    uniquifier = await get_video_uniquifier()
    return await uniquifier.uniquify_video_async(input_path, account_username, copy_number)

async def cleanup_uniquifier_temp_files():
    """Очистить все временные файлы уникализатора с проверкой на shutdown"""
    global _global_uniquifier
    if _global_uniquifier:
        try:
            await _global_uniquifier.cleanup_temp_files_async()
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e):
                print("[WARN] [UNIQUIFY] Event loop shutdown detected, skipping cleanup")
            else:
                raise

def cleanup_hanging_ffmpeg():
    """Очистка зависших FFmpeg процессов"""
    try:
        import psutil
        import platform
        
        is_windows = platform.system().lower() == 'windows'
        ffmpeg_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                    ffmpeg_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if ffmpeg_processes:
            print(f"[TOOL] [UNIQUIFY_CLEANUP] Found {len(ffmpeg_processes)} FFmpeg processes")
            for proc in ffmpeg_processes:
                try:
                    # Проверяем как долго процесс работает
                    create_time = proc.create_time()
                    runtime = time.time() - create_time
                    
                    # На Windows используем более короткий таймаут
                    timeout_threshold = 300 if is_windows else 600  # 5 минут для Windows, 10 для остальных
                    
                    if runtime > timeout_threshold:
                        print(f"💀 [UNIQUIFY_CLEANUP] Killing long-running FFmpeg process (PID: {proc.pid}, runtime: {runtime:.1f}s)")
                        
                        if is_windows:
                            # На Windows сначала пробуем мягкое завершение
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                proc.kill()
                                proc.wait(timeout=2)
                        else:
                            proc.kill()
                            proc.wait(timeout=5)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue
                    
        print(f"[OK] [UNIQUIFY_CLEANUP] FFmpeg cleanup completed")
        
        # На Windows добавляем небольшую задержку
        if is_windows:
            time.sleep(0.5)
        
    except ImportError:
        print(f"[WARN] [UNIQUIFY_CLEANUP] psutil not available, cannot cleanup FFmpeg processes")
    except Exception as e:
        print(f"[FAIL] [UNIQUIFY_CLEANUP] Error during FFmpeg cleanup: {str(e)}")

def check_ffmpeg_availability() -> bool:
    """Проверка доступности FFmpeg"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        # Если не найден в PATH, попробуем добавить стандартные пути
        try:
            import os
            standard_paths = [
                r"C:\ffmpeg\bin",
                r"C:\Program Files\ffmpeg\bin",
                r"C:\Program Files (x86)\ffmpeg\bin",
                r"C:\tools\ffmpeg\bin",
            ]
            
            for path in standard_paths:
                if os.path.exists(os.path.join(path, "ffmpeg.exe")):
                    # Временно добавляем в PATH
                    old_path = os.environ.get('PATH', '')
                    os.environ['PATH'] = path + os.pathsep + old_path
                    
                    result = subprocess.run(["ffmpeg", "-version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        print(f"[OK] [FFMPEG_CHECK] Found FFmpeg at: {path}")
                        return True
        except Exception:
            pass
        
        return False

def uniquify_video_sync(input_path: str, output_path: str, quality: int = 23) -> bool:
    """Синхронная уникализация видео с Windows совместимостью"""
    try:
        # Проверяем доступность FFmpeg
        if not check_ffmpeg_availability():
            print("[FAIL] [UNIQUIFY] FFmpeg not available")
            return False
        
        # Создаем команду FFmpeg
        cmd = [
            "ffmpeg", "-i", input_path,
            "-c:v", "libx264",
            "-crf", str(quality),
            "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-level", "4.1",
            "-c:a", "aac",
            "-b:a", "96k",
            "-movflags", "+faststart",
            "-y",  # Перезаписывать выходной файл
            output_path
        ]
        
        print(f"[TOOL] [UNIQUIFY] FFmpeg command: {' '.join(cmd[:8])}... (truncated)")
        
        # Используем Windows-совместимый subprocess
        result = run_subprocess_windows(
            cmd,
            timeout=300,  # 5 минут таймаут
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"[OK] [UNIQUIFY] Video uniquified successfully: {output_path}")
            return True
        else:
            print(f"[FAIL] [UNIQUIFY] FFmpeg failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("[FAIL] [UNIQUIFY] FFmpeg timeout")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] [UNIQUIFY] FFmpeg error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] [UNIQUIFY] Unexpected error: {e}")
        return False

def get_video_info_sync(video_path: str) -> Optional[Dict]:
    """Получение информации о видео с Windows совместимостью"""
    try:
        # Команда для получения информации о видео
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        # Используем Windows-совместимый subprocess
        result = run_subprocess_windows(cmd, timeout=30, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        else:
            print(f"[FAIL] [UNIQUIFY] FFprobe failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[FAIL] [UNIQUIFY] FFprobe timeout")
        return None
    except (subprocess.CalledProcessError, ValueError):
        print("[FAIL] [UNIQUIFY] FFprobe error")
        return None
    except Exception as e:
        print(f"[FAIL] [UNIQUIFY] Unexpected error: {e}")
        return None 