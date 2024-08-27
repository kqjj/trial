from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from pytube import YouTube
import os
import subprocess
from dotenv import load_dotenv
import logging

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
PORT = int(os.getenv('PORT', '8443'))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def start(update: Update, context: CallbackContext) -> None:
    user_first_name = update.effective_user.first_name
    update.message.reply_text(f"Welcome {user_first_name}, Send me YouTube Video url, I will give video in your preferred format.")
    logger.info(f"User {user_first_name} started the bot.")

def handle_link(update: Update, context: CallbackContext) -> None:
    url = update.message.text
    logger.info(f"Received URL: {url}")

    if "youtube.com" not in url and "youtu.be" not in url:
        update.message.reply_text("Please send me YouTube link only.")
        logger.warning("Invalid URL received.")
        return

    context.user_data['url'] = url

    keyboard = [
        [
            InlineKeyboardButton("HD QUALITY", callback_data='720p'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Select video format:', reply_markup=reply_markup)

def download_and_merge_video_audio(url, resolution):
    yt = YouTube(url)
    video_stream = yt.streams.filter(res=resolution, mime_type="video/mp4").first()
    audio_stream = yt.streams.filter(only_audio=True, mime_type="audio/mp4").first()

    if not video_stream or not audio_stream:
        raise Exception("Could not find suitable video or audio streams.")

    video_file = video_stream.download(filename='video.mp4')
    audio_file = audio_stream.download(filename='audio.mp4')

    output_file = 'output.mp4'
    cmd = [
        'ffmpeg', '-i', video_file, '-i', audio_file, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', output_file
    ]
    subprocess.run(cmd)

    os.remove(video_file)
    os.remove(audio_file)

    return output_file

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    resolution = query.data
    url = context.user_data['url']
    query.edit_message_text(text=f"Please wait: Downloading {resolution} format")

    try:
        logger.info(f"Downloading video from URL: {url} at resolution: {resolution}")
        video_file = download_and_merge_video_audio(url, resolution)
        query.edit_message_text(text="Download completed. Sending the file...")
        context.bot.send_video(chat_id=query.message.chat_id, video=open(video_file, 'rb'))
        os.remove(video_file)
        logger.info("Video sent successfully.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        query.edit_message_text(text=f"An error occurred: {str(e)}")

def main() -> None:
    updater = Updater(BOT_TOKEN, use_context=True)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dispatcher.add_handler(CallbackQueryHandler(button))

    # Set up webhook
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=BOT_TOKEN,
                          webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    updater.idle()

if __name__ == '__main__':
    main()
