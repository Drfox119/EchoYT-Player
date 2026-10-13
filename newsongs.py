import yt_dlp

import playlists


def search_videos(query: str, max_results: int = 5):
    """Search YouTube and return a list of {"title", "url"} dicts.

    Non-interactive: raises on failure and never prompts the user.
    """

    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "playlistend": max_results,
    }

    search_url = f"ytsearch{max_results}:{query}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_url, download=False)
        entries = (info or {}).get("entries", []) or []

    videos = []

    for item in entries:
        title = item.get("title", "Untitled")
        video_id = item.get("id")
        url = item.get("url") or f"https://www.youtube.com/watch?v={video_id}"

        videos.append({
            "title": title,
            "url": url,
        })

    return videos


def add_to_playlist(url: str, title: str = None, playlist: str = None):
    """Add a track to a playlist unless it is already there.

    Returns True when added, False when the track is a duplicate.
    """

    return playlists.add_item(url, title, playlist)


def fetch_title(url: str):
    """Resolve a single URL to its title (blocking; use in a worker thread)."""

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return (info or {}).get("title")


def search_youtube(query: str, max_results: int = 5):
    print(f"\nSearching YouTube for '{query}'...\n")

    try:
        results = search_videos(query, max_results)

    except Exception as e:
        print(f"Search failed: {e}")
        return None

    if not results:
        print("No results found.")
        return None

    videos = {idx: video for idx, video in enumerate(results, start=1)}

    print("Results:\n")

    for idx, video in videos.items():
        print(f"{idx}. {video['title']}")
        print(f"   {video['url']}\n")

    while True:
        try:
            choice = int(input(f"Choose a video (1-{len(videos)}): "))

            if choice in videos:
                return videos[choice]

            print(f"Invalid choice. Please choose between 1 and {len(videos)}.")

        except ValueError:
            print("Please enter a valid number.")


def new():
    try:
        search_count_input = input(
            "How many search results to show? (default 5): "
        ).strip()

        search_results = int(search_count_input) if search_count_input else 5

    except ValueError:
        print("Invalid number provided. Defaulting to 5.")
        search_results = 5

    query = input("\nEnter the song/video name: ").strip()

    if not query:
        print("Search query cannot be empty!")
        return

    selected_video = search_youtube(
        query,
        max_results=search_results
    )

    if selected_video:
        print(f"\nYou selected: {selected_video['title']}")

        # "a" automatically creates playlist.txt
        # if it doesn't already exist.
        added = add_to_playlist(selected_video["url"], selected_video.get("title"))

        if added:
            print("Added to playlist!")
        else:
            print("Already in the playlist, skipped.")

        return selected_video
