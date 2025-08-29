import requests
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

HIKER_API_KEY = "w0xxjcp8m2dym58s6lyzyraqjddhwel9"

async def analyze_hashtag_full(hashtag_name: str) -> dict:
    """Анализирует ВСЕ видео хэштега быстро"""
    headers = {
        'accept': 'application/json',
        'x-access-key': HIKER_API_KEY
    }
    
    try:
        print(f"🔍 Анализ хэштега: #{hashtag_name}")
        
        # Получаем информацию о хэштеге
        hashtag_info_url = f"https://api.hikerapi.com/v1/hashtag/by/name?name={hashtag_name}"
        response = requests.get(hashtag_info_url, headers=headers, timeout=30)
        
        if response.status_code == 402:
            return {"error": "💳 Недостаточно средств на аккаунте HikerAPI. Пополните баланс на https://hikerapi.com/billing"}
        elif response.status_code != 200:
            return {"error": f"Ошибка API: {response.status_code}"}
        
        hashtag_data = response.json()
        media_count = hashtag_data.get('media_count', 0)
        print(f"📹 Всего видео: {media_count}")
        
        if media_count == 0:
            return {"error": "Хэштег не найден или не содержит видео"}
        
        # Собираем ВСЕ видео через пагинацию
        all_videos = []
        next_page_id = None
        page = 1
        
        while len(all_videos) < media_count:
            # Формируем URL
            if next_page_id:
                clips_url = f"https://api.hikerapi.com/v2/hashtag/medias/clips?name={hashtag_name}&page_id={next_page_id}"
            else:
                clips_url = f"https://api.hikerapi.com/v2/hashtag/medias/clips?name={hashtag_name}"
            
            # Показываем прогресс только каждые 5 страниц
            if page % 5 == 1:
                print(f"📄 Страница {page}: {len(all_videos)}/{media_count}")
            
            response = requests.get(clips_url, headers=headers, timeout=60)
            
            if response.status_code != 200:
                break
            
            chunk_data = response.json()
            
            # Извлекаем видео из структуры ответа
            videos = []
            next_page_id = None
            
            if isinstance(chunk_data, dict) and 'response' in chunk_data:
                response_data = chunk_data['response']
                
                # Быстрое извлечение видео из секций
                sections = response_data.get('sections', [])
                
                # Диагностика секций (только на первой странице)
                if page == 1:
                    section_types = [s.get('layout_type', 'unknown') for s in sections]
                    print(f"🔍 Типы секций: {section_types}")
                
                for section in sections:
                    layout_content = section.get('layout_content', {})
                    section_videos = []
                    
                    # Для media_grid - самый частый тип
                    if 'medias' in layout_content:
                        medias = layout_content['medias']
                        for item in medias:
                            media = item.get('media')
                            if media and 'play_count' in media:
                                section_videos.append(media)
                        videos.extend(section_videos)
                    
                    # Для clips секций
                    elif 'one_by_two_item' in layout_content:
                        clips = layout_content['one_by_two_item'].get('clips', {})
                        # items
                        items = clips.get('items', [])
                        for item in items:
                            media = item.get('media')
                            if media and 'play_count' in media:
                                section_videos.append(media)
                        # fill_items
                        fill_items = clips.get('fill_items', [])
                        for item in fill_items:
                            media = item.get('media')
                            if media and 'play_count' in media:
                                section_videos.append(media)
                        videos.extend(section_videos)
                        if page <= 2:  # Диагностика первых страниц
                            print(f"   🎬 one_by_two_item: {len(items)} items + {len(fill_items)} fill_items = {len(section_videos)} с play_count")
                    
                    # Дополнительные типы секций
                    elif 'clips' in layout_content:
                        clips = layout_content['clips']
                        # items
                        items = clips.get('items', [])
                        for item in items:
                            media = item.get('media')
                            if media and 'play_count' in media:
                                section_videos.append(media)
                        # fill_items  
                        fill_items = clips.get('fill_items', [])
                        for item in fill_items:
                            media = item.get('media')
                            if media and 'play_count' in media:
                                section_videos.append(media)
                        videos.extend(section_videos)
                    
                    # Неизвестные типы секций
                    else:
                        if page <= 2:
                            available_keys = list(layout_content.keys())
                            print(f"   ❓ Неизвестная секция с ключами: {available_keys}")
                
                if page <= 2:  # Общая диагностика первых страниц
                    print(f"   ➡️ Всего найдено на странице {page}: {len(videos)} видео")
                
                # Получаем next_page_id
                next_page_id = response_data.get('next_page_id')
                
                # Дополнительно проверяем next_page_id на корневом уровне
                if not next_page_id and 'next_page_id' in chunk_data:
                    next_page_id = chunk_data.get('next_page_id')
            
            if not videos:
                print(f"❌ Остановка: нет видео на странице {page}")
                break
            
            all_videos.extend(videos)
            page += 1
            
            # Диагностика остановки
            if not next_page_id:
                print(f"❌ Остановка: нет next_page_id на странице {page-1}")
                # Проверяем more_available только для информации
                if isinstance(chunk_data, dict) and 'response' in chunk_data:
                    more_available = chunk_data['response'].get('more_available')
                    print(f"📊 more_available: {more_available}")
                break
            
            # Игнорируем more_available и продолжаем пока есть next_page_id
            # Защита от бесконечного цикла остается
            if page > 50:
                print(f"❌ Остановка: достигнут лимит 50 страниц")
                break
        
        # Быстрый подсчет статистики без диагностики
        total_play_count = sum(
            int(video.get('play_count', 0)) 
            for video in all_videos 
            if isinstance(video, dict) and isinstance(video.get('play_count'), (int, float))
        )
        analyzed_videos = sum(
            1 for video in all_videos 
            if isinstance(video, dict) and isinstance(video.get('play_count'), (int, float))
        )
        
        print(f"📥 {len(all_videos)} видео, 👀 {total_play_count:,} просмотров")
        
        # Итоговая статистика
        summary = {
            "hashtag_name": hashtag_name,
            "timestamp": datetime.now().isoformat(),
            "total_videos": media_count,
            "fetched_videos": len(all_videos),
            "analyzed_videos": analyzed_videos,
            "videos_without_play_count": len(all_videos) - analyzed_videos,
            "total_views": total_play_count,
            "average_views": total_play_count / analyzed_videos if analyzed_videos > 0 else 0,
            "pages_loaded": page - 1
        }
        
        return summary
        
    except requests.exceptions.Timeout:
        return {"error": "Превышено время ожидания ответа от API"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"error": f"Произошла ошибка: {str(e)}"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🎬 Привет! Я бот для быстрого анализа хэштегов Instagram.\n\n"
        "Просто отправь мне название хэштега (без #) и я:\n"
        "• Проанализирую ВСЕ видео\n"
        "• Подсчитаю общее количество просмотров\n"
        "• Покажу детальную статистику\n\n"
        "Пример: caspin14"
    )

