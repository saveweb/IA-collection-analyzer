import streamlit as st
import pandas as pd
import numpy as np
from ia_collection_analyzer.getmetadatas import fetch_metadata
from ia_collection_analyzer.constdatas import REQUIRED_METADATA

st.title("Internet Archive Collection Analyzer")

st.write(
    "This is a simple web app that analyzes the metadata of an Internet Archive collection."
)

st.markdown(
    "Here are some example / suggested collections to analyze:"
    "\n - [`wikiteam`](https://archive.org/details/wikiteam): `~421,000` items. A Large collection of archived wikis. (Not suggested currently, as this have 14 years of history, some data may cause bugs of this program.)"
    "\n - [`bilibili_videos`](https://archive.org/details/bilibili_videos): `~48,000` items. A collection of archived videos from an Chinese Youtube-like website [Bilibili](https://www.bilibili.com/). Archive tool can be found at [GitHub](https://github.com/saveweb/biliarchiver)."
    "\n - [`bilibili_videos_sub_1`](https://archive.org/details/bilibili_videos_sub_1): `~20,000` items. A subset of the `bilibili_videos` collection."
)

# cache system
if "collection_id" not in st.session_state:
    st.session_state.collection_id = "bilibili_videos"
if "got_metadata" not in st.session_state:
    st.session_state.got_metadata = False
if "items_pd" not in st.session_state:
    st.session_state.items_pd = None
if "selected_columns" not in st.session_state:
    st.session_state.selected_columns = []
if "filtered_pd" not in st.session_state:
    st.session_state.filtered_pd = None

# input the collection name
col1, col2 = st.columns([6, 1], vertical_alignment="bottom")
with col1:
    collection_id = st.text_input("Enter the collection ID:", "bilibili_videos")
    collection_id = (
        collection_id.strip()
        .replace(" ", "_")
        .replace('"', "")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
    )
with col2:
    conform_button = st.button("Conform")

if not conform_button and not st.session_state.got_metadata or collection_id == "":
    st.stop()

# Check if we need to fetch new data
if not st.session_state.got_metadata or collection_id != st.session_state.collection_id:
    guide_text = st.markdown(
        f"Getting fresh metadata for collection: **{collection_id}**"
    )
    items = fetch_metadata(collection_id)
    items_pd = pd.DataFrame(items)
    if items_pd.empty:
        st.error(
            "Failed to fetch metadata for the collection. Please check the collection ID."
        )
        st.stop()

    data_transform_text = st.text("cleaning data...")
    # drop columns with 80%+ nan
    items_pd = items_pd.dropna(axis=1, thresh=0.8 * len(items_pd))
    items_pd = items_pd.dropna(axis=0, thresh=0.7 * len(items_pd.columns))
    # drop mediatype=collections
    items_pd = items_pd[items_pd["mediatype"] != "collection"]

    # drop columns with different types inner.
    # for col in items_pd.columns:
    #    items_pd[col] = items_pd[col].apply(lambda x: x if isinstance(x, type(items_pd[col][0])) else np.nan)

    # calculate metadata
    data_transform_text.text("calculating metadata...")
    items_pd["addeddate"] = pd.to_datetime(items_pd["addeddate"])
    items_pd["publicdate"] = pd.to_datetime(items_pd["publicdate"])
    data_transform_text.text("Data transformation and cleaning complete!")

    # Update cache
    st.session_state.collection_id = collection_id
    st.session_state.items_pd = items_pd
    st.session_state.got_metadata = True
    st.session_state.selected_columns = []
else:
    guide_text = st.markdown(
        f"Using cached metadata for collection: **{collection_id}**"
    )
    items_pd = st.session_state.items_pd

st.write("The collection contains the following items:")
try:
    st.write(items_pd.head(10))
except Exception as e:
    st.markdown("Failed to display top 10 lines. Only first will be shown.")
    st.write(items_pd.head(1))
    st.write(e)

st.header("Selecting columns to analyze")
st.write("Select additional columns you want to analyze:")
seleactable_columns = [col for col in items_pd.columns if col not in REQUIRED_METADATA]

col1, col2 = st.columns([6, 1], vertical_alignment="bottom")
selected_columns = st.multiselect("Select columns:", seleactable_columns, default=[])

# Update the filtering code to use cache
if (
    st.session_state.filtered_pd is None
    or selected_columns != st.session_state.selected_columns
):
    filtered_pd = items_pd[selected_columns + REQUIRED_METADATA]
    filtered_pd = filtered_pd.dropna(axis=0, how="any")

    # Cache the filtered dataframe and selected columns
    st.session_state.filtered_pd = filtered_pd
    st.session_state.selected_columns = selected_columns
else:
    filtered_pd = st.session_state.filtered_pd

# Display preview (existing code)
st.write("Preview of the selected columns:")
st.write(filtered_pd.head(30))

# Plan to plot
col1, col2, col3 = st.columns([3, 3, 1], vertical_alignment="bottom")
with col1:
    x_axis = st.selectbox("Select the x-axis:", selected_columns)
with col2:
    y_axis = st.selectbox("Select the y-axis:", selected_columns)
with col3:
    plot_button = st.button("Plot")

if plot_button and x_axis != y_axis:
    st.write("Plotting the data...")
    st.write(f"X-axis: {x_axis}, Y-axis: {y_axis}")

    # Create comprehensive aggregation table
    all_metrics = (
        filtered_pd.groupby(x_axis)[y_axis]
        .agg(
            [
                ("Count", "count"),
                ("Sum", "sum"),
                ("Mean", "mean"),
                ("Median", "median"),
                ("Min", "min"),
                ("Max", "max"),
            ]
        )
        .reset_index()
    )

    # Display complete aggregated data
    st.write("Complete aggregation metrics:")
    # Create multi-line chart (excluding Count since it's often on different scale)
    metrics_for_plot = all_metrics.drop(columns=["Count", "Sum", "Max"])
    metrics_for_plot = metrics_for_plot.set_index(x_axis)

    st.write("Multi-metric trend lines:")
    st.line_chart(metrics_for_plot)

    st.write(all_metrics)
