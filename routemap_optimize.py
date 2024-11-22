import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import requests
import math as python_math  # Using python-math
import random2  # Using random2

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
    # Initialize session state for tabs
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Home"

    # Navigation buttons
    def set_active_tab(tab_name):
        st.session_state.active_tab = tab_name

    # Tab rendering logic
    if st.session_state.active_tab == "Home":
        st.title("Welcome to the Route Optimization App")
        st.write("Navigate through the tabs to enter addresses, view maps, and tables.")
        if st.button("Go to Addresses Tab"):
            set_active_tab("Addresses")

    elif st.session_state.active_tab == "Addresses":
        st.title("Enter Addresses")
        default_addresses = [
            "1950 Old Alabama Rd, Roswell, GA, 30076",
            "6015 State Bridge rd, Duluth, GA, 30097",
            "3102 Hartford Mill Pl, Duluth, GA,30097",
            "928 Hawk Creek Trail, Lawrenceville, GA,30043",
            "1699 Centerville Dr, Buford, GA,30518",
            "1323 Terrasol ridge sw, lilburn, ga, 30047"
        ]
        addresses = [st.text_input(f"Address {i + 1}", value=default_addresses[i] if i < len(default_addresses) else "") for i in range(10)]
        if st.button("Optimize Route"):
            # Dummy success message
            st.success("Route optimized! Navigate to the Map or Route Table tabs.")

    elif st.session_state.active_tab == "Map":
        st.title("Map View")
        st.write("Display the map here.")
        if st.button("Go to Route Table"):
            set_active_tab("Route Table")

    elif st.session_state.active_tab == "Route Table":
        st.title("Route Table")
        st.write("Display the route table here.")

if __name__ == "__main__":
    main()
