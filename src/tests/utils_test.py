import pytest
import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import value_filter, numeric_filter, get_table_download_link  # noqa: E402


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


# Make sure test runs
def test_link_gen():
    df = pd.DataFrame.from_dict({"test": [1, 2, 3]})
    get_table_download_link(df, "test.csv")
