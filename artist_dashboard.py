from analyze_artist import SpotifyArtistSummary
from dotenv import load_dotenv
import logging
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px


def log_configuration():

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - %(module)s - line # %(lineno)d")

    fh = logging.FileHandler('artist_dashboard.log', 'w')  # record what the program is doing in a separate log file
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


load_dotenv()

log_configuration()

app = dash.Dash(__name__)

# define the layout of the Dash web app / artist dashboard
app.layout = html.Div([
    html.H3('SEARCH ARTIST', style={'fontFamily': 'Arial'}),
    dcc.Input(id='input-artist',
              type='text',
              placeholder='Enter name of artist...',
              value="The Japanese House",
              debounce=True),
    html.Br(),
    html.H3('ARTIST OVERVIEW', style={'fontFamily': 'Arial'}),
    html.Div(id='track-data', style={'display': 'none'}),
    html.Div(id='artist-summary-table'),
    html.H5('Compare metrics to similar artists (select # of artists below)', style={'fontFamily': 'Arial'}),
    dcc.Dropdown(id='dropdown',
                 options=[{'label': str(i), 'value': i} for i in range(100, 301, 100)],
                 value=100,
                 style={'width': '35%'}),
    html.Br(),
    html.Div(id='rankings-table'),
    html.Br(),
    html.H3("RELEASE HISTORY OVERVIEW", style={'fontFamily': 'Arial'}),
    html.Div([html.H4('Distribution of track popularity scores', style={'float': 'left', 'fontFamily': 'Arial'}),
              html.H4('Record label partners', style={'flex': '1', 'text-align': 'center', 'fontFamily': 'Arial'})],
             style={'width': '100%', 'display': 'inline-block'}),
    html.Div([dcc.Graph(id='histogram', style={'width': '40%', 'display': 'inline-block'}),
              dcc.Graph(id='bar-chart-2', style={'width': '60%', 'display': 'inline-block'})]),
    html.H4('Total releases per year', style={'fontFamily': 'Arial'}),
    dcc.Graph(id='bar-chart'),
    html.H4('Track popularity scores (grouped by year)', style={'fontFamily': 'Arial'}),
    dcc.Graph(id='box-whisker'),
    html.H4("Artist's release timeline", style={'fontFamily': 'Arial'}),
    html.P("The plot below displays the point in their career that the artist released each one of their albums, EP, "
           "and singles. A line chart is included to highlight the most popular track from each release event."),
    dcc.Graph(id='scatter-plot'),
    html.H4("Artist's discography", style={'fontFamily': 'Arial'}),
    html.Div(id='release-history-table'),
    dcc.Interval(id='interval', interval=300000, n_intervals=0)
])


@app.callback(
    [Output('track-data', 'children'),
     Output('artist-summary-table', 'children'),
     Output('release-history-table', 'children')],
    [Input('input-artist', 'value'),
     Input('interval', 'n_intervals')]
)
def get_artist_data(input_artist, n_intervals):

    """
    Callback function that retrieves an artist's Spotify track data and summarizes the act's career / release history

    :param input_artist: the name of an artist of interest
    :param n_intervals: number of intervals that have passed (helps refresh the dashboard every 5 minutes)
    :return: several datatables containing the selected artist's information
    """

    # create instance of the 'SpotifyArtistSummary' class to get the selected artist's Spotify data
    artist_summary = SpotifyArtistSummary()
    artist_data, track_data = artist_summary.get_artist_discography(input_artist)

    # store the artist's information in 2 Dash DataTables
    artist_table = dash_table.DataTable(artist_data.to_dict('records'),
                                        [{"name": i, "id": i} for i in artist_data.columns],
                                        style_table={'width': '700px'})

    track_table_cols = ["track_title", "album_title", "performer_names", "label", "release_date", "track_pop",
                        "track_position", "album_tracks", "remix", "collab", "release_event_num"]
    track_table = dash_table.DataTable(track_data[track_table_cols].to_dict('records'),
                                       [{"name": i, "id": i} for i in track_table_cols],
                                       sort_action='native',
                                       sort_mode='multi',
                                       style_table={'width': '700px'})

    return track_data.to_json(), artist_table, track_table


