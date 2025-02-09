import requests
from bs4 import BeautifulSoup

def parse_file_name(video_name):
    new_name = get_movie_name_from_tvdb(video_name)

    return f"modificato_{new_name}"

def get_movie_name_from_tvdb(video_name):
    search_url = f"https://www.themoviedb.org/search?query={video_name.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(search_url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Trova il primo risultato nella sezione film
        movie_element = soup.select_one(".results .card .title a")

        if movie_element:
            return movie_element.text.strip()

    return None