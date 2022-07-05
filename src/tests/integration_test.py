import copy
import datetime
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest
from go_utils.constants import abbreviation_dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import date_fmt, default_cleanup_dict, protocols  # noqa: E402
from utils import (  # noqa: E402
    apply_cleanup_filters,
    apply_filters,
    download_data,
    generate_json_object,
    update_data_args,
)

default_cleanup_params = copy.deepcopy(default_cleanup_dict)


test_values = [
    (
        {
            "protocol": "Mosquito Habitat Mapper",
            "start_date": datetime.date(2017, 5, 31),
            "end_date": datetime.date(2021, 12, 25),
            "selected_filters": [
                "mhm_LarvaeCount > 0.0",
                "mhm_LarvaeCountIsRangeFlag in ['110', '100', '111', '101']",
            ],
        },
        "mhm.csv",
        {
            "poor_geolocation_filter": True,
            "valid_coords_filter": False,
            "duplicate_filter": True,
            "duplicate_filter_cols": [
                "mhm_measuredDate",
                "mhm_Latitude",
                "mhm_Longitude",
                "mhm_WaterSource",
            ],
            "duplicate_filter_size": 2,
        },
        lambda df: np.all(
            (df["mhm_LarvaeCount"] > 0)
            & (
                (df["mhm_PhotoBitBinary"] == "110")
                | (df["mhm_PhotoBitBinary"] == "100")
                | (df["mhm_PhotoBitBinary"] == "111")
                | (df["mhm_PhotoBitBinary"] == "101")
            )
        ),
    ),
    (
        {
            "protocol": "Mosquito Habitat Mapper",
            "start_date": datetime.date(2021, 6, 1),
            "end_date": datetime.date(2021, 8, 1),
            "selected_filters": [
                "mhm_IsGenusOfInterest in [1]",
                "mhm_LarvaeCountIsRangeFlag < 1",
            ],
        },
        "mhm.csv",
        {
            "poor_geolocation_filter": True,
            "valid_coords_filter": True,
            "duplicate_filter": False,
            "duplicate_filter_cols": [],
            "duplicate_filter_size": 2,
        },
        lambda df: np.all(
            (df["mhm_IsGenusOfInterest"] == 1) & (df["mhm_LarvaeCountIsRangeFlag"] < 1)
        ),
    ),
    (
        {
            "protocol": "Mosquito Habitat Mapper",
            "start_date": datetime.date(2018, 8, 23),
            "end_date": datetime.date(2021, 10, 15),
            "selected_filters": [
                "mhm_PhotoCount >= 1",
                "mhm_elevation > 400",
                "mhm_Genus in ['Anopheles']",
            ],
        },
        "mhm.csv",
        {
            "poor_geolocation_filter": False,
            "valid_coords_filter": True,
            "duplicate_filter": True,
            "duplicate_filter_cols": [
                "mhm_MGRSLatitude",
                "mhm_MGRSLongitude",
                "mhm_measuredDate",
                "mhm_WaterSource",
            ],
            "duplicate_filter_size": 10,
        },
        lambda df: np.all(
            (df["mhm_elevation"] > 400)
            & (df["mhm_Genus"] == "Anopheles")
            & (df["mhm_PhotoCount"] >= 1)
        ),
    ),
    (
        {
            "protocol": "Land Cover",
            "start_date": datetime.date(2017, 5, 31),
            "end_date": datetime.date(2021, 12, 25),
            "selected_filters": [
                "lc_PrimaryClassification not in ['Barren, Bare Rock', 'Urban, Residential Property']",
                "lc_SubCompletenessScore >= 0.5",
            ],
        },
        "lc.csv",
        {
            "poor_geolocation_filter": True,
            "valid_coords_filter": True,
            "duplicate_filter": True,
            "duplicate_filter_cols": [
                "lc_MGRSLatitude",
                "lc_MGRSLongitude",
                "lc_measuredDate",
                "lc_PrimaryClassification",
            ],
            "duplicate_filter_size": 4,
        },
        lambda df: np.all(
            (df["lc_SubCompletenessScore"] >= 0.5)
            & ~(
                (df["lc_PrimaryClassification"] == "Barren, Bare Rock")
                | (df["lc_PrimaryClassification"] == "Urban, Residential Property")
            )
        ),
    ),
    (
        {
            "protocol": "Land Cover",
            "start_date": datetime.date(2018, 8, 23),
            "end_date": datetime.date(2021, 12, 25),
            "selected_filters": [
                "lc_ClassificationCount >= 3.0",
                "lc_PhotoCount >= 1.0",
            ],
        },
        "lc.csv",
        default_cleanup_params,
        lambda df: np.all(
            (df["lc_ClassificationCount"] >= 3.0) & (df["lc_PhotoCount"] >= 1.0)
        ),
    ),
    (
        {
            "protocol": "Land Cover",
            "start_date": datetime.date(2018, 8, 23),
            "end_date": datetime.date(2021, 12, 25),
            "selected_filters": ["lc_SnowIce in [True]", "lc_PrimaryPercentage > 50.0"],
        },
        "lc.csv",
        default_cleanup_params,
        lambda df: np.all((df["lc_PrimaryPercentage"] > 50.0) & (df["lc_SnowIce"])),
    ),
]


