"""Client for Remote Alsamixer."""
import logging
from .announcement_pipe import AnnouncementPipe

import voluptuous as vol

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaType,
)
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, STATE_IDLE, STATE_PLAYING
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.network import get_url

_LOGGER = logging.getLogger(__name__)

CONF_PIPE = "pipe"
CONF_VOLUME = "volume"

DOMAIN = "announcement_pipe"

SUPPORT_ANNOUNCEMENT_PIPE = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.PLAY_MEDIA
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

    def __prepare(self, queue):
        self._hass.bus.listen_once("announcement.prepared", lambda event: queue.put(event.as_dict()['data']))
        self._hass.bus.fire("announcement.prepare", {})

    def __restore(self, prep_data, done):
        self._hass.bus.listen_once("announcement.restored", lambda event: done.set())
        self._hass.bus.fire("announcement.restore", prep_data)

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

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play media."""

        _LOGGER.info('Playing media %s ', media_id)

        if media_type != MediaType.MUSIC:
            _LOGGER.error('media type %s is not supported', media_type)
            return

        if media_source.is_media_source_id(media_id):
            resolved_media = await media_source.async_resolve_media(self._hass, media_id, self.entity_id)
            url = get_url(self._hass) + resolved_media.url
            _LOGGER.info('Announcement media resolved %s -> %s', media_id, url)
            self._pipe.make_announcement(url)
        else:
            _LOGGER.info('Not a media source %s', media_id)
