import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import requests
import math as python_math  # Using python-math
import random2  # Using random2
import folium
from streamlit_folium import st_folium

# Function to compute distance matrix
@st.cache_data
def compute_distance_matrix(locations):
    num_locations = len(locations)
    distance_matrix = [[0] * num_locations for _ in range(num_locations)]
    for i in range(num_locations):
        for j in range(i, num_locations):
            distance = geodesic(locations[i], locations[j]).kilometers
            distance_matrix[i][j] = distance
            distance_matrix[j][i] = distance
    return distance_matrix

# Function to create a data model for TSP
def create_data_model(locations):
    return {
        'locations': locations,
        'num_locations': len(locations),
        'distance_matrix': compute_distance_matrix(locations),
    }

# Geocode addresses using Photon API
def geocode_address(address):
    url = f'https://photon.komoot.io/api/?q={address}'
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json()
        if results['features']:
            first_result = results['features'][0]
            latitude = first_result['geometry']['coordinates'][1]
            longitude = first_result['geometry']['coordinates'][0]
            return address, latitude, longitude
    return None

# TSP Solver using Simulated Annealing with fixed start and end points
def tsp_solver(data_model, iterations=1000, temperature=10000, cooling_rate=0.95):
    def distance(point1, point2):
        return python_math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    num_locations = data_model['num_locations']
    locations = data_model['locations']
    
    start_point = locations[0]
    end_point = locations[-1]
    intermediate_points = locations[1:-1]

    current_solution = list(range(len(intermediate_points)))
    random2.shuffle(current_solution)

    current_solution = [0] + [i + 1 for i in current_solution] + [num_locations - 1]

    current_distance = sum(
        distance(locations[current_solution[i - 1]], locations[current_solution[i]])
        for i in range(1, len(current_solution))
    )

    best_solution = current_solution[:]
    best_distance = current_distance

    for _ in range(iterations):
        temp = temperature * (cooling_rate ** _)
        new_solution = current_solution[:]
        i, j = random2.sample(range(1, num_locations - 1), 2)
        new_solution[i], new_solution[j] = new_solution[j], new_solution[i]

        new_distance = sum(
            distance(locations[new_solution[i - 1]], locations[new_solution[i]])
            for i in range(1, len(new_solution))
        )

        delta = new_distance - current_distance
        if delta < 0 or random2.random() < python_math.exp(-delta / temp):
            current_solution = new_solution[:]
            current_distance = new_distance

        if current_distance < best_distance:
            best_solution = current_solution[:]
            best_distance = current_distance

    return [locations[i] for i in best_solution]

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
        route_data.append((from_name, to_name, f"{distance * 0.621371:.2f} miles"))

    st.metric("Total Distance", f"{total_distance * 0.621371:.2f} miles")
    st.table(pd.DataFrame(route_data, columns=["From", "To", "Distance (miles)"]))

# Main Streamlit application
def main():
    st.title("Enhanced Route Optimization App")
    tab1, tab2, tab3, tab4 = st.tabs(["Home", "Addresses", "Map", "Route Table"])

    if "addresses" not in st.session_state:
        st.session_state["addresses"] = [
            "1950 Old Alabama Rd, Roswell, GA, 30076",
            "5720 Lilburn Stone Mountain Rd, Stone Mountain, GA 30087",
            "1489 Buford Hwy, Cumming, GA 30041",
            "330 Village Dr, Dawsonville, GA 30534",
            "350 Rock Eagle Rd, Eatonton, GA 31024",
            "", "", "", "", ""
        ]

    with tab1:
        st.header("Welcome to the Route Map Optimization App:sunglasses:")
        st.write(""" - # Home: Introduction and navigation instructions.
        - ##  Addresses: Enter the addresses you want to optimize the route with first address as starting and last address as ending point.Clear button clear default address in the search box.
        - ## Map: View the optimized route on the map.
        - ## Route Table: See the detailed route and distances between stops.
        -### Preview driving direction takes to Google Maps with input address.""")

    with tab2:
        st.header("Enter Addresses")

        addresses = [st.text_input(f"Address {i + 1}", value=st.session_state["addresses"][i]) for i in range(10)]

        if st.button("Clear"):
            st.session_state["addresses"] = [""] * 10

        if st.button("Optimize Route"):
            geocoded = [geocode_address(addr) for addr in addresses if addr.strip()]
            geocoded = [x for x in geocoded if x is not None]

            if len(geocoded) < 2:
                st.error("Please enter at least 2 valid addresses.")
                return

            locations = [(lat, lon) for _, lat, lon in geocoded]
            place_names = [name for name, _, _ in geocoded]
            loc_df = pd.DataFrame({'Place_Name': place_names, 'Coordinates': locations})

            data_model = create_data_model(locations)
            try:
                optimal_route = tsp_solver(data_model)

                st.session_state['optimal_route'] = optimal_route
                st.session_state['loc_df'] = loc_df
                st.experimental_set_query_params(tab="2")

            except Exception as e:
                st.error(f"An error occurred during route optimization: {e}")

    with tab3:
        st.header("Map View")
        if 'optimal_route' in st.session_state:
            optimal_route = st.session_state['optimal_route']
            loc_df = st.session_state['loc_df']

            # Create a Folium map centered at the first location
            map_center = optimal_route[0]
            map_view = folium.Map(location=map_center, zoom_start=10)

            # Add markers with custom red block icons for each location
            for index, location in enumerate(optimal_route):
                place_name = loc_df.loc[loc_df['Coordinates'] == location, 'Place_Name'].values[0]
                folium.Marker(
                    location=location,
                    popup=f"<b>Address:</b> {place_name}",
                    tooltip=f"Stop {index + 1}",
                    icon=folium.Icon(color="red", icon="stop", prefix="fa"),
                ).add_to(map_view)

            # Display the map
            st_data = st_folium(map_view, width=700, height=500)

            # Option to view directions in Google Maps
            gmaps_link = "https://www.google.com/maps/dir/" + "/".join(
                [f"{lat},{lon}" for lat, lon in optimal_route]
            )
            st.markdown(f"[Preview Driving Directions]({gmaps_link})")
        else:
            st.info("No route optimized yet.")

    with tab4:
        st.header("Route Table")
        if 'loc_df' in st.session_state and 'optimal_route' in st.session_state:
            loc_df = st.session_state['loc_df']
            optimal_route = st.session_state['optimal_route']
            display_route(optimal_route, loc_df)
        else:
            st.info("No route optimized yet.")

if __name__ == "__main__":
    main()
