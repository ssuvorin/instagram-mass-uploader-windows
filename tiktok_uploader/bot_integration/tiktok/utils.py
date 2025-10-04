import os
import shutil

from tiktok_uploader.bot_integration import logger


def delete_video(name):
    try:
        # Получаем корневую директорию проекта
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        video_path = os.path.join(project_root, 'videos', name)
        
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.debug(f'Deleted video {name}')
        else:
            logger.warning(f'Video file not found: {video_path}')
    except Exception as e:
        logger.error(f'Failed to delete video {name}: {str(e)}')

def delete_title(title):
    try:
        # Получаем корневую директорию проекта
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        titles_path = os.path.join(project_root, 'titles', 'titles.txt')
        
        if not os.path.exists(titles_path):
            logger.warning(f'Titles file not found: {titles_path}')
            return
            
        with open(titles_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Удаляем строку с заголовком (учитываем возможные вариации пробелов)
        modified_lines = [line for line in lines if line.strip() != title.strip()]
        
        with open(titles_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
            
        logger.debug(f'Deleted title: {title}')
    except Exception as e:
        logger.error(f'Failed to delete title {title}: {str(e)}')

def delete_profile(name):
    try:
        # Получаем корневую директорию проекта
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        profile_path = os.path.join(project_root, 'accounts', 'accounts_data', name)
        
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path)
            logger.debug(f'Deleted profile directory: {name}')
        else:
            logger.warning(f'Profile directory not found: {profile_path}')
    except Exception as e:
        logger.error(f'Failed to delete profile {name}: {str(e)}')


def safe_delete_after_upload(video_name, description, upload_success):
    """
    Безопасное удаление видео и заголовка только после успешной загрузки
    
    Args:
        video_name (str): Имя видео файла
        description (str): Описание/заголовок видео
        upload_success (bool): Флаг успешной загрузки
    """
    if not upload_success:
        logger.info(f'Upload failed for {video_name}, keeping files')
        return
    
    logger.info(f'Upload successful for {video_name}, cleaning up files')
    delete_video(video_name)
    if description:
        delete_title(description)


def create_backup_before_delete(video_name, description=None):
    """
    Создает резервную копию файлов перед удалением
    
    Args:
        video_name (str): Имя видео файла
        description (str, optional): Описание/заголовок видео
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        backup_dir = os.path.join(project_root, 'backup')
        
        # Создаем директорию backup если её нет
        os.makedirs(backup_dir, exist_ok=True)
        
        # Резервная копия видео
        video_path = os.path.join(project_root, 'videos', video_name)
        if os.path.exists(video_path):
            backup_video_path = os.path.join(backup_dir, f'backup_{video_name}')
            shutil.copy2(video_path, backup_video_path)
            logger.debug(f'Created backup for video: {video_name}')
        
        # Резервная копия заголовков
        if description:
            titles_path = os.path.join(project_root, 'titles', 'titles.txt')
            backup_titles_path = os.path.join(backup_dir, 'backup_titles.txt')
            
            if os.path.exists(titles_path):
                # Добавляем заголовок в backup файл
                with open(backup_titles_path, 'a', encoding='utf-8') as f:
                    f.write(f'{description}\n')
                logger.debug(f'Added title to backup: {description}')
                
    except Exception as e:
        logger.error(f'Failed to create backup: {str(e)}')


def safe_delete_with_backup(video_name, description, upload_success, create_backup=True):
    """
    Безопасное удаление с возможностью создания резервной копии
    
    Args:
        video_name (str): Имя видео файла
        description (str): Описание/заголовок видео
        upload_success (bool): Флаг успешной загрузки
        create_backup (bool): Создавать ли резервную копию
    """
    if not upload_success:
        logger.info(f'Upload failed for {video_name}, keeping files')
        return
    
    if create_backup:
        create_backup_before_delete(video_name, description)
    
    logger.info(f'Upload successful for {video_name}, cleaning up files')
    delete_video(video_name)
    if description:
        delete_title(description)