async def handle_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения с хэштегами"""
    hashtag_name = update.message.text.strip()
    
    if hashtag_name.startswith('#'):
        hashtag_name = hashtag_name[1:]
    
    if not hashtag_name:
        await update.message.reply_text("❌ Пожалуйста, введите название хэштега")
        return
    
    status_message = await update.message.reply_text(
        f"🔍 Анализирую хэштег #{hashtag_name}...\n"
        f"Это может занять несколько минут."
    )
    
    result = await analyze_hashtag_full(hashtag_name)
    
    if "error" in result:
        await status_message.edit_text(f"❌ {result['error']}")
        return
    
    # Форматируем результат
    coverage_percent = (result['analyzed_videos'] / result['total_videos']) * 100 if result['total_videos'] > 0 else 0
    
    response_text = f"""
📊 ПОЛНЫЙ АНАЛИЗ ХЭШТЕГА #{result['hashtag_name']}

📹 Всего видео: {result['total_videos']:,}
📥 Загружено: {result['fetched_videos']:,}
🔍 С данными просмотров: {result['analyzed_videos']:,}
❌ Без данных просмотров: {result['videos_without_play_count']:,}
📄 Страниц загружено: {result['pages_loaded']}

👀 Общие просмотры: {result['total_views']:,}
📈 Среднее на видео: {result['average_views']:,.0f}

📊 Покрытие: {coverage_percent:.1f}%

{"✅ Все видео проанализированы!" if result['fetched_videos'] >= result['total_videos'] else f"⚠️ Загружено {result['fetched_videos']} из {result['total_videos']} видео"}
"""
    
    await status_message.edit_text(response_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🤖 БОТ ДЛЯ БЫСТРОГО АНАЛИЗА ХЭШТЕГОВ INSTAGRAM

Возможности:
✅ Быстрый анализ всех видео хэштега
✅ Подсчет общего количества просмотров
✅ Детальная статистика
✅ Анализ через пагинацию

Команды:
/start - Начать работу
/help - Показать справку

Просто отправьте название хэштега без # для анализа.
"""
    
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке запроса. Проверьте логи."
        )

def main():
    """Запуск бота"""
    BOT_TOKEN = "8037834166:AAER_S3xYbuwzhlN0EZZ7GVjkrWm1a1TxfU"
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hashtag))
    application.add_error_handler(error_handler)
    
    print("🤖 Быстрый бот для анализа хэштегов запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
