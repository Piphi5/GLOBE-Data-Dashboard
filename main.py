import streamlit as st
from go_utils import get_api_data
from go_utils.geoenrich import get_country_api_data
from go_utils import mhm, lc
import datetime
from pandas.api.types import is_numeric_dtype
import pandas as pd
import numpy as np
from functools import partial
import matplotlib.pyplot as plt
import base64


def numeric_filter(operation, value, column, df):
    return eval(f"df['{column}'] {operation} {value}")


def value_filter(values, exclude, column, df):
    if exclude:
        data_filter = np.vectorize(lambda entry: entry not in selected_values)
    else:
        data_filter = np.vectorize(lambda entry: entry in selected_values)
    return data_filter(df[column].to_numpy())


def get_table_download_link(df, name):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(
        csv.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{name}.csv">Download csv file</a>'
    return href


protocols = {
    "Mosquito Habitat Mapper": "mosquito_habitat_mapper",
    "Land Cover": "land_covers",
}

plotting = {
    "Mosquito Habitat Mapper": mhm.diagnostic_plots,
    "Land Cover": lc.diagnostic_plots,
}

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


def clear_filters():
    st.session_state["filters"] = dict()
    st.session_state["selected_filters"] = list()
    st.session_state["filtered_data"] = None


st.set_page_config(page_title="GLOBE MHM and LC Data Portal")
filtering, data_view = st.beta_columns(2)
with filtering:
    st.header("Basic Dataset Information")

    st.subheader("Protocol")
    st.session_state["protocol"] = st.selectbox(
        "Which GLOBE protocol would you like to use?", protocols.keys()
    )

    st.subheader("Date Range")
    dates = st.date_input(
        "range, no dates",
        [datetime.date(2017, 5, 31), datetime.datetime.today().date()],
    )

    download_args = {"protocol": protocols[st.session_state["protocol"]]}

    if len(dates) == 2:
        start_date, end_date = dates
        download_args["start_date"] = start_date
        download_args["end_date"] = end_date

    if st.button("Get raw data"):
        st.session_state["data"] = get_api_data(**download_args)
        clear_filters()

    if st.session_state["data"] is not None:
        st.header("Filter Selector")

        # for key in st.session_state["filters"].keys():
        #         if key not in st.session_state["selected_filters"]:
        #                 del st.session_state["filters"][key]
        #                 st.write("BAD")
        st.session_state["selected_filters"] = st.multiselect(
            "Selected Filters",
            st.session_state["filters"].keys(),
            None
            if not st.session_state["selected_filters"]
            else st.session_state["selected_filters"],
        )
        st.write(st.session_state["selected_filters"])
        #
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

        if st.button("Add filter"):
            st.session_state["filters"][name] = filter_function
            st.session_state["selected_filters"].append(name)
            st.experimental_rerun()

        mask = np.full(len(st.session_state["data"]), True)
        for key, filter_func in st.session_state["filters"].items():
            if key in st.session_state["selected_filters"]:
                mask = mask & filter_func(st.session_state["data"])
        st.session_state["filtered_data"] = st.session_state["data"][mask]


with data_view:
    st.write(st.session_state["filtered_data"])
    if (
        st.session_state["protocol"] in plotting
        and st.session_state["filtered_data"] is not None
    ):
        plotting[st.session_state["protocol"]](st.session_state["filtered_data"])
        for num in plt.get_fignums():
            fig = plt.figure(num)
            st.pyplot(fig)

with st.sidebar:
    st.header("Get the Data")
    if st.button("Make Link"):
        if st.session_state["filtered_data"] is not None:
            file_name = f"{st.session_state['protocol']}-{len(st.session_state['filtered_data'])}"
            st.markdown(
                get_table_download_link(st.session_state["filtered_data"], file_name),
                unsafe_allow_html=True,
            )
