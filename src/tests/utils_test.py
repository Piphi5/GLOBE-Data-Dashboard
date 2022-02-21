import datetime
import json
import os
import sys

import pandas as pd
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (  # noqa: E402
    datetime_to_str,
    get_metadata_download_link,
    get_numeric_filter_args,
    get_table_download_link,
    get_value_filter_args,
    numeric_filter,
    value_filter,
)

numerical_test_values = [
    (">", 5, "mhm_LarvaeCount", [5, 0, -9999, 10], [False, False, False, True]),
    ("<", 45, "mhm_Latitude", [37.5, 0, 75.5, -90.0], [True, True, False, True]),
    (">=", 45, "mhm_Longitude", [37.5, 45.0, 75.5, -90.0], [False, True, True, False]),
    ("<=", 5, "mhm_Latitude", [5, 0, -9999, 10], [True, True, True, False]),
    ("==", 45, "mhm_Latitude", [37.5, 0, 45, -90.0], [False, False, True, False]),
    ("!=", 45, "mhm_Latitude", [37.5, 0, 45, -90.0], [True, True, False, True]),
]

value_test_values = [
    # Test booleans
    (
        [True],
        False,
        "mhm_HasEggs",
        [True, False, False, True],
        [True, False, False, True],
    ),
    # Test LC flags
    (
        ["001001", "001111"],
        False,
        "lc_PhotoBitBinary",
        ["001001", "001111", "011001", "101111", "000000", "001100"],
        [True, True, False, False, False, False, False],
    ),
    (
        ["001001", "001111"],
        True,
        "lc_ClassificationBitBinary",
        ["001001", "001111", "011001", "101111", "000000", "001100"],
        [False, False, True, True, True, True],
    ),
    # Test Bit Flags
    (
        ["1"],
        True,
        "mhm_WatersourceIsContainer",
        ["1", "0", "1", "0", "0", "1"],
        [False, True, False, True, True, False],
    ),
]

numerical_test_string_values = [
    ("mhm_LarvaeCount > 5", ">", "5", "mhm_LarvaeCount"),
    ("mhm_LarvaeCount <= -8", "<=", "-8", "mhm_LarvaeCount"),
    ("mhm_Latitude < 45", "<", "45", "mhm_Latitude"),
    ("mhm_Latitude == 36.23", "==", "36.23", "mhm_Latitude"),
    ("mhm_Longitude >= 22", ">=", "22", "mhm_Longitude"),
    ("mhm_Longitude != 0", "!=", "0", "mhm_Longitude"),
]

value_test_string_values = [
    ("mhm_HasEggs in [True]", [True], False, "mhm_HasEggs"),
    (
        "lc_ClassificationBitBinary in ['001001', '001111', '011001']",
        ["001001", "001111", "011001"],
        False,
        "lc_ClassificationBitBinary",
    ),
    (
        "lc_ClassificationBitBinary not in ['001001', '001111', '011001']",
        ["001001", "001111", "011001"],
        True,
        "lc_ClassificationBitBinary",
    ),
    ("mhm_HasEggs not in [True]", [True], True, "mhm_HasEggs"),
]

datetime_test_string = [
    (datetime.datetime(2017, 5, 31), "2017-05-31"),
    (datetime.datetime(2020, 11, 3), "2020-11-03"),
    (datetime.datetime(2021, 8, 12), "2021-08-12"),
]


def list_to_df(column, data):
    return pd.DataFrame.from_dict({column: data})


def run_filtering_comparison(func, desired, data, column, **kwargs):
    df = list_to_df(column, data)
    for desired, result in zip(desired, func(df=df, column=column, **kwargs)):
        assert desired == result


@pytest.mark.parametrize(
    "operation, value, column, data, desired", numerical_test_values
)
def test_number_filter(operation, value, column, data, desired):
    run_filtering_comparison(
        numeric_filter, desired, data, column, operation=operation, value=value
    )


@pytest.mark.parametrize("values, exclude, column, data, desired", value_test_values)
def test_value_filter(values, exclude, column, data, desired):
    run_filtering_comparison(
        value_filter, desired, data, column, exclude=exclude, values=values
    )


@pytest.mark.parametrize(
    "filter_name, operation, value, column", numerical_test_string_values
)
def test_numeric_filter_parse(filter_name, operation, value, column):
    test_operation, test_value, test_column = get_numeric_filter_args(filter_name)
    assert test_operation == operation
    assert test_value == value
    assert test_column == column


@pytest.mark.parametrize(
    "filter_name, values, exclude, column", value_test_string_values
)
def test_value_filter_parse(filter_name, values, exclude, column):
    test_values, test_exclude, test_column = get_value_filter_args(filter_name)
    assert all([test_value == value for test_value, value in zip(test_values, values)])
    assert test_exclude == test_exclude
    assert test_column == column


@pytest.mark.parametrize("datetime, datetime_str", datetime_test_string)
def test_datetime_conversion(datetime, datetime_str):
    test_str = datetime_to_str(datetime)
    assert test_str == datetime_str


# Make sure test runs
def test_link_gen():
    df = pd.DataFrame.from_dict({"test": [1, 2, 3]})
    get_table_download_link(df, "test.csv")

    json_test = {"test": "test", "test1": [1, 2, 3]}
    get_metadata_download_link(json.dumps(json_test), "test.json")
