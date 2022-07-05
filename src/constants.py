protocols = {
    "Mosquito Habitat Mapper": "mosquito_habitat_mapper",
    "Land Cover": "land_covers",
}


date_fmt = "%Y-%m-%d"

data_keys = [
    "protocol",
    "start_date",
    "end_date",
    "countries",
    "regions",
    "selected_filters",
    "selected_filter_types",
]

default_cleanup_dict = {
    "poor_geolocation_filter": False,
    "valid_coords_filter": False,
    "duplicate_filter": False,
    "duplicate_filter_cols": [],
    "duplicate_filter_size": 2,
}
