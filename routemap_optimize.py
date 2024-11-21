import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import requests
import math as python_math
import random2
import plotly.express as px

# OSRM Configuration
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"

# Function to get coordinates
def get_coordinates(address):
    geolocator = Nominatim(user_agent="route_finder")
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    else:
        st.error(f"Could not geocode address: {address}")
        return None

# Function to get travel distance between coordinates using OSRM
def get_travel_distance(coord1, coord2):
    coord_string = f"{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}"
    response = requests.get(f"{OSRM_BASE_URL}/{coord_string}?overview=false")
    if response.status_code == 200:
        data = response.json()
        return data['routes'][0]['distance']
    else:
        st.error(f"Error fetching travel distance data from OSRM. Status code: {response.status_code}")
        return float('inf')

# Function to create distance matrix
def create_distance_matrix(coords):
    distance_matrix = np.zeros((len(coords), len(coords)))
    for i, coord1 in enumerate(coords):
        for j, coord2 in enumerate(coords):
            distance_matrix[i][j] = get_travel_distance(coord1, coord2)
    return distance_matrix

# Function to get route coordinates using OSRM
def get_route_coordinates(coords):
    coord_string = ";".join([f"{lon},{lat}" for lat, lon in coords])
    response = requests.get(f"{OSRM_BASE_URL}/{coord_string}?overview=full&geometries=geojson")
    if response.status_code == 200:
        data = response.json()
        return data['routes'][0]['geometry']['coordinates']
    else:
        st.error(f"Error fetching route data from OSRM. Status code: {response.status_code}")
        return []

# Function to optimize route using geneticalgorithm
def tsp_solver(data_model, iterations=1000, temperature=10000, cooling_rate=0.95):
    def distance(point1, point2):
        return python_math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    num_locations = data_model['num_locations']
    locations = data_model['locations']

    # Generate initial random solution
    current_solution = list(range(num_locations))
    random2.shuffle(current_solution)

    # Calculate initial solution's distance
    current_distance = sum(
        distance(locations[current_solution[i - 1]], locations[current_solution[i]])
        for i in range(num_locations)
    )

    best_solution = current_solution[:]
    best_distance = current_distance

    # Simulated Annealing
    for _ in range(iterations):
        temp = temperature * (cooling_rate ** _)
        new_solution = current_solution[:]
        i, j = random2.sample(range(num_locations), 2)
        new_solution[i], new_solution[j] = new_solution[j], new_solution[i]

        new_distance = sum(
            distance(locations[new_solution[i - 1]], locations[new_solution[i]])
            for i in range(num_locations)
        )

        delta = new_distance - current_distance
        if delta < 0 or random2.random() < python_math.exp(-delta / temp):
            current_solution = new_solution[:]
            current_distance = new_distance

        if current_distance < best_distance:
            best_solution = current_solution[:]
            best_distance = current_distance

    return [locations[i] for i in best_solution] + [locations[best_solution[0]]]

# Display route and distances
def display_route(route, loc_df):
    route_data = []
    total_distance = 0

    for i in range(len(route) - 1):
        loc1, loc2 = route[i], route[i + 1]
        distance = geodesic(loc1, loc2).kilometers
        total_distance += distance

        from_name = loc_df.loc[loc_df['Coordinates'] == loc1, 'Place_Name'].values[0]
        to_name = loc_df.loc[loc_df['Coordinates'] == loc2, 'Place_Name'].values[0]
        route_data.append((from_name, to_name, f"{distance:.2f} km", f"{distance * 0.621371:.2f} mi"))

    st.metric("Total Distance", f"{total_distance * 0.621371:.2f} miles")
    st.table(pd.DataFrame(route_data, columns=["From", "To", "Distance (km)", "Distance (mi)"]))

# Display map with route
def display_map(route, locations):
    route_coords = get_route_coordinates(route)
    route_coords = [(lat, lon) for lon, lat in route_coords]  # swap order for Plotly

    route_df = pd.DataFrame(route_coords, columns=["lat", "lon"])
    route_df["sequence"] = range(1, len(route_coords) + 1)
    marker_df = pd.DataFrame(locations, columns=["lat", "lon"])
    marker_df["address"] = [f"Address {i+1}" for i in range(len(locations))]

    fig = px.scatter_mapbox(
        marker_df,
        lat="lat",
        lon="lon",
        hover_name="address",
        zoom=12,
        mapbox_style="carto-positron",
    )

    fig.add_scattermapbox(
        lat=route_df["lat"],
        lon=route_df["lon"],
        mode="lines",
        line=dict(width=4, color="blue"),
        name="Route",
    )

    fig.add_scattermapbox(
        lat=route_df["lat"],
        lon=route_df["lon"],
        mode="markers+text",
        text=route_df["sequence"],
        textposition="top right",
        marker=dict(size=8, color="red"),
        name="Route Points",
    )

    st.plotly_chart(fig, use_container_width=True)

# Main Streamlit application
def main():
    st.title("Route Optimization with Interactive Map")

    tab1, tab2 = st.tabs(["Map", "Address Search"])

    with tab1:
        st.subheader("Optimized Route")
        st.write("This tab will display the optimized route on the map.")

    with tab2:
        st.subheader("Enter up to 10 addresses:")
        addresses = [st.text_input(f"Address {i + 1}") for i in range(10)]

    if st.button("Optimize Route"):
        with tab1:
            st.subheader("Optimized Route")

        # Geocode the addresses
        geocoded = [geocode_address(addr) for addr in addresses if addr.strip()]
        geocoded = [x for x in geocoded if x is not None]  # Remove failed geocodes

        if len(geocoded) < 2:
            st.error("Please enter at least 2 valid addresses.")
            return

        # Extract coordinates and place names
        locations = [(lat, lon) for _, lat, lon in geocoded]
        place_names = [name for name, _, _ in geocoded]
        loc_df = pd.DataFrame({'Place_Name': place_names, 'Coordinates': locations})

        try:
            # Solve TSP for route optimization
            data_model = create_data_model(locations)
            optimal_route = tsp_solver(data_model)

            with tab1:
                display_map(optimal_route, locations)
                display_route(optimal_route, loc_df)

            with tab2:
                st.subheader("Optimized Route Table")
                display_route(optimal_route, loc_df)

            # Generate Google Maps link
            gmaps_link = "https://www.google.com/maps/dir/" + "/".join(
                [f"{lat},{lon}" for lat, lon in optimal_route]
            )
            st.markdown(f"[Open Optimized Route in Google Maps]({gmaps_link})")
        except Exception as e:
            st.error(f"An error occurred during route optimization
