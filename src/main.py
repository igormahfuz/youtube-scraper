"""
Actor to download YouTube videos from a given list of URLs using yt-dlp.
"""

from __future__ import annotations
from apify import Actor
import asyncio
import yt_dlp
import os
import mimetypes
import uuid
import re

async def download_video(video_url: str, quality: str, proxy_url: str | None) -> dict:
    """
    Downloads a YouTube video using yt-dlp, saves it to the key-value store,
    and returns a public URL for download.
    """
    Actor.log.info(f"Starting download for video: {video_url} with quality: {quality}")

    # Temporary path to store the downloaded video
    temp_path = './temp_video'
    os.makedirs(temp_path, exist_ok=True)

    ydl_opts = {
        'format': quality,
        'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'progress_hooks': [lambda d: Actor.log.info(f"yt-dlp status: {d['status']}") if d['status'] in ['downloading', 'finished'] else None],
    }

    if proxy_url:
        ydl_opts['proxy'] = proxy_url
        Actor.log.info(f"Using proxy: {proxy_url}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            local_file_path = ydl.prepare_filename(info_dict)

            if not local_file_path or not os.path.exists(local_file_path):
                raise FileNotFoundError(f"yt-dlp did not download the file for URL: {video_url}")

            Actor.log.info(f"Successfully downloaded video to temporary path: {local_file_path}")

            # Read the downloaded file
            with open(local_file_path, 'rb') as f:
                video_content = f.read()
            
            # Get mime type
            mime_type, _ = mimetypes.guess_type(local_file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Save to key-value store
            key_value_store_id = os.environ.get('APIFY_DEFAULT_KEY_VALUE_STORE_ID')

            # Sanitize title for key name
            title = info_dict.get('title', 'video')
            # Replace invalid characters with an underscore
            sanitized_title = re.sub(r'[^a-zA-Z0-9!-_.\'()]', '_', title)
            # Replace multiple underscores with a single one
            sanitized_title = re.sub(r'__+', '_', sanitized_title)
            
            # Add UUID to avoid collisions and ensure uniqueness
            record_key = f"{sanitized_title[:200]}_{uuid.uuid4().hex}"

            await Actor.set_value(record_key, video_content, content_type=mime_type)
            
            # Construct the public URL
            # The public URL is in the format: https://api.apify.com/v2/key-value-stores/{STORE_ID}/records/{KEY_NAME}?disableRedirect=true
            download_url = f"https://api.apify.com/v2/key-value-stores/{key_value_store_id}/records/{record_key}"

            Actor.log.info(f"Saved video to key-value store. Download link: {download_url}")

            # Push metadata to dataset
            output_data = {
                "video_url": video_url,
                "title": info_dict.get('title'),
                "uploader": info_dict.get('uploader'),
                "duration": info_dict.get('duration'),
                "download_url": download_url,
                "error": None,
            }
            await Actor.push_data(output_data)

            # Clean up the local file
            os.remove(local_file_path)

            return {"status": "success", "download_url": download_url, "video_url": video_url}

    except Exception as e:
        error_message = f"An unexpected error occurred: {type(e).__name__}: {e}"
        Actor.log.error(error_message)
        await Actor.push_data({"video_url": video_url, "title": None, "uploader": None, "duration": None, "download_url": None, "error": error_message})
        return {"status": "error", "error": error_message, "video_url": video_url}

async def main() -> None:
    async with Actor:
        Actor.log.info("Starting YouTube Downloader Actor.")

        inp = await Actor.get_input() or {}
        video_urls: list[str] = inp.get("videoUrls", [])
        quality: str = inp.get("quality", "best")
        proxy_type = inp.get("proxyType", "RESIDENTIAL")

        if not video_urls:
            await Actor.fail(status_message="Input 'videoUrls' is required and must be a non-empty list.")
            return

        proxy_configuration = None
        if proxy_type != "NONE":
            Actor.log.info(f"Using {proxy_type} proxies.")
            try:
                proxy_configuration = await Actor.create_proxy_configuration(groups=[proxy_type])
            except Exception as e:
                await Actor.fail(
                    status_message=f"Could not create proxy configuration for group '{proxy_type}'. "
                                 f"This might be a permission issue with your Apify account. Error: {e}"
                )
                return
        else:
            Actor.log.info("Proxy is disabled.")

        download_tasks = []
        for video_url in video_urls:
            proxy_url_to_use = await proxy_configuration.new_url() if proxy_configuration else None
            task = download_video(video_url, quality, proxy_url_to_use)
            download_tasks.append(task)
        
        total_videos = len(download_tasks)
        processed_count = 0
        success_count = 0
        
        Actor.log.info(f"Starting download of {total_videos} videos.")

        for future in asyncio.as_completed(download_tasks):
            result = await future
            processed_count += 1
            
            video_url_processed = result.get('video_url', 'N/A')
            msg = f"{processed_count}/{total_videos} → {video_url_processed}"
            
            if result.get("status") == "success":
                success_count += 1
                msg += " ✔"
            else:
                msg += f" ❌ ({result.get('error', 'Unknown error')})"
            
            Actor.log.info(msg)
            await Actor.set_status_message(msg)

        final_message = f"Processing finished. Successfully downloaded {success_count}/{total_videos} videos."
        await Actor.set_status_message(final_message)
        Actor.log.info(final_message)
