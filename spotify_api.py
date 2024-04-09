import requests
import json
import base64
import logging


class GetSpotifyData:

    """
    Class that uses the Spotify Web API to retrieve information about an artist and their tracks
    """

    def __init__(self, client_id, client_secret):

        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = self.get_auth_header()

    def get_token(self):

        """
        Method to obtain an API access token
        """

        auth_string = self.client_id + ":" + self.client_secret
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')

        url = 'https://accounts.spotify.com/api/token'
        headers = {'Authorization': 'Basic ' + auth_base64,
                   'Content-Type': 'application/x-www-form-urlencoded'}

        data = {"grant_type": "client_credentials"}
        result = requests.post(url, headers=headers, data=data)
        json_result = json.loads(result.content)
        token = json_result["access_token"]

        return token

    def get_auth_header(self):

        token = self.get_token()
        return {'Authorization': 'Bearer ' + token}

    def get_artist_id(self, artist_name):

        """
        Method to retrieve an artist's Spotify ID

        :param artist_name: the name of an artist
        :return: the unique id of the artist
        """

        headers = self.headers
        endpoint = 'https://api.spotify.com/v1/search'
        query = f"?q={artist_name}&type=artist&limit=1"
        url = endpoint + query
        result = requests.get(url, headers=headers)
        json_result = json.loads(result.content)['artists']['items']

        if len(json_result) == 0:
            print("Could not find artist")
            return None

        return json_result[0]['id']

    def get_artist_info(self, artist_name):

        """
        Method that obtains high-level info & stats about an artist (# of followers, associated genres, etc.)

        :param artist_name: the name of an artist
        :return: json object containing info about the artist
        """

        headers = self.headers
        artist_id = self.get_artist_id(artist_name)
        endpoint = f"https://api.spotify.com/v1/artists/{artist_id}"

        try:
            result = requests.get(endpoint, headers=headers)
            result.raise_for_status()
            json_result = json.loads(result.content)
            return json_result
        except requests.exceptions.RequestException as err:
            logging.exception(f"API REQUEST: 'get_artist_info', ARTIST: {artist_name}, ERROR TYPE: see below\n\n {err}")

    def get_related_artists(self, artist_id, num_artists):

        """
        Method that grabs the data of an artist's related artists (acts whose music is often similar stylistically).
        One can also manually look up the names of these artists by navigating to the 'Fans Also Like' section of an
        individual artist's Spotify page.

        :param artist_id: the spotify ID of an artist
        :param num_artists: the number of related acts (can only return the data for a maximum of 20 related artists)
        :return: json object storing the related artists' data
        """

        headers = self.headers
        endpoint = f"https://api.spotify.com/v1/artists/{artist_id}/related-artists"
        result = requests.get(endpoint, headers=headers)
        json_result = json.loads(result.content)
        return json_result['artists'][:num_artists]

    def get_artist_albums(self, artist_id, offset=0, limit=50, groups="album"):

        """
        Method that returns Spotify album data for an individual artist

        :param artist_id: spotify ID of the artist
        :param offset: the index of the first item to return
        :param limit: the number of items (albums) to return (can return up to 50)
        :param groups: the type of album to return ('album', 'single', 'appears_on', or 'compilation')
        :return: json object containing data associated with each of the artist's albums
        """

        headers = self.headers
        endpoint = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
        market = "US"
        query = f"?include_groups={groups}&market={market}&limit={limit}&offset={offset}"
        url = endpoint + query

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json_response = response.json()
            return json_response
        except requests.exceptions.RequestException as err:
            logging.exception(f"API REQUEST: 'get_artist_albums', ARTIST ID: {artist_id}, ERR TYPE: see below..."
                              f"\n\n {err}")

    def get_album_tracks_data(self, album_ids, market="US"):

        """
        Method that returns track data from multiple albums

        :param album_ids: comma-separated list of albums' Spotify IDs (can provide up to 20 IDs)
        :param market: country code (default value is set to 'US')
        :return: json object containing individual track data for each of the provided albums
        """

        headers = self.headers
        endpoint = f"https://api.spotify.com/v1/albums"
        params = f"?ids={album_ids}&market={market}"
        url = endpoint + params

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json_response = response.json()
            return json_response
        except requests.exceptions.RequestException as err:
            logging.exception(f"API REQUEST: 'get_album_tracks_data', ERROR MESSAGE: see below\n\n {err}")

    def get_multiple_tracks_data(self, track_ids):

        """
        Method that retrieves additional information for 2+ tracks

        :param track_ids: comma-separated list of tracks' Spotify IDs
        :return: json object containing track data (this includes tracks' popularity scores)
        """

        headers = self.headers
        endpoint = f"https://api.spotify.com/v1/tracks"
        params = f"?ids={track_ids}"
        url = endpoint + params

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json_response = response.json()
            return json_response
        except requests.exceptions.RequestException as err:
            logging.exception(f"API REQUEST: 'get_multiple_tracks_data', ERROR MESSAGE: see below\n\n {err}")


if __name__ == "__main__":

    pass



