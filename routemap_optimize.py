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
    
    # Fixed start and end points
    start_point = locations[0]
    end_point = locations[-1]
    intermediate_points = locations[1:-1]

    # Generate initial random solution for intermediate points
    current_solution = list(range(len(intermediate_points)))
    random2.shuffle(current_solution)

    # Add fixed start and end points to the current solution
    current_solution = [0] + [i + 1 for i in current_solution] + [num_locations - 1]

    # Calculate initial solution's distance
    current_distance = sum(
        distance(locations[current_solution[i - 1]], locations[current_solution[i]])
        for i in range(1, len(current_solution))
    )

    best_solution = current_solution[:]
    best_distance = current_distance

    # Simulated Annealing
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

# Display interactive map with directions
def display_map_with_directions(route, loc_df):
    import folium
    from streamlit_folium import st_folium

    m = folium.Map(location=[route[0][0], route[0][1]], zoom_start=13)

    # Add markers and lines for the route
    for i in range(len(route) - 1):
        folium.Marker(
            location=route[i],
            popup=loc_df.loc[loc_df['Coordinates'] == route[i], 'Place_Name'].values[0],
            icon=folium.Icon(color='blue' if i != 0 else 'green', icon='info-sign')
        ).add_to(m)
        folium.Marker(
            location=route[i + 1],
            popup=loc_df.loc[loc_df['Coordinates'] == route[i + 1], 'Place_Name'].values[0],
            icon=folium.Icon(color='blue' if i != len(route) - 2 else 'red', icon='info-sign')
        ).add_to(m)
        folium.PolyLine(
            locations=[route[i], route[i + 1]],
            color="blue",
            weight=2.5,
            opacity=1
        ).add_to(m)

    st_folium(m, width=700, height=500)

# Main Streamlit application
def main():
    st.title("Route Optimization with Interactive Map")

    # Create separate tabs for address input and map/route table
    tab1, tab2 = st.tabs(["Address Input", "Map & Route Table"])

    with tab1:
        # Default addresses
        default_addresses = [
            "1950 Old Alabama Rd, Roswell, GA, 30076",
            "6015 State Bridge rd, Duluth, GA, 30097",
            "3102 Hartford Mill Pl, Duluth, GA,30097",
            "928 Hawk Creek Trail, Lawrenceville, GA,30043",
            "1699 Centerville Dr, Buford, GA,30518",
            "1323 Terrasol ridge sw, lilburn, ga, 30047"
        ]
        
        # Upload CSV file with addresses
        uploaded_file = st.file_uploader("Upload CSV file with addresses", type="csv")
        
        if uploaded_file is not None:
            addresses_df = pd.read_csv(uploaded_file)
            addresses = addresses_df['Address'].tolist()
            # If the list is shorter than 10, fill with default addresses
            while len(addresses) < 10:
                addresses.append("")
        else:
            # Input for up to 10 addresses with default addresses pre-populated
            st.write("Enter up to 10 addresses:")
            addresses = [st.text_input(f"Address {i + 1}", value=default_addresses[i] if i < len(default_addresses) else "") for i in range(10)]

    with tab2:
        # Display map and calculate route
        if st.button("Optimize Route"):
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

            # Solve TSP for route optimization
            data_model = create_data_model(locations)
            try:
                optimal_route = tsp_solver(data_model)

                # Display interactive map with directions
                display_map_with_directions(optimal_route, loc_df)
                
                # Display route table
                display_route(optimal_route, loc_df)

                # Generate Google Maps link
                gmaps_link = "https://www.google.com/maps/dir/" + "/".join(
                    [f"{lat},{lon}" for lat, lon in optimal_route]
                )
                st.markdown(f"[Open Optimized Route in Google Maps]({gmaps_link})")
                
            except Exception as e:
                st.error(f"An error occurred during route optimization: {e}")

if __name__ == "__main__":
    main()
