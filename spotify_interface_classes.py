class Artist:

    def __init__(self, spotify_id, name, spotify_followers, spotify_popularity, genres):
        self.id = spotify_id
        self.name = name
        self.followers = spotify_followers
        self.popularity = spotify_popularity
        self.genres = genres

    def __repr__(self):
        return f"{self.name}"

    def __str__(self):
        return self.__repr__()


if __name__ == "__main__":

    pass
