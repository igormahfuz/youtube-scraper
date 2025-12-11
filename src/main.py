"""
Actor to download YouTube videos from a given list of URLs using yt-dlp.
"""

from __future__ import annotations
from apify import Actor
import asyncio
import yt_dlp
import os

async def download_video(video_url: str, quality: str, proxy_url: str | None) -> dict:
    """
    Downloads a YouTube video using yt-dlp.
    """
    Actor.log.info(f"Starting download for video: {video_url} with quality: {quality}")

    output_path = './storage/datasets/default'
    os.makedirs(output_path, exist_ok=True)

    ydl_opts = {
        'format': quality,
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
            return {"status": "success", "file_path": file_path, "video_url": video_url}

    except yt_dlp.utils.DownloadError as e:
        error_message = f"yt-dlp download failed: {e}"
        Actor.log.error(error_message)
        await Actor.push_data({"video_url": video_url, "error": error_message})
        return {"status": "error", "error": error_message, "video_url": video_url}
    except Exception as e:
        error_message = f"An unexpected error occurred: {type(e).__name__}: {e}"
        Actor.log.error(error_message)
        await Actor.push_data({"video_url": video_url, "error": error_message})
        return {"status": "error", "error": error_message, "video_url": video_url}

async def main() -> None:
    async with Actor:
        Actor.log.info("Starting YouTube Downloader Actor.")

        inp = await Actor.get_input() or {}
        video_urls: list[str] = inp.get("videoUrls", [])
        quality: str = inp.get("quality", "best")
        proxy_type = inp.get("proxyType", "RESIDENTIAL")

        if not video_urls:
            raise ValueError("Input 'videoUrls' is required and must be a non-empty list.")

        proxy_configuration = None
        if proxy_type != "NONE":
            Actor.log.info(f"Using {proxy_type} proxies.")
            try:
                proxy_configuration = await Actor.create_proxy_configuration(groups=[proxy_type])
            except Exception as e:
                Actor.log.error(f"Could not create proxy configuration for group '{proxy_type}'. "
                              f"This might be a permission issue with your Apify account. Error: {e}")
                raise
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
                msg += f" ❌ ({result['error']})"
            
            Actor.log.info(msg)
            await Actor.set_status_message(msg)

        final_message = f"Processing finished. Successfully downloaded {success_count}/{total_videos} videos."
        await Actor.set_status_message(final_message)
        Actor.log.info(final_message)
