from os.path import join, dirname, isfile

import deezeridu
from json_database import JsonConfigXDG
from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_utils.log import LOG
from ovos_utils.parse import fuzzy_match
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    ocp_search


class DeezerSkill(OVOSCommonPlaybackSkill):
    def __init__(self):
        super(DeezerSkill, self).__init__("Deezer")
        self.supported_media = [MediaType.GENERIC,
                                MediaType.MUSIC]
        self.skill_icon = join(dirname(__file__), "ui", "deezer.png")
        self.api = deezeridu.API()
        self.credentials = JsonConfigXDG("deezer", subfolder="deezeridu")

    def get_intro_message(self):
        self.speak_dialog("intro")

    # common play
    @ocp_search()
    def search_deezer(self, phrase, media_type=MediaType.GENERIC):
        """Analyze phrase to see if it is a play-able phrase with this skill.

        Arguments:
            phrase (str): User phrase uttered after "Play", e.g. "some music"
            media_type (MediaType): requested CPSMatchType to media for

        Returns:
            search_results (list): list of dictionaries with result entries
            {
                "match_confidence": MatchConfidence.HIGH,
                "media_type":  CPSMatchType.MUSIC,
                "uri": "https://audioservice.or.gui.will.play.this",
                "playback": PlaybackType.VIDEO,
                "image": "http://optional.audioservice.jpg",
                "bg_image": "http://optional.audioservice.background.jpg"
            }
        """
        if not isfile(self.credentials.path):
            LOG.error(f"Deezer credentials are not set! please edit"
                      f" {self.credentials.path}")
            return []

        # match the request media_type
        base_score = 0
        if media_type == MediaType.MUSIC:
            base_score += 15

        explicit_request = False
        if self.voc_match(phrase, "deezer"):
            # explicitly requested deezer
            base_score += 50
            phrase = self.remove_voc(phrase, "deezer")
            explicit_request = True

        # score
        def calc_score(match, idx=0):
            # idx represents the order from deezer
            score = base_score - idx * 5  # - 5% as we go down the results list

            score += 100 * fuzzy_match(phrase.lower(), match["title"].lower())

            # small penalty to not return 100 and allow better disambiguation
            if media_type == MediaType.GENERIC:
                score -= 10

            if explicit_request:
                score += 30
            return min(100, score)

        try:
            idx = 0
            for t in self.api.search_track(phrase)["data"]:
                album = t.get("album") or {}
                pic = album.get('cover_xl') or album.get('cover_big') or \
                      album.get('cover_medium') or \
                      album.get('cover_small') or album.get('cover')
                if not pic:
                    artist = t.get("artist") or {}
                    pic = artist.get('picture_xl') or artist.get(
                        'picture_big') or \
                          artist.get('picture_medium') or \
                          artist.get('picture_small') or artist.get('picture')
                r = {
                    "title": t["title"],
                    "url": t["link"],
                    "image": pic or self.skill_icon,
                    "duration": t["duration"]
                }
                yield {
                    "match_confidence": calc_score(r, idx),
                    "media_type": MediaType.MUSIC,
                    "length": r.get("duration"),
                    "uri": "deezer//" + r["url"],
                    # NOTE: mycroft-gui fails to play deezer, so we need vlc
                    "playback": PlaybackType.AUDIO,
                    "image": r.get("image"),
                    "bg_image": r.get("image"),
                    "skill_icon": self.skill_icon,
                    "skill_logo": self.skill_icon,  # backwards compat
                    "title": r["title"],
                    "skill_id": self.skill_id
                }
                idx += 1

            # results = [t.track_info for t in self.api.search_track(phrase)]
        except Exception as e:
            self.log.error("Deezer search failed!")


def create_skill():
    return DeezerSkill()
