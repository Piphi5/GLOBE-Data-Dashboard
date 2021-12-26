import datetime
import json
from functools import partial
from io import StringIO
from random import randint

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from go_utils import get_api_data, lc, mhm
from pandas.api.types import is_numeric_dtype

from constants import data_keys, date_fmt, protocols
from utils import (
    get_metadata_download_link,
    get_table_download_link,
    numeric_filter,
    update_data_args,
    value_filter,
)

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
if "selected_filter_types" not in st.session_state:
    st.session_state["selected_filter_types"] = list()

if "protocol" not in st.session_state:
    st.session_state["protocol"] = ""

if "download_args" not in st.session_state:
    st.session_state["download_args"] = dict()


def clear_filters():
    st.session_state["filters"] = dict()
    st.session_state["selected_filters"] = list()
    st.session_state["filtered_data"] = None


st.set_page_config(page_title="GLOBE Observer MHM and LC Data Portal")
filtering, data_view = st.columns(2)
with filtering:
    st.header("Basic Dataset Information")

    if st.session_state["file_loaded"]:
        index = list(protocols.keys()).index(
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
        dates = st.date_input(
            "range, no dates",
            [
                st.session_state["download_args"]["start_date"],
                st.session_state["download_args"]["end_date"],
            ],
        )
    else:
        dates = st.date_input(
            "range, no dates",
            [datetime.date(2017, 5, 31), datetime.datetime.today().date()],
        )

    st.session_state["download_args"]["protocol"] = protocols[
        st.session_state["protocol"]
    ]

    if len(dates) == 2:
        start_date, end_date = dates
        st.session_state["download_args"]["start_date"] = start_date
        st.session_state["download_args"]["end_date"] = end_date

    # Retrieves cleaned GLOBE Data matching your given parameters
    if st.button("Get raw data"):
        st.session_state["data"] = get_api_data(**st.session_state["download_args"])
        clear_filters()

    if st.session_state["file_loaded"]:
        st.session_state["data"] = get_api_data(**st.session_state["download_args"])
        st.session_state["file_loaded"] = False

    # Allows users to further filter API-returned data
    if st.session_state["data"] is not None:
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
            "Select the column", st.session_state["data"].columns
        )

        if (
            is_numeric_dtype(st.session_state["data"][selected_col])
            and len(pd.unique(st.session_state["data"][selected_col])) > 2
        ):
            selected_op = st.selectbox("Operation", [">", "<", "==", ">=", "<=", "!="])
            value = st.number_input("Enter value")
            filter_function = partial(numeric_filter, selected_op, value, selected_col)
            filter_type = "numeric"
            name = f"{selected_col} {selected_op} {value}"
        else:
            selected_values = st.multiselect(
                "Select values", pd.unique(st.session_state["data"][selected_col])
            )
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
            st.session_state["selected_filter_types"].append(filter_type)
            st.experimental_rerun()

        # All filters return a boolean mask used to filter the finalized dataset
        mask = np.full(len(st.session_state["data"]), True)
        for key, filter_func in st.session_state["filters"].items():
            if key in st.session_state["selected_filters"]:
                mask = mask & filter_func(st.session_state["data"])
        st.session_state["filtered_data"] = st.session_state["data"][mask]


with data_view:
    if (
        st.session_state["protocol"] in plotting
        and st.session_state["filtered_data"] is not None
    ):
        st.write(
            st.session_state["filtered_data"][
                : min(10000, len(st.session_state["filtered_data"]))
            ]
        )
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
            st.session_state["filters"],
        )

        st.session_state["file_loaded"] = True
        if "uploader_key" in st.session_state.keys():
            st.session_state.pop("uploader_key")
        st.experimental_rerun()

    st.header("Get the Data")
    if st.button("Make CSV Link"):
        if st.session_state["filtered_data"] is not None:
            file_name = f"{st.session_state['protocol']}-{len(st.session_state['filtered_data'])}"
            st.markdown(
                get_table_download_link(st.session_state["filtered_data"], file_name),
                unsafe_allow_html=True,
            )
    st.header("Download Metadata JSON")
    if st.button("Make JSON Link"):
        download_data = {**st.session_state["download_args"], **st.session_state}
        json_obj = json.dumps(
            {
                key: download_data[key]
                if type(download_data[key]) is not datetime.date
                else download_data[key].strftime(date_fmt)
                for key in data_keys
            }
        )
        if st.session_state["filtered_data"] is not None:
            file_name = f"{st.session_state['protocol']}-{len(st.session_state['filtered_data'])}"
            st.markdown(
                get_metadata_download_link(json_obj, file_name),
                unsafe_allow_html=True,
            )
