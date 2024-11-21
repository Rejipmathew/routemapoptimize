import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
import itertools

# OSRM Configuration
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"

# Function to get coordinates
def get_coordinates(address):
    geolocator = Nominatim(user_agent="route_optimizer")
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    else:
        st.error(f"Could not geocode address: {address}")
        return None

# Function to get route distance between two points
def get_route_distance(coord1, coord2):
    coord_string = f"{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}"
    params = {"overview": "false", "geometries": "polyline"}
    response = requests.get(f"{OSRM_BASE_URL}/{coord_string}", params=params)
    if response.status_code == 200:
        route_data = response.json()
        return route_data["routes"][0]["distance"]  # Distance in meters
    else:
        return float("inf")  # Return a large distance if there's an error

# Function to optimize route using TSP (Brute Force)
def optimize_route(coords):
    min_distance = float("inf")
    best_order = None
    for order in itertools.permutations(coords):
        total_distance = sum(
            get_route_distance(order[i], order[i + 1]) for i in range(len(order) - 1)
        )
        if total_distance < min_distance:
            min_distance = total_distance
            best_order = order
    return best_order

# Function to get the optimized route from OSRM
def get_route(coords):
    coord_string = ";".join([f"{lon},{lat}" for lat, lon in coords])
    params = {"overview": "full", "geometries": "geojson"}
    response = requests.get(f"{OSRM_BASE_URL}/{coord_string}", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error fetching route data from OSRM.")
        return None

# Streamlit App
st.title("Route Optimizer with OpenStreetMap (Plotly)")
st.subheader("Enter up to 10 addresses:")

# Input fields for addresses
addresses = []
for i in range(10):
    address = st.text_input(f"Address {i + 1}", key=f"address_{i}")
    if address.strip():
        addresses.append(address.strip())

# Process on button click
if st.button("Find Best Route"):
    if len(addresses) < 2:
        st.warning("Please enter at least two addresses.")
    else:
        # Get coordinates
        coords = [get_coordinates(address) for address in addresses]
        coords = [c for c in coords if c is not None]  # Filter out invalid coordinates

        if len(coords) < 2:
            st.error("Not enough valid addresses to calculate a route.")
        else:
            # Optimize the route
            optimized_coords = optimize_route(coords)
            if optimized_coords:
                # Fetch route from OSRM
                route_data = get_route(optimized_coords)
                if route_data:
                    # Extract route geometry
                    geometry = route_data["routes"][0]["geometry"]["coordinates"]
                    route_coords = [(lat, lon) for lon, lat in geometry]

                    # Prepare data for Plotly
                    route_df = pd.DataFrame(route_coords, columns=["lat", "lon"])
                    marker_df = pd.DataFrame(optimized_coords, columns=["lat", "lon"])
                    marker_df["address"] = addresses

                    # Create the map with Plotly
                    fig = px.scatter_mapbox(
                        marker_df,
                        lat="lat",
                        lon="lon",
                        hover_name="address",  # Display address on hover
                        zoom=12,
                        mapbox_style="carto-positron",
                    )

                    # Add route line
                    fig.add_scattermapbox(
                        lat=route_df["lat"],
                        lon=route_df["lon"],
                        mode="lines",
                        line=dict(width=4, color="blue"),
                        name="Route",
                        hoverinfo="skip",  # Disable hover on the line
                    )

                    # Display map
                    st.plotly_chart(fig, use_container_width=True)
