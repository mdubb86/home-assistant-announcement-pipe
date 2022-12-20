import queue
import subprocess
import threading
import logging

from time import sleep

_LOGGER = logging.getLogger(__name__)

class AnnouncementPipe:

    def __init__(self, filter_volume, output_pipe, state_callback, prepare, restore):
        self.output_pipe = output_pipe
        self.filter_volume = filter_volume
        self.announce_queue = queue.SimpleQueue()
        self.state_callback = state_callback
        self.prepare = prepare
        self.prep_queue = queue.SimpleQueue()
        self.restore = restore
        self.restore_event = threading.Event()
        self.thread = threading.Thread(target=self.__run)
        self.thread.start()

    def __run(self):
        _LOGGER.info("Starting announcement pipe thread")
        while True:

            # Block until an announcement is queued
            url = self.announce_queue.get()

            if url is False:
                break

            # Invoke state callback
            self.state_callback(True)

            # Prepare for announcement(s)
            _LOGGER.debug("Requesting preparation")
            self.restore_event.clear()
            self.prepare(self.prep_queue)
            prep_data = self.prep_queue.get()
            _LOGGER.info("Preparation complete: %s", str(prep_data))

            # Play announcement
            self.__play(url)

            # Continue to play any queued announcements
            while True:
                try:
                    url = self.announce_queue.get_nowait()
                    self.__play(url)
                except queue.Empty:
                    break

            # Sleep 1 to clear buffer
            sleep(1)

            # Restore after announcement(s)
            _LOGGER.debug("Requesting restore")
            self.restore_event.clear()
            self.restore(prep_data, self.restore_event)
            self.restore_event.wait()
            _LOGGER.debug("Restore complete")

            # Invoke state update
            self.state_callback(False)

        _LOGGER.info("Exited announcement pipe thread")

    def __play(self, url):
        _LOGGER.info("Playing announcement %s", url)
        res = subprocess.run(['ffmpeg', '-y', '-re', '-i', url, '-f', 'u16le', '-acodec', 'pcm_s16le', '-ac',
                             '2', '-ar', '48000', '-filter:a', 'volume=' + str(self.filter_volume), self.output_pipe],
                             capture_output=True, text=True)
        _LOGGER.debug('FFmpeg output: %s', res.stderr)

    def make_announcement(self, url):
        _LOGGER.debug("Adding %s to announcement queue", url)
        self.announce_queue.put(url)

    def set_volume(self, filter_volume):
        self.filter_volume = filter_volume

    def close(self):
        self.announce_queue.put(False)
