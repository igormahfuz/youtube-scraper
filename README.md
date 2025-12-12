# Actor – YouTube Video Downloader

[![Apify Actor](https://img.shields.io/badge/Apify-Actor-2f77ff)](https://apify.com) [![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/) [![yt-dlp](https://img.shields.io/badge/yt--dlp-supported-orange)](https://github.com/yt-dlp/yt-dlp) [![Docker](https://img.shields.io/badge/Docker-ready-2496ED)](https://www.docker.com/)

## Overview
This Actor downloads YouTube videos using `yt-dlp`, stores the file in Apify Key-Value Store with a public download link, and pushes clean metadata to Dataset (title, uploader, duration, original URL, error).

## Features
- Download videos from a list of YouTube URLs
- Quality selection via `yt-dlp` format strings (with safe presets)
- Apify proxy groups support (`RESIDENTIAL`, etc.) or `NONE` to disable
- Public download URLs via Key-Value Store
- Structured metadata in Dataset

## Input Parameters
- `videoUrls` (`Array<string>`, required): List of YouTube video URLs
- `quality` (`String`, optional, default `best`): `yt-dlp` format/preset. Examples: `best`, `worst`, `bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best`, `bestvideo[height<=1080]+bestaudio/best[height<=1080]`, `bestvideo[height<=720]+bestaudio/best[height<=720]`, `bestvideo[height<=480]+bestaudio/best[height<=480]`, `bestvideo[height<=360]+bestaudio/best[height<=360]`
- `proxyType` (`String`, optional, default `RESIDENTIAL`): Exact Apify proxy group name. Use `NONE` to disable

### Input Example
```json
{
  "videoUrls": [
    "https://www.youtube.com/watch?v=XqZsoesa55w",
    "https://www.youtube.com/watch?v=PsNyag6JGv4",
    "https://www.youtube.com/watch?v=ctEksNz7tqg"
  ],
  "quality": "best",
  "proxyType": "RESIDENTIAL"
}
```

## During the Run
- Progress is logged and set as `statusMessage`: `processed/total → URL ✔/❌`
- Invalid input (e.g., empty `videoUrls`) immediately fails with explanation

## Output
- Key-Value Store: video file saved under a unique key. Public link format:
  `https://api.apify.com/v2/key-value-stores/{STORE_ID}/records/{KEY}`
- Dataset item fields per video:
  - `video_url`, `title`, `uploader`, `duration`, `download_url`, `error`

### Example Dataset Item
```json
{
  "video_url": "https://www.youtube.com/watch?v=ADs8tvU2xDc",
  "title": "...",
  "uploader": "Red Bull",
  "duration": 123,
  "download_url": "https://api.apify.com/v2/key-value-stores/STORE_ID/records/ADs8tvU2xDc_...",
  "error": null
}
```

## Use on Apify (UI)
1. Open the Actor in Apify
2. Fill the input form (`videoUrls`, optional `quality`, `proxyType`)
3. Run and monitor `statusMessage`. Files appear in KV Store; metadata in Dataset

## Run via API
- Start a run:
```bash
curl -X POST "https://api.apify.com/v2/acts/OWNER~youtube-video-downloader/runs?token=YOUR_APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "videoUrls": [
      "https://www.youtube.com/watch?v=XqZsoesa55w"
    ],
    "quality": "best",
    "proxyType": "RESIDENTIAL"
  }'
```
- Get items from Dataset:
```bash
curl "https://api.apify.com/v2/datasets/DATASET_ID/items?clean=true"
```
- Download file via `download_url` from the dataset item

### Node.js example
```js
const fetch = require('node-fetch');
const input = {
  videoUrls: ["https://www.youtube.com/watch?v=XqZsoesa55w"],
  quality: "best",
  proxyType: "RESIDENTIAL",
};
const res = await fetch("https://api.apify.com/v2/acts/OWNER~youtube-video-downloader/runs?token=YOUR_APIFY_TOKEN", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(input),
});
const run = await res.json();
```

## Run Locally
```bat
apify run
```
Or with Docker on Windows:
```bat
docker build -t youtube-video-downloader .
docker run -e APIFY_TOKEN=YOUR_APIFY_TOKEN -v %CD%\apify_storage:/app/apify_storage youtube-video-downloader
```

## Performance Notes
Compute unit usage depends on number of videos, selected quality, and proxy/network stability. Typical runs process dozens of videos in minutes.

## Bugs, fixes, updates, and changelog
This Actor is under active development. If you have feature requests or find bugs, please open an issue.
