from spotify_api import GetSpotifyData
from spotify_interface_classes import Artist
import os
import logging
import numpy as np
import pandas as pd
import re
from datetime import datetime
from itertools import chain


class SpotifyArtistSummary(GetSpotifyData):

    """
    Class that builds upon the 'GetSpotifyData' class and contains its own set of methods that are intended to provide
    deeper insight into an artist's career and release history
    """

    def __init__(self):
        # access your client id & client secret to interact with the Spotify Web API
        super().__init__(os.getenv('client_id'), os.getenv('client_secret'))
        self.artists = []  # this will be filled if the 'build_related_artist_network' method is called

    def get_all_albums(self, artist_obj):

        """
        Method that retrieves every album released by an artist
        Calls the 'process_all_albums' helper method to do this

        :param artist_obj: instance of the 'Artist' class from the 'spotify_interface_classes' module
        :return: a list of the artist's albums (and their associated data)
        """

        off = 0
        lim = 50  # this is the max amount of albums you can grab at once
        alb_group_types = ["album", "single"]
        processed_albs = 0
        group_total_albs = []
        all_albs = []

        try:
            logging.info(f"Grabbing album data for {artist_obj.name}")
            res = self.process_all_albums(artist_obj.id, off, lim, alb_group_types, processed_albs, group_total_albs, all_albs)
            return res
        except Exception as err:
            logging.exception(f"Method: 'get_all_albums', Artist = {artist_obj.name}, Err Type: see below..."
                              f"\n\n{err}")

    def process_all_albums(self, artist_id, offset_val, limit_val, alb_groups, processed_albums, group_total_albums,
                           all_albums):

        """
        Method that retrieves the data for every album released by an artist. It does this by calling the parent class'
        'get_artist_albums' method and parsing its response. If an artist has > 50 albums, this method will call itself
        recursively to make another API request / grab the remaining album data.

        :param artist_id: spotify ID of the artist
        :param offset_val: the index of the first item (album) to return
        :param limit_val: the number of items to return (can return up to 50)
        :param alb_groups: list specifying the types of albums to return
        :param processed_albums: the total # of albums that have been processed so far
        :param group_total_albums: list that helps determine whether every album of each type has been processed (this
        is used to assess whether or not the base case has been reached)
        :param all_albums: list of the artist's albums (empty initially, is built up with each API request)
        :return: a complete list containing all of the artist's albums (and their associated metadata)
        """

        # make the initial API request
        groups_str = ",".join(alb_groups)
        batch_response = self.get_artist_albums(artist_id, offset=offset_val, limit=limit_val, groups=groups_str)

        batch_albums = batch_response["items"]
        batch_album_count = len(batch_albums)

        # grab the relevant info from the JSON response
        release_dates = [batch_albums[i]['release_date'] for i in range(batch_album_count)]
        album_tracks = [batch_albums[i]['total_tracks'] for i in range(batch_album_count)]
        album_types = [batch_albums[i]['album_type'] for i in range(batch_album_count)]
        album_groups = [batch_albums[i]['album_group'] for i in range(batch_album_count)]
        album_ids = [batch_albums[i]['id'] for i in range(batch_album_count)]
        artist_ids = [artist_id for i in range(batch_album_count)]

        album_data = list(zip(release_dates, album_tracks, album_types, album_groups, album_ids, artist_ids))

        # update input lists & counter
        all_albums.append(album_data)
        group_total_albums.append(batch_response['total'])
        processed_albums += batch_album_count

        # base case - check if every album of each type has been processed
        # if the two values below are NOT equivalent, then 1 of the 3 recursive conditions below will kick in and an
        # additional API request will be made to grab the remaining album data
        if processed_albums == group_total_albums[0]:
            all_albums_cleaned = [j for i in all_albums for j in i]
            return all_albums_cleaned

        # recursive condition 1
        if (batch_album_count == limit_val) and (album_groups[0] != album_groups[-1]):
            # find the index value where there's a change in the 'album_group' type
            same_val_counter = 0
            for i in range(len(album_groups) - 1, -1, -1):
                if album_groups[i] == album_groups[-1]:
                    same_val_counter += 1
                else:
                    break
            # update the arguments for the next API request
            offset_val += same_val_counter
            change_idx = (limit_val - 1) - (same_val_counter - 1)
            change_idx_val = album_groups[change_idx - 1]
            if change_idx_val == "album":
                alb_groups = ["single"]
            res = self.process_all_albums(artist_id, offset_val, limit_val, alb_groups, processed_albums, group_total_albums, all_albums)

        # recursive condition 2
        if (batch_album_count == limit_val) and (album_groups[0] == album_groups[-1]):
            offset_val += limit_val  # update the values for the next API request
            res = self.process_all_albums(artist_id, offset_val, limit_val, alb_groups, processed_albums, group_total_albums, all_albums)

        # recursive condition 3
        if (batch_album_count < limit_val) and (album_groups[0] == album_groups[-1]):
            alb_groups.pop(0)
            offset_val = 0  # update the values for the next API request
            res = self.process_all_albums(artist_id, offset_val, limit_val, alb_groups, processed_albums, group_total_albums, all_albums)

        return res

    def get_all_tracks(self, album_list):

        """
        Method that retrieves data for every track featured on an artist's albums
        Calls 'get_album_tracks' helper method defined below

         :param album_list: list of Spotify album IDs
         :return: list containing data for every track released by the artist
         """

        album_count = len(album_list)
        logging.info(f"Artist has {album_count} total albums/release events to process")

        i = 0  # use this to track total albums that have been processed
        j = i + 20  # can only process a maximum of 20 albums at once
        releases = []

        while i <= (album_count - 1):

            sub_list = album_list[i: j]  # grab the next 20 albums to be processed
            album_ids_lst = [x[4] for x in sub_list]
            album_ids_str = ",".join(album_ids_lst)  # string of album IDs needed for the API request
            tracks_artist_ids = [y for x in sub_list for y in (x[1] * (x[5] + " ")).split()]
            api_response = self.get_album_tracks(album_ids_str, tracks_artist_ids)  # returns a list of tuples

            for element in api_response:  # each element is an individual track
                releases.append(element)

            i = j
            j += 20

        logging.info(f"Finished collecting track data from the {album_count} albums")
        return releases

    def get_album_tracks(self, album_ids, artist_ids):

        """
        Method that returns track data for up to 20 albums
        Parses the response returned by the 'get_album_tracks_data' method

         :param album_ids: a string containing the Spotify album IDs
         :param artist_ids: list of artist IDs associated with each album
         :return: list containing track metadata
         """

        album_ids_lst = album_ids.split(",")
        track_data = self.get_album_tracks_data(album_ids)
        total_albums = len(track_data['albums'])

        track_titles = list(chain.from_iterable([[k['name'] for k in j['tracks']['items']] if j is not None else [np.nan] for j in track_data['albums']]))
        album_titles = [track_data['albums'][i]['name'] for i in range(total_albums) for j in range(len(track_data['albums'][i]['tracks']['items']))]
        artist_names = [",".join([k['name'] for k in track_data['albums'][i]['tracks']['items'][j]['artists']]) for i in range(total_albums)
                        for j in range(len(track_data['albums'][i]['tracks']['items']))]
        labels = [track_data['albums'][i]['label'] for i in range(total_albums) for j in range(len(track_data['albums'][i]['tracks']['items']))]
        album_pop_scores = [track_data['albums'][i]['popularity'] for i in range(total_albums) for j in range(len(track_data['albums'][i]['tracks']['items']))]
        track_secs = [round(sub_list['duration_ms'] * .001, 2) for i in range(total_albums) for sub_list in track_data['albums'][i]['tracks']['items']]
        track_positions = [sub_list['track_number'] for i in range(total_albums) for sub_list in track_data['albums'][i]['tracks']['items']]
        track_ids = [sub_list['id'] for i in range(total_albums) for sub_list in track_data['albums'][i]['tracks']['items']]
        album_ids = [album_ids_lst[i] for i in range(total_albums) for j in track_data['albums'][i]['tracks']['items']]
        all_performer_ids = [",".join([k['id'] for k in track_data['albums'][i]['tracks']['items'][j]['artists']])
                             for i in range(total_albums) for j in range(len(track_data['albums'][i]['tracks']['items']))]
        primary_artist_ids = [i for i in artist_ids]

        combined_track_data = list(zip(track_titles, album_titles, artist_names, labels, album_pop_scores, track_secs,
                                       track_positions, track_ids, album_ids, all_performer_ids, primary_artist_ids))
        return combined_track_data

    def get_track_pop_scores(self, id_list):

        """
        Method to get the Spotify popularity scores for a list of tracks
        Obtains the popularity scores by calling the 'get_multiple_tracks_data' method from the parent class

        :param id_list: list of Spotify track IDs
        :return: a list of the same size that contains the popularity scores for each of the provided tracks
        """

        total_ids = len(id_list)
        all_responses = []

        i = 0
        j = 50  # can only provide a maximum of 50 tracks per API request
        while i <= (total_ids - 1):
            sub_list = id_list[i: j]
            ids_str = ",".join(sub_list)
            json_result = self.get_multiple_tracks_data(ids_str)
            pop_scores = [json_result['tracks'][i]['popularity'] for i in range(len(json_result['tracks']))]

            for element in pop_scores:
                all_responses.append(element)

            i = j
            j += 50

        logging.info(f"Collected popularity scores for all {total_ids} tracks.")
        return all_responses

    def get_artist_discography(self, artist_name):

        """
        This calls several methods defined above to provide a complete picture of an artist's discography / career

        :param artist_name: the name of an artist
        :return: 2 dataframes (1 that summarizes an artist's activity & 1 that contains detailed information about every
        track the artist has ever released)
        """

        artist = self.get_artist_info(artist_name)
        artist_summary = Artist(artist['id'], artist['name'], artist['followers']['total'], artist['popularity'],
                                ", ".join(artist['genres']))

        # get album data for the artist
        albums = self.get_all_albums(artist_summary)
        album_df_cols = ["release_date", "album_tracks", "album_type", "album_group", "album_id", "artist_spot_id"]
        album_df = pd.DataFrame(albums, columns=album_df_cols)
        album_df.drop('artist_spot_id', axis=1, inplace=True)

        # get individual track data for the artist
        tracks = self.get_all_tracks(albums)
        tracks_cleaned = [i for i in tracks if i[-1] in i[-2]]
        tracks_df_cols = ["track_title", "album_title", "performer_names", "label", "album_pop", "track_secs",
                          "track_position", "track_id", "album_id", "all_performer_ids", "artist_spot_id"]
        tracks_df = pd.DataFrame(tracks_cleaned, columns=tracks_df_cols)

        # join the 2 dataframes together
        combined_track_data = pd.merge(album_df, tracks_df, on='album_id', how='inner')

        # get the Spotify popularity scores for each track
        combined_track_data['track_pop'] = self.get_track_pop_scores(list(combined_track_data['track_id']))

        # derive additional fields from the existing columns
        combined_track_data['release_date'] = pd.to_datetime(combined_track_data['release_date'], format="ISO8601")
        today = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
        combined_track_data['days_since_release'] = today - combined_track_data['release_date']
        combined_track_data['days_since_release'] = combined_track_data['days_since_release'].dt.days
        combined_track_data['release_event_num'] = combined_track_data.groupby('artist_spot_id')['release_date'].rank(
            method='dense')

        remix_search = lambda row: 1 if re.search(r'remix', row['track_title'], re.IGNORECASE) else 0
        collab_search = lambda row: 1 if len(row['performer_names'].split(",")) > 1 else 0
        combined_track_data['remix'] = combined_track_data.apply(remix_search, axis=1)
        combined_track_data['collab'] = combined_track_data.apply(collab_search, axis=1)

        # create df that summarizes the artist's release history
        agg_dict = {'release_date': ['min', 'max'],
                    'track_title': [('tracks_released', lambda x: len(set(x)))],
                    'release_event_num': [('total_release_events', lambda x: int(x.max()))],
                    'collab': 'sum',
                    'remix': 'sum',
                    'track_pop': [('most_recent', lambda x: list(x)[0]), 'max', 'mean']}
        artist_summary_df = combined_track_data.groupby(['artist_spot_id']).agg(agg_dict)
        artist_summary_df.columns = ["_".join(list(i)) for i in artist_summary_df.columns]
        artist_summary_df = artist_summary_df.rename(columns={'track_title_tracks_released': 'total_original_releases',
                                        'release_event_num_total_release_events': 'total_release_events',
                                        'collab_sum': 'total_collabs',
                                        'remix_sum': 'total_remixes',
                                        'track_pop_most_recent': 'track_pop_last_release'})
        artist_summary_df['release_window'] = artist_summary_df[('release_date_max')] - artist_summary_df[('release_date_min')]
        artist_summary_df['days_since_last_release'] = artist_summary_df[['release_date_max']].apply(lambda x: today - x, axis=1)
        artist_summary_df['days_since_last_release'] = artist_summary_df['days_since_last_release'].dt.days.astype(int)
        artist_summary_df['active'] = artist_summary_df['days_since_last_release'].apply(lambda x: 'yes' if x <= 730 else 'no')
        artist_summary_df['most_pop_release_event'] = int(
            combined_track_data[combined_track_data['track_pop'] == combined_track_data['track_pop'].max()][
                'release_event_num'].values[0])
        artist_summary_df['total_release_events'] = artist_summary_df['total_release_events'].astype(str)
        artist_summary_df['track_pop_mean'] = round(artist_summary_df['track_pop_mean'], 2)
        artist_summary_df['release_window'] = pd.to_timedelta(artist_summary_df['release_window']).dt.days
        artist_summary_df['years_releasing'] = round(artist_summary_df['release_window'] / 365, 2)

        # complete any remaining data preprocessing and select the columns of interest
        combined_track_data['release_date'] = combined_track_data['release_date'].dt.date

        artist_summary_df['artist_name'] = artist_summary.name
        artist_summary_df['spotify_followers'] = artist_summary.followers
        artist_summary_df['spotify_popularity'] = artist_summary.popularity
        artist_summary_cols = ["artist_name", "active", "years_releasing", "days_since_last_release",
                               "spotify_followers", "spotify_popularity", "most_pop_release_event",
                               "total_release_events", "total_original_releases", "track_pop_max", "track_pop_mean",
                               "total_collabs", "total_remixes"]
        artist_summary_df = artist_summary_df[artist_summary_cols]
        artist_summary_df.reset_index(drop=True, inplace=True)

        return artist_summary_df, combined_track_data

    def build_related_artist_network(self, seed_act="The Japanese House", total_acts=100, related_act_count=20):

        """
        This method builds a network of related / similar-sounding artists. It first does this by taking in an initial
        artist (the 'seed_act') and grabbing Spotify data associated with that artists' related acts. The method
        continues to grow the network by then retrieving the related artist data for each of the seed act's related
        artists. This process repeats until the size of the network is equal to the value provided in the 'total_acts'
        param. The 'process_related_acts' method below is called to help accomplish all of this.

        :param seed_act: the name of the input artist
        :param total_acts: the size of the artist network you'd like to build
        :param related_act_count: the number of related acts (can only return the data for a max of 20 related artists)

        """

        seed_act_data = self.get_artist_info(seed_act)
        seed_act_obj = Artist(seed_act_data['id'], seed_act_data['name'], seed_act_data['followers']['total'],
                              seed_act_data['popularity'], ", ".join(seed_act_data['genres']))

        artist_idx = 0
        acts_added = 0
        processed_artists = set()

        self.artists.append(seed_act_obj)  # add seed act to the class variable / list 'artists'
        processed_artists.add(seed_act_obj.id)
        acts_added += 1

        while len(self.artists) < total_acts:

            current_act = self.artists[artist_idx]
            current_act_id = current_act.id  # this will initially return the ID of the 'seed_act'
            # grab the related acts associated with the current artist
            related_acts = self.process_related_acts(current_act_id, related_act_count)  # returns a list

            for act in related_acts:
                if acts_added == total_acts:
                    break  # stop building the network
                else:
                    if act.id not in processed_artists:  # if new, add the related act to the 'artists' list
                        self.artists.append(act)
                        processed_artists.add(act.id)
                        acts_added += 1

            artist_idx += 1  # update counter to grab the related acts for the next artist in the 'artists' list

        logging.info(f"Comparing {seed_act}'s metrics to those of {total_acts} similar artists ")

    def process_related_acts(self, artist_id, related_act_count):

        """
        Method that calls the 'get_related_artists' method from the parent class and grabs the relevant information from
        its response

        :param artist_id: an artist's Spotify ID
        :param related_act_count: the number of related acts (can only return the data for a max of 20 related artists)
        :return: a list of 'Artist' objects (see 'spotify_interface_classes.py' for more info on the 'Artist' class)
        """

        related_acts = self.get_related_artists(artist_id, related_act_count)
        related_acts_cleaned = []

        for i in range(len(related_acts)):
            act_id = related_acts[i]['id']
            name = related_acts[i]['name']
            followers = related_acts[i]['followers']['total']
            popularity = related_acts[i]['popularity']
            genres = ", ".join(related_acts[i]['genres'])

            act_obj = Artist(act_id, name, followers, popularity, genres)
            related_acts_cleaned.append(act_obj)

        return related_acts_cleaned


if __name__ == "__main__":

    pass




