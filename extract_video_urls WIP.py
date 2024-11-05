def extract_video_urls(self) -> List[str]:
    """Extract individual video URLs from playlists or single video URLs.
    
    Returns:
        List[str]: A list containing individual video URLs extracted from
                   the provided URLs (including those within playlists).
    """
    
    # Initialize an empty list to store all extracted video URLs
    all_video_urls = []
    
    # Iterate through each URL provided in self.urls
    for url in self.urls:
        
        # Check if the download process was stopped by the user
        if self._is_stopped:
            # Emit a status update message to inform that the process was stopped
            self.status_update.emit("Download stopped by user.")
            break  # Exit the loop if stopped
        
        # Emit a status update message indicating which URL is currently being processed
        self.status_update.emit(f"Attempting to extract video urls from URL {url}")
        
        ydl_opts_flat = {
                    'quiet': True,
                    'skip_download': True,
                    'ignoreerrors': True,
                    'no_color': True,       # Do not stick color text in output that will cause problems
                }
        
        if self.cookies_file:
            ydl_opts_flat['cookiefile'] = str(self.cookies_file)
            self.logger.debug(f"Using cookies file for extraction: {self.cookies_file}")
        else:
            self.logger.debug(f"No cookie file provided.")
        
        try:
            # Configure yt_dlp to extract info without downloading (use flat extraction for playlists)
            with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
                # Attempt to extract information from the URL
                info_dict = ydl.extract_info(url, download=False)
                
                if info_dict is None:
                    self.logger.error(f"No metadata found for URL: {url}")
                    self.failed_urls.append({"url": url, "reason": "No metadata found."})
                    continue
                info_type = info_dict.get('_type', 'video') #get what the info type is
                
                # If the URL is a playlist, info will contain 'entries'
                if 'entries' in info:
                    for entry in info['entries']:  # Loop through each entry in the playlist
                        # Append each individual video URL to the list
                        all_video_urls.append(entry['url'])
                else:
                    # For a single video URL, add it directly to the list
                    all_video_urls.append(url)
        
        except Exception as e:
            # Log an error if extraction fails and add the URL to failed downloads, also print what the info type is
            self.logger.error(f"Failed to extract URLs from {url}: {e}")
            self.failed_downloads.append((url, "Failed to extract video URLs"))
            self.logger.warning(f"Unhandled type: {info_type} for URL: {url}")

    # Return the list of extracted video URLs
    return all_video_urls

    def process_video_url(self, video_url: str):
        """Download and process an individual video URL."""
        if self._is_stopped:
            self.status_update.emit("Download stopped by user.")
            break
        try:
            output_file_path = self.output_path / f"{clean_filename(video_url)}.mp4"
            
            if video_url in self.download_manager.downloaded_files or output_file_path.exists():
                self.logger.info(f"File for URL {video_url} already downloaded, skipping.")
                return
            
            self.download_manager.download_video(video_url, output_file_path)

            # Emit progress and status updates
            self.status_update.emit(f"Downloaded: {video_url}")
            self.total_progress_update.emit(100 * (self.urls.index(video_url) + 1) // len(self.urls))

        except Exception as e:
            self.logger.error(f"Failed to download video: {video_url} - {e}")
            self.failed_downloads.append((video_url, str(e)))