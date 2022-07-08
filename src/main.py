import copy
import datetime
import json
from functools import partial
from io import StringIO
from random import randint

import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from go_utils import constants, lc, mhm
from pandas.api.types import is_hashable, is_numeric_dtype

from constants import default_cleanup_dict, protocols
from utils import (
    apply_cleanup_filters,
    apply_filters,
    convert_df,
    download_data,
    generate_json_object,
    numeric_filter,
    update_data_args,
    value_filter,
)

country_list = [
    country for countries in constants.region_dict.values() for country in countries
]

plotting = {
    "Mosquito Habitat Mapper": mhm.diagnostic_plots,
    "Land Cover": lc.diagnostic_plots,
}

index = 0

if "file_loaded" not in st.session_state:
    st.session_state["file_loaded"] = False

if "data" not in st.session_state:
    st.session_state["data"] = None

if "filtered_data" not in st.session_state:
    st.session_state["filtered_data"] = None

if "filters" not in st.session_state:
    st.session_state["filters"] = dict()

if "selected_filters" not in st.session_state:
    st.session_state["selected_filters"] = list()


if "protocol" not in st.session_state:
    st.session_state["protocol"] = ""

if "download_args" not in st.session_state:
    st.session_state["download_args"] = dict()

if "display_map" not in st.session_state:
    st.session_state["display_map"] = False
if "cleanup_filters" not in st.session_state:
    st.session_state["cleanup_filters"] = copy.deepcopy(default_cleanup_dict)
if "cleaned_data" not in st.session_state:
    st.session_state["cleaned_data"] = pd.DataFrame()
if "selected_filter_defaults" not in st.session_state:
    st.session_state["selected_filter_defaults"] = []
if "cleanup_defaults" not in st.session_state:
    st.session_state["cleanup_defaults"] = []


def clear_filters():
    st.session_state["filters"] = dict()
    st.session_state["selected_filters"] = list()
    st.session_state["filtered_data"] = None


st.set_page_config(page_title="GLOBE Observer MHM and LC Data Portal", layout="wide")
filtering, data_view, plots = st.columns(3)
with filtering:
    st.header("Basic Dataset Information")

    if st.session_state["file_loaded"]:
        index = list(protocols.values()).index(
            st.session_state["download_args"]["protocol"]
        )

    # Users select the GLOBE Observer Protocol
    st.subheader("Protocol")
    st.session_state["protocol"] = st.selectbox(
        "Which GLOBE protocol would you like to use?", protocols.keys(), index=index
    )

    # Users select their desired data range
    st.subheader("Date Range")
    if st.session_state["file_loaded"]:
        start_date = st.date_input(
            "Start Date",
            st.session_state["download_args"]["start_date"],
        )
        end_date = st.date_input(
            "End Date",
            st.session_state["download_args"]["end_date"],
        )
    else:
        start_date = st.date_input(
            "Start Date",
            datetime.date(2017, 5, 31),
        )
        end_date = st.date_input(
            "End Date",
            datetime.datetime.today().date(),
        )

    st.session_state["download_args"]["protocol"] = protocols[
        st.session_state["protocol"]
    ]

    st.session_state["download_args"]["start_date"] = start_date
    st.session_state["download_args"]["end_date"] = end_date

    if st.session_state["file_loaded"]:
        default_countries = st.session_state["download_args"]["countries"]
        default_regions = st.session_state["download_args"]["regions"]
    else:
        default_countries = []
        default_regions = []

    st.subheader("Countries")
    st.session_state["download_args"]["countries"] = st.multiselect(
        "Select countries", country_list, default=default_countries
    )
    st.subheader("Regions")
    st.session_state["download_args"]["regions"] = st.multiselect(
        "Select regions", constants.region_dict.keys(), default=default_regions
    )

    # Retrieves cleaned GLOBE Data matching your given parameters
    if st.button("Get raw data"):
        st.session_state["data"] = download_data(st.session_state["download_args"])
        clear_filters()

    if st.session_state["file_loaded"]:
        st.session_state["data"] = download_data(st.session_state["download_args"])
        st.session_state["cleanup_defaults"] = st.session_state["cleanup_filters"][
            "duplicate_filter_cols"
        ]
        st.session_state["selected_filter_defaults"] = st.session_state[
            "selected_filters"
        ]
        st.session_state["file_loaded"] = False

    # Allows users to further filter API-returned data
    if st.session_state["data"] is not None:
        st.header("Cleanup Filter Selection")
        with st.expander("Options"):
            st.markdown("## Documentation:")
            st.markdown(
                """
            To better understand the purpose of these filters and their procedures you can visit the following links:  
            - [Poor geolocational filter](https://iges-geospatial.github.io/globe-observer-utils-docs/go_utils/filtering.html#filter-poor-geolocational-data)  
            - [Valid coordinates filter](https://iges-geospatial.github.io/globe-observer-utils-docs/go_utils/filtering.html#filter-invalid-coords)  
            - [Duplicates filter](https://iges-geospatial.github.io/globe-observer-utils-docs/go_utils/filtering.html#filter-duplicates)
            """
            )
            geolocation_filter = st.checkbox(
                "Apply Poor Geolocational Data Filter",
                value=st.session_state["cleanup_filters"]["poor_geolocation_filter"],
            )
            valid_coords = st.checkbox(
                "Apply Valid Coordinates Data Filter (exclusive)",
                value=st.session_state["cleanup_filters"]["valid_coords_filter"],
            )
            st.session_state["cleanup_filters"][
                "poor_geolocation_filter"
            ] = geolocation_filter
            st.session_state["cleanup_filters"]["valid_coords_filter"] = valid_coords
            duplicate_filter = st.checkbox(
                "Apply Duplicate Filter",
                value=st.session_state["cleanup_filters"]["duplicate_filter"],
            )
            if duplicate_filter:
                group_criteria = st.multiselect(
                    "Matching Columns",
                    st.session_state["data"].columns,
                    default=st.session_state["cleanup_defaults"],
                )
                min_size = st.number_input(
                    "Group size (inclusive)",
                    2,
                    value=st.session_state["cleanup_filters"]["duplicate_filter_size"],
                )
                st.session_state["cleanup_filters"][
                    "duplicate_filter_cols"
                ] = group_criteria
                st.session_state["cleanup_filters"]["duplicate_filter_size"] = min_size
            st.session_state["cleanup_filters"]["duplicate_filter"] = duplicate_filter
        st.session_state["cleaned_data"] = apply_cleanup_filters(
            st.session_state["data"], **st.session_state["cleanup_filters"]
        )

        st.header("Filter Selector")
        st.session_state["selected_filters"] = st.multiselect(
            "Selected Filters",
            st.session_state["filters"].keys(),
            None
            if not st.session_state["selected_filters"]
            else st.session_state["selected_filters"],
        )
        st.write(st.session_state["selected_filters"])

        selected_col = st.selectbox(
            "Select the column", st.session_state["cleaned_data"].columns
        )

        if (
            is_numeric_dtype(st.session_state["cleaned_data"][selected_col])
            and len(pd.unique(st.session_state["cleaned_data"][selected_col])) > 2
        ):
            selected_op = st.selectbox("Operation", [">", "<", "==", ">=", "<=", "!="])
            value = st.number_input("Enter value")
            filter_function = partial(numeric_filter, selected_op, value, selected_col)
            filter_type = "numeric"
            name = f"{selected_col} {selected_op} {value}"
        else:
            if np.all(
                [
                    np.vectorize(is_hashable)(
                        st.session_state["cleaned_data"][selected_col].to_numpy()
                    )
                ]
            ):
                selection_values = pd.unique(
                    st.session_state["cleaned_data"][selected_col]
                )
            else:
                teams = []
                for _, row in st.session_state["cleaned_data"].iterrows():
                    if not is_hashable(row[selected_col]):
                        for team in row[selected_col]:
                            teams.append(team)
                teams = set(teams)
                selection_values = list(teams)

            selected_values = st.multiselect("Select values", selection_values)

            is_remove = st.checkbox("Remove Selected Values")
            operation = "not in" if is_remove else "in"
            name = f"{selected_col} {operation} {selected_values}"
            filter_function = partial(
                value_filter, selected_values, is_remove, selected_col
            )
            filter_type = "value"
        if st.button("Add filter"):
            st.session_state["filters"][name] = filter_function
            st.session_state["selected_filters"].append(name)
            st.experimental_rerun()

        st.session_state["filtered_data"] = apply_filters(
            st.session_state["cleaned_data"],
            st.session_state["filters"],
            st.session_state["selected_filters"],
        )

