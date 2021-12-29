import ast
import base64
import datetime
import json
import re
from functools import partial

import numpy as np

from constants import data_keys, date_fmt


def numeric_filter(operation, value, column, df):
    """Filters a data column numerically.
    Parameters
    ----------
    operation: str
        Operator used to filter data (e.g. ">", "<", "==", ">=", "<=", "!=")
    value: float
        Operand / number
    column: str
        String for column name
    df: pd.DataFrame
        DataFrame
    Returns
    -------
    ndarray
        1D Boolean array that indicates whether each entry of the DataFrame matches the given numeric filter.
    """
    return eval(f"df['{column}'] {operation} {value}")


def get_numeric_filter_args(filter_name):

    column, operation, value = filter_name.split(" ")
    return operation, value, column


def value_filter(values, exclude, column, df):
    """Filters a given data column by the presence of given values.
    Parameters
    ----------
    values: list
        List of desired or unwanted cell values in a given column
    exclude: bool
        boolean indicating whether to include or exclude values
    column: str
        String for column name
    df: pd.DataFrame
        DataFrame
    Returns
    -------
    ndarray
        1D Boolean array mask indicating which entries match the given criteria
    """
    if exclude:
        data_filter = np.vectorize(lambda entry: entry not in values)
    else:
        data_filter = np.vectorize(lambda entry: entry in values)
    return data_filter(df[column].to_numpy())


def get_value_filter_args(filter_name):
    values = ast.literal_eval(re.search(r"\[.*\]", filter_name).group(0))
    exclude = "not" in filter_name
    column = filter_name.split(" ")[0]
    return values, exclude, column


def get_table_download_link(df, name):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    Parameters
    ----------
    df: pd.DataFrame
        DataFrame to be downloaded
    name: str
        The filename for the CSV (doesn't include .csv)
    Returns
    -------
    str
        href string that will download the data to the user as a CSV
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(
        csv.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{name}.csv">Download csv file</a>'
    return href


def apply_filters(data, filter_dict, selected_filters_list):
    # All filters return a boolean mask used to filter the finalized dataset
    mask = np.full(len(data), True)
    for key, filter_func in filter_dict.items():
        if key in selected_filters_list:
            mask = mask & filter_func(data)
    return data[mask]


def get_metadata_download_link(json, name):
    json_str = str(json)
    b64 = base64.b64encode(
        json_str.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/json;base64,{b64}" download="{name}.json">Download json file</a>'
    return href


def update_data_args(metadata, download_args, selected_filter_list, filter_func_dict):
    filter_types = {
        "numeric": (get_numeric_filter_args, numeric_filter),
        "value": (get_value_filter_args, value_filter),
    }
    download_args["protocol"] = metadata["protocol"]
    download_args.update(
        {
            key: datetime.datetime.strptime(metadata[key], date_fmt)
            for key in data_keys
            if "date" in key
        }
    )
    for filter_name, filter_type in zip(
        metadata["selected_filters"], metadata["selected_filter_types"]
    ):
        name_parser, func = filter_types[filter_type]
        filter_function = partial(func, *name_parser(filter_name))
        filter_func_dict[filter_name] = filter_function
        selected_filter_list.append(filter_name)


def generate_json_object(download_data):
    return json.dumps(
        {
            key: download_data[key]
            if type(download_data[key]) is not datetime.date
            else download_data[key].strftime(date_fmt)
            for key in data_keys
        }
    )