@app.callback(
    Output('rankings-table', 'children'),
    [Input('input-artist', 'value'),
     Input('dropdown', 'value')]
)
def compare_2_peers(input_artist, artist_network_size):

    """
    This callback function compares the selected artist's metrics to those of similar artists

    :param input_artist: the name of an artist
    :param artist_network_size: the number of acts you'd like to compare the artist to
    :return: Dash DataTable that displays how an act's follower count & popularity score stacks up against its peers
    """

    summary = SpotifyArtistSummary()
    summary.build_related_artist_network(seed_act=input_artist,
                                         total_acts=artist_network_size,
                                         related_act_count=20)

    follower_values = [i.followers for i in summary.artists]
    popularity_scores = [i.popularity for i in summary.artists]
    follower_ranking = sum(1 for val in follower_values if val >= follower_values[0])
    pop_ranking = sum(1 for val in popularity_scores if val >= popularity_scores[0])

    data = [{'spot_followers_ranking': f"{follower_ranking}/{artist_network_size}",
             'spot_popularity_ranking': f" {pop_ranking}/{artist_network_size}"}]
    columns = [{'name': col, 'id': col} for col in data[0].keys()]
    comp_table = dash_table.DataTable(data=data,columns=columns, style_table={'width': '300px'})

    return comp_table


@app.callback(
    [Output('scatter-plot', 'figure'),
     Output('histogram', 'figure'),
     Output('bar-chart', 'figure'),
     Output('box-whisker', 'figure'),
     Output('bar-chart-2', 'figure')],
    Input('track-data', 'children')
)
def fill_plots(artist_track_data):

    """
    This callback function generates and updates the dashboard's plots

    :param artist_track_data: the 1st data table returned by the 'get_artist_data' callback function above
    :return: 5 updated plots for the artist of interest
    """

    # first complete any remaining data preprocessing
    plots_df = pd.read_json(artist_track_data)
    plots_df['release_date'] = pd.to_datetime(plots_df['release_date'], unit='ms')
    plots_df.sort_values(by='release_date', ascending=True, inplace=True)

    plots_df['days_since_last_release'] = plots_df.groupby('artist_spot_id')['release_date'].diff().fillna(pd.Timedelta(seconds=0)).dt.days
    plots_df['days_since_1st_release'] = plots_df.groupby('artist_spot_id')['days_since_last_release'].cumsum()
    plots_df['release_year'] = plots_df['release_date'].dt.year

    # plot 1
    scatter = px.scatter(plots_df,
                         x='days_since_1st_release',
                         y='track_pop',
                         hover_data=['track_title', 'album_title', 'release_date', 'label'],
                         color_discrete_sequence=['#36454F'])
    max_pop_per_release = plots_df.groupby('days_since_1st_release')['track_pop'].max()
    line_plot = px.line(max_pop_per_release,
                        x=max_pop_per_release.index,
                        y='track_pop',
                        color_discrete_sequence=['#008000'])
    line_plot.update_traces(line=dict(dash="dot", width=3, color="green"))
    for data in line_plot.data:
        scatter.add_trace(data)
    scatter.update_xaxes(title_text="Days into the artist's career")
    scatter.update_yaxes(title_text="Spotify track popularity")

    # plot 2
    hist = px.histogram(plots_df,
                        x='track_pop',
                        nbins=30,
                        opacity=.5)
    hist.update_xaxes(title_text="Spotify track popularity")
    hist.update_yaxes(title_text="Track count")
    hist.update_traces(marker=dict(color='#008000', line=dict(color='black', width=1)))

    # plot 3
    bar_data = plots_df.groupby('release_year')['track_title'].count().reset_index()
    bar_data.rename(columns={"track_title": "tracks_released"}, inplace=True)
    bar = px.bar(bar_data, x='release_year', y='tracks_released', color_discrete_sequence=['#36454F'], opacity=.8)
    bar.update_xaxes(title_text="Release year")
    bar.update_yaxes(title_text="Tracks released")

    # plot 4
    box_plot = px.box(plots_df, x='release_year', y='track_pop', color_discrete_sequence=['#008000'])
    box_plot.update_xaxes(title_text="Release year")
    box_plot.update_yaxes(title_text="Spotify track popularity")

    # plot 5
    bar2_data = plots_df.groupby('label')['track_title'].count().reset_index()
    bar2_data.rename(columns={"track_title": "total_releases"}, inplace=True)
    bar2_data.sort_values(by='total_releases', ascending=True, inplace=True)
    bar2 = px.bar(bar2_data,
                  x='total_releases',
                  y='label',
                  orientation='h',
                  color_discrete_sequence=['#36454F'],
                  opacity=.8)
    bar2.update_xaxes(title_text='total releases')
    bar2.update_yaxes(title_text='label')

    return scatter, hist, bar, box_plot, bar2


if __name__ == '__main__':

    app.run_server(debug=True)
