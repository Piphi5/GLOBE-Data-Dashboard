import base64
import numpy as np


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
