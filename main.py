import math

import openrouteservice
from openrouteservice import convert
import matplotlib.pyplot as plt
import requests
from ast import literal_eval
import settings
from geopy.distance import geodesic
import geopy
from pprint import pprint


def get_path(start_lat, start_long, end_lat, end_long, get_raw=False):
    coords = ((start_long, start_lat), (end_long, end_lat))
    client = openrouteservice.Client(key=settings.openrouteservice_key)
    geometry = client.directions(coords)
    if not get_raw:
        decoded = convert.decode_polyline(
            geometry['routes'][0]['geometry'])  # decode encoded path to a list of coordinates
        x, y = [], []
        for i in decoded['coordinates']:
            x.append(i[0])
            y.append(i[1])
        return x, y
    return geometry


def reverse_geocode(lat, long):
    key = settings.geocoding_key
    url = f"https://geocode.maps.co/reverse?lat={lat}&lon={long}&api_key={key}"
    info = requests.get(url).text
    info = literal_eval(info)["display_name"]
    return info


def geocode(addr, get_lat_lon=True):
    key = settings.geocoding_key
    url = f"https://geocode.maps.co/search?q={addr}&api_key={key}"
    info = requests.get(url).text
    info = literal_eval(info)
    if get_lat_lon:
        return info[0]['lat'], info[0]['lon']
    return info


def find_nearby_parks(latitude, longitude, radius):
    response = requests.get("https://overpass-api.de/api/interpreter", params={
        'data': (
            f'[out:json];'
            f'node(around:{radius},{latitude},{longitude})["leisure"="park"];'
            f'out;'
        )})
    data = response.json()
    parks = []
    for node in data.get('elements',
                         []):  # In case there are no elements(when no parks are found), it will return an empty list.
        park_info = {
            'name': node.get('tags', {}).get('name', 'Unnamed Park'),
            'latitude': node.get('lat'),
            'longitude': node.get('lon')
        }
        parks.append(park_info)
    return parks


def get_weather(lat, long, start_time=None, end_time=None):
    response = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat,
        "longitude": long,
        "hourly": "precipitation,snowfall",
        "timezone": 'auto'
    })

    data = response.json()
    return data


def pretty_print_miles(distance, in_units='meters', round_to=.25):
    if in_units == 'meters':
        distance /= 1609.344
    if distance < round_to:
        return round(distance, 2)
    return distance - distance % round_to

def calculate_storms_along_path(path_geo, additional_time, point_density, max_snowfall, max_precip):
    path = convert.decode_polyline(path_geo)['coordinates']
    pprint(path)
    path_points = [path[0]]
    path_distances = [0]
    for i in path[1:]:
        distance = geopy.distance.geodesic(reversed(path_points[-1]), reversed(i)).miles
        if distance > point_density:
            path_points.append(i)
            path_distances.append(distance + path_distances[-1])

    path_weather = []
    invalid_weather = []

    # get weather
    for i in range(1, len(path_points)):
        expected_distance = path_distances[i]
        start = math.floor((expected_distance / pace) + (additional_time / 60))
        end = math.ceil((path_distances[i - 1] / pace) + (additional_time / 60))


        end += 1  # makes slicing inclusive of last value

        predicted_weather = get_weather(*reversed(path_points[i]))
        predicted_weather = [
            predicted_weather['hourly']['precipitation'][start:end + 1],
            predicted_weather['hourly']['snowfall'][start:end + 1],
        ]

        if any([j > max_precip for j in predicted_weather[0]]):
            invalid_weather.append(i)
        if any([j > max_snowfall for j in predicted_weather[0]]):
            invalid_weather.append(i)

    return invalid_weather

def get_directions(raw_path):
    route_steps = raw_path['routes'][0]['segments'][0]['steps'][:-1]
    prev_name = '-'
    steps = []
    # print all instructions for the routes
    for step in route_steps:
        step_name = step['name'] if step['name'] != '-' else prev_name
        step_distance = pretty_print_miles(step['distance'])
        if step['name'] != '-':
            prev_name = step['name']
        steps.append(f"On {step_name}, travel for {step_distance} miles, then {step['instruction']}.")


addr = input("What is your address?")
trip_rad = float(input("How far do you want to travel (in miles)?"))
pace = 0
while pace == 0:
    print("Which mode of transport will you be taking?")
    print("1. Walking")
    print("2. Jogging")
    print("3. Biking")
    mode = input("Type here: ")

    if mode == "1":
        pace = 3
    elif mode == "2":
        pace = 6
    elif mode == "3":
        pace = 10
    else:
        print("Please give an appropriate answer")

trip_rad *= 1609.344  # get in meters
coord_lat, coord_long = geocode(addr)
nearby_parks = find_nearby_parks(coord_lat, coord_long, trip_rad)
nearby_parks_shown = nearby_parks[:5]

all_paths = []
for park in nearby_parks_shown:
    path = get_path(coord_lat, coord_long, park['latitude'], park['longitude'], get_raw=True)['routes'][0]['geometry']
    print(calculate_storms_along_path(path, 0, 8, 10, 0.2))

if len(nearby_parks) == 0:
    print("No Parks Found")




