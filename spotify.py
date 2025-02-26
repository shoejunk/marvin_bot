import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class SpotifyClient:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope='playlist-read-private playlist-read-collaborative user-library-read user-read-playback-state user-modify-playback-state'
        ))

    def _get_active_device(self):
        devices = self.sp.devices()
        if devices and devices.get('devices') and len(devices['devices']) > 0:
            return devices['devices'][0]['id']
        return None

    def _ensure_active_device(self):
        device_id = self._get_active_device()
        if device_id:
            self.sp.transfer_playback(device_id, force_play=True)
        return device_id

    def play_track(self, track_name):
        device_id = self._ensure_active_device()
        if not device_id:
            return False

        # Clean up track name by replacing underscores with spaces
        clean_track_name = track_name.replace('_', ' ')
        results = self.sp.search(q=clean_track_name, limit=1, type='track')
        if results.get('tracks') and results['tracks'].get('items') and len(results['tracks']['items']) > 0:
            track_uri = results['tracks']['items'][0]['uri']
            self.sp.start_playback(device_id=device_id, uris=[track_uri])
            return True
        return False

    def play_playlist(self, playlist_name):
        try:
            device_id = self._ensure_active_device()
            if not device_id:
                logging.warning("No active device found")
                return False

            # Clean up playlist name by replacing underscores with spaces
            clean_playlist_name = playlist_name.replace('_', ' ')
            logging.info("Looking for playlist: '%s'", clean_playlist_name)

            # Search with increased limit
            offset = 0
            limit = 50
            while True:
                playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
                logging.info("Found %d playlists in your library (showing %d to %d)", playlists['total'], offset + 1, offset + len(playlists['items']))

                for playlist in playlists['items']:
                    logging.info("- %s (ID: %s)", playlist['name'], playlist['id'])
                    if playlist['name'].lower() == clean_playlist_name.lower():
                        logging.info("Found matching playlist: %s", playlist['name'])
                        self.sp.start_playback(device_id=device_id, context_uri=playlist['uri'])
                        return True

                if len(playlists['items']) < limit:
                    break

            logging.info("No playlist named '%s' found in your library", playlist_name)
            return False
        except spotipy.exceptions.SpotifyException as e:
            logging.error("Spotify API error: %s", str(e))
            return False
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            return False
            
    def pause_music(self):
        """Pause currently playing music"""
        try:
            device_id = self._get_active_device()
            if not device_id:
                logging.warning("No active device found")
                return False
                
            self.sp.pause_playback(device_id=device_id)
            logging.info("Music paused")
            return True
        except spotipy.exceptions.SpotifyException as e:
            logging.error("Spotify API error: %s", str(e))
            return False
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            return False
            
    def unpause_music(self):
        """Resume playing paused music"""
        try:
            device_id = self._get_active_device()
            if not device_id:
                logging.warning("No active device found")
                return False
                
            self.sp.start_playback(device_id=device_id)
            logging.info("Music resumed")
            return True
        except spotipy.exceptions.SpotifyException as e:
            logging.error("Spotify API error: %s", str(e))
            return False
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            return False
            
    def volume_up(self, increment=10):
        """Increase volume by the specified percentage"""
        try:
            device_id = self._get_active_device()
            if not device_id:
                logging.warning("No active device found")
                return False
                
            # Get current playback state to check volume
            current_playback = self.sp.current_playback()
            if not current_playback or 'device' not in current_playback:
                logging.warning("No active playback found")
                return False
                
            current_volume = current_playback['device']['volume_percent']
            new_volume = min(100, current_volume + increment)
            
            self.sp.volume(new_volume, device_id=device_id)
            logging.info(f"Volume increased from {current_volume}% to {new_volume}%")
            return True
        except spotipy.exceptions.SpotifyException as e:
            logging.error("Spotify API error: %s", str(e))
            return False
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            return False
            
    def volume_down(self, decrement=10):
        """Decrease volume by the specified percentage"""
        try:
            device_id = self._get_active_device()
            if not device_id:
                logging.warning("No active device found")
                return False
                
            # Get current playback state to check volume
            current_playback = self.sp.current_playback()
            if not current_playback or 'device' not in current_playback:
                logging.warning("No active playback found")
                return False
                
            current_volume = current_playback['device']['volume_percent']
            new_volume = max(0, current_volume - decrement)
            
            self.sp.volume(new_volume, device_id=device_id)
            logging.info(f"Volume decreased from {current_volume}% to {new_volume}%")
            return True
        except spotipy.exceptions.SpotifyException as e:
            logging.error("Spotify API error: %s", str(e))
            return False
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            return False