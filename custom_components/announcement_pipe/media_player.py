"""Client for Remote Alsamixer."""
import logging
from .announcement_pipe import AnnouncementPipe

import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_VOLUME_SET,
)

from homeassistant.components.media_player.const import SUPPORT_VOLUME_SET
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, STATE_IDLE, STATE_PLAYING
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_PIPE = "pipe"
CONF_VOLUME = "volume"

DOMAIN = "announcement_pipe"

SUPPORT_ANNOUNCEMENT_PIPE = (
    SUPPORT_VOLUME_SET
    | SUPPORT_PLAY_MEDIA
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PIPE): cv.string,
        vol.Optional(CONF_VOLUME): cv.small_float
        # vol.Required(CONF_HOSTS): [{
        #     vol.Required('ip'): cv.string,
        #     vol.Optional('port'): cv.port,
        #     vol.Required("alias"): cv.string
        # }]
    }
)



def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Announcement Pipe platform."""
    pipe = config.get(CONF_PIPE)
    add_entities([AnnouncementPipeEntity(hass, pipe)])


class AnnouncementPipeEntity(MediaPlayerEntity):
    """Representation of an AnnouncementPipe entity."""

    def __init__(self, hass, output_pipe):
        """Initialize the AnnouncementPipe entity."""
        self._volume = 0.5
        self._hass = hass
        self._name = "Announcement Pipe"
        self._state = STATE_IDLE
        self._pipe = AnnouncementPipe(self._volume * 2, output_pipe, self.__state_callback, self.__prepare, self.__restore)
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, self.__shutdown)

    def __state_callback(self, playing):
        self._state = STATE_PLAYING if playing else STATE_IDLE
        self.schedule_update_ha_state()

    def __prepare(self, done):
        self._hass.bus.listen_once("prepared_for_announcement", lambda event: done.set())
        self._hass.bus.fire("prepare_for_announcement", {})

    def __restore(self, done):
        self._hass.bus.listen_once("restored_after_announcement", lambda event: done.set())
        self._hass.bus.fire("restore_after_announcement", {})

    def __shutdown(self):
        self._pipe.close()

    def set_volume_level(self, volume):
        """Set the volume level."""
        self._volume = volume
        self._pipe.set_volume(volume * 2)
        self.schedule_update_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """Return the name of the control."""
        return self._name

    @property
    def volume_level(self):
        """Return the volume level."""
        return self._volume

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_ANNOUNCEMENT_PIPE

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    def play_media(self, media_type, media_id, **kwargs):
        """Play media."""

        if media_type != MEDIA_TYPE_MUSIC:
            _LOGGER.error("invalid media type")
            return
        self._pipe.make_announcement(media_id)