@pytest.mark.parametrize("input_json, input_data, cleanup_args, condition", test_values)
def test_files(input_json, input_data, cleanup_args, condition):
    csv_dir = os.path.join(os.getcwd(), f"src/tests/test_data/test_csvs/{input_data}")
    json_dir = os.path.join(os.getcwd(), "src/tests/test_data/test_jsons")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)

    json_dir = os.path.join(json_dir, "test.json")
    df = pd.read_csv(csv_dir)

    # Add country and region fields to JSON to match formatting
    input_json["countries"] = []
    input_json["regions"] = []

    # add cleanup filter arguments
    input_json["cleanup_filters"] = cleanup_args

    # Saves metadata to JSON
    with open(json_dir, "w") as f:
        f.write(generate_json_object(input_json))

    # Reads in saved metadata
    with open(json_dir) as f:
        metadata = json.load(f)

    print(metadata)
    # Setup variables
    download_args = {}
    selected_filter_list = list()
    cleanup_filters = dict()
    filter_func_dict = dict()
    update_data_args(
        metadata, download_args, selected_filter_list, cleanup_filters, filter_func_dict
    )

    # Download Arguments Assert
    assert download_args["protocol"] == protocols[metadata["protocol"]]

    start_date_key = "start_date"
    end_date_key = "end_date"
    assert download_args[start_date_key] == datetime.datetime.strptime(
        metadata[start_date_key], date_fmt
    )
    assert download_args[end_date_key] == datetime.datetime.strptime(
        metadata[end_date_key], date_fmt
    )

    # Cleanup tests
    target_df = apply_cleanup_filters(df, **cleanup_args)
    test_df = apply_cleanup_filters(df, **cleanup_filters)
    assert target_df.equals(test_df)

    # Filter tests
    filtered_df = apply_filters(df, filter_func_dict, selected_filter_list)
    assert condition(filtered_df)

    # Cleanup JSON
    os.remove(json_dir)


raw_data_values = [
    {
        "protocol": "Mosquito Habitat Mapper",
        "start_date": datetime.date(2017, 5, 31),
        "end_date": datetime.date(2021, 12, 25),
        "countries": ["Brazil"],
        "regions": ["North America", "Africa"],
    },
    {
        "protocol": "Land Cover",
        "start_date": datetime.date(2017, 5, 31),
        "end_date": datetime.date(2021, 12, 25),
        "countries": ["Thailand"],
        "regions": [],
    },
    {
        "protocol": "Mosquito Habitat Mapper",
        "start_date": datetime.date(2017, 5, 31),
        "end_date": datetime.date(2021, 12, 25),
        "countries": [],
        "regions": [],
    },
]


@pytest.mark.parametrize("input_json", raw_data_values)
def test_raw_data_download(input_json):
    # Add blank selected filters to json to match formatting
    input_json["selected_filters"] = []
    input_json["selected_filter_types"] = []
    input_json["cleanup_filters"] = {}

    json_dir = os.path.join(os.getcwd(), "src/tests/test_data/test_jsons")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)

    json_dir = os.path.join(json_dir, "test.json")

    # Saves metadata to JSON
    with open(json_dir, "w") as f:
        f.write(generate_json_object(input_json))

    # Reads in saved metadata
    with open(json_dir) as f:
        metadata = json.load(f)

    # Setup variables
    download_args = dict()
    selected_filter_list = list()
    cleanup_filters = dict()
    filter_func_dict = dict()
    update_data_args(
        metadata, download_args, selected_filter_list, cleanup_filters, filter_func_dict
    )
    df = download_data(download_args)

    # Presence of COUNTRY column indicates the country-enriched dataset was used
    prefix = abbreviation_dict[download_args["protocol"]]
    country_col = f"{prefix}_COUNTRY"
    if download_args["countries"] or download_args["regions"]:
        assert country_col in df.columns
    else:
        assert country_col not in df.columns
    # Cleanup JSON
    os.remove(json_dir)