has_data = (
    st.session_state["protocol"] in plotting
    and st.session_state["filtered_data"] is not None
)

with data_view:
    st.session_state["display_map"] = st.checkbox(
        "Display Map", value=st.session_state["display_map"]
    )
    if has_data:
        # Display Map if its checked
        if st.session_state["display_map"]:
            prefix = constants.abbreviation_dict[
                st.session_state["download_args"]["protocol"]
            ]
            lon_col = f"{prefix}_Longitude"
            lat_col = f"{prefix}_Latitude"
            m = leafmap.Map()
            m.add_points_from_xy(
                st.session_state["filtered_data"][[lat_col, lon_col]],
                x=lon_col,
                y=lat_col,
                popups=[],
                layer_name="Points",
            )
            m.to_streamlit()

        # Display data table (first 10000 entries)
        st.write(
            st.session_state["filtered_data"][
                : min(10000, len(st.session_state["filtered_data"]))
            ]
        )

with plots:
    if has_data:
        plotting[st.session_state["protocol"]](st.session_state["filtered_data"])
        for num in plt.get_fignums():
            fig = plt.figure(num)
            st.pyplot(fig)

with st.sidebar:
    st.header("Upload JSON")
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = str(randint(1000, 100000000))
    uploaded_file = st.file_uploader(
        "Choose a file", key=st.session_state["uploader_key"]
    )
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        metadata = json.loads(stringio.read())
        update_data_args(
            metadata,
            st.session_state["download_args"],
            st.session_state["selected_filters"],
            st.session_state["cleanup_filters"],
            st.session_state["filters"],
        )
        st.session_state["file_loaded"] = True
        if "uploader_key" in st.session_state.keys():
            st.session_state.pop("uploader_key")
        st.experimental_rerun()

    if type(st.session_state["filtered_data"]) is pd.DataFrame:
        st.header("Get the Data")
        st.download_button(
            "Download CSV",
            convert_df(st.session_state["filtered_data"]),
            file_name=f"{st.session_state['protocol']}-{len(st.session_state['filtered_data'])}.csv",
        )

        st.header("Download Metadata JSON")
        download_data = {**st.session_state["download_args"], **st.session_state}
        json_obj = str(generate_json_object(download_data)).encode("utf-8")
        st.download_button(
            "Download Metadata JSON",
            json_obj,
            file_name=f"{st.session_state['protocol']}-{len(st.session_state['filtered_data'])}.json",
        )
