if st.button("Find Best Route"):
    if len(addresses) < 2:
        st.warning("Please enter at least two addresses.")
    else:
        # Get coordinates
        coords = [get_coordinates(address) for address in addresses]
        coords = [c for c in coords if c is not None]  # Filter invalid coords

        if len(coords) < 2:
            st.error("Could not get enough valid addresses to calculate a route.")
        else:
            # Optimize route
            optimized_coords = optimize_route(coords)
            if optimized_coords:
                # Fetch the route
                route_data = get_route(optimized_coords)
                if route_data:
                    # Extract route geometry
                    geometry = route_data["routes"][0]["geometry"]["coordinates"]
                    route_coords = [(lat, lon) for lon, lat in geometry]

                    # Prepare data for Plotly
                    route_df = pd.DataFrame(route_coords, columns=["lat", "lon"])
                    marker_df = pd.DataFrame(optimized_coords, columns=["lat", "lon"])
                    marker_df["address"] = addresses  # Use original addresses for display

                    # Create the map with Plotly
                    fig = px.scatter_mapbox(
                        marker_df,
                        lat="lat",
                        lon="lon",
                        hover_name="address",  # Address appears on hover
                        zoom=12,
                        mapbox_style="carto-positron",
                    )

                    # Add the route as a line
                    fig.add_scattermapbox(
                        lat=route_df["lat"],
                        lon=route_df["lon"],
                        mode="lines",
                        line=dict(width=4, color="blue"),
                        name="Route",
                        hoverinfo="skip",  # Disable hover for the line
                    )

                    # Display the map
                    st.plotly_chart(fig, use_container_width=True)
