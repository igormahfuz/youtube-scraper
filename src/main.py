"""
Actor to download a YouTube video from a given URL using yt-dlp.
"""

from __future__ import annotations
from apify import Actor
import asyncio
import yt_dlp
import os

async def download_video(video_url: str, proxy_url: str | None) -> dict:
    """
    Downloads a YouTube video using yt-dlp.
    """
    Actor.log.info(f"Starting download for video: {video_url}")

    output_path = './storage/datasets/default'
    os.makedirs(output_path, exist_ok=True)

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
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
            file_path = ydl.prepare_filename(info_dict)

            Actor.log.info(f"Successfully downloaded video to: {file_path}")
            
            # Push metadata to dataset
            await Actor.push_data({
                "video_url": video_url,
                "title": info_dict.get('title'),
                "uploader": info_dict.get('uploader'),
                "duration": info_dict.get('duration'),
                "file_path": file_path,
                "error": None,
            })
            return {"status": "success", "file_path": file_path}

    except yt_dlp.utils.DownloadError as e:
        error_message = f"yt-dlp download failed: {e}"
        Actor.log.error(error_message)
        await Actor.push_data({"video_url": video_url, "error": error_message})
        return {"status": "error", "error": error_message}
    except Exception as e:
        error_message = f"An unexpected error occurred: {type(e).__name__}: {e}"
        Actor.log.error(error_message)
        await Actor.push_data({"video_url": video_url, "error": error_message})
        return {"status": "error", "error": error_message}

async def main() -> None:
    async with Actor:
        Actor.log.info("Starting YouTube Downloader Actor.")

        inp = await Actor.get_input() or {}
        video_url: str = inp.get("videoUrl")
        proxy_type = inp.get("proxyType", "RESIDENTIAL")

        if not video_url:
            raise ValueError("Input 'videoUrl' is required.")

        proxy_configuration = None
        proxy_url_to_use = None
        if proxy_type != "NONE":
            Actor.log.info(f"Using {proxy_type} proxies.")
            try:
                proxy_configuration = await Actor.create_proxy_configuration(groups=[proxy_type])
                if proxy_configuration:
                    proxy_url_to_use = await proxy_configuration.new_url()
            except Exception as e:
                Actor.log.error(f"Could not create proxy configuration for group '{proxy_type}'. "
                              f"This might be a permission issue with your Apify account. Error: {e}")
                raise
        else:
            Actor.log.info("Proxy is disabled.")

        result = await download_video(video_url, proxy_url_to_use)

        if result["status"] == "success":
            await Actor.set_status_message(f"Video downloaded successfully: {result['file_path']}")
            Actor.log.info("Processing finished.")
        else:
            await Actor.set_status_message(f"Failed to download video. Check log for details.")
            Actor.log.error(f"Error details: {result['error']}")