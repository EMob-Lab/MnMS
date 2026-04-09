import os
import argparse
import pandas as pd
import numpy as np


# Function to analyze the path data from a DataFrame
def analyze_paths(df_paths):
    # Print the range of departure times
    print(f"First user departure time: {df_paths['TIME'].min()}")
    print(f"Last path departure time: {df_paths['TIME'].max()}")

    # Initialize counters
    total_paths = len(df_paths)
    paths_inf_cost = 0
    paths_not_defined = 0
    paths_inf_length = 0
    paths_services_not_defined = 0
    paths_path_not_chosen = 0

    # Iterate over each path entry to count issues
    for index, path in df_paths.iterrows():
        if path["COST"] == np.inf:  # Check for infinite cost
            paths_inf_cost = paths_inf_cost + 1
        if path["PATH"] == '':  # Check for missing path
            paths_not_defined = paths_not_defined + 1
        if path["LENGTH"] == np.inf:  # Check for infinite length
            paths_inf_length = paths_inf_length + 1
        if path["SERVICES"] == '':  # Check for undefined mobility services
            paths_services_not_defined = paths_services_not_defined + 1
        if path["CHOSEN"] == '':  # Check if a path was not chosen
            paths_path_not_chosen = paths_path_not_chosen + 1

    # Print summary statistics
    print(f"Total number of paths: {total_paths}")
    print(f"Number of users with a infinite path cost: {paths_inf_cost}")
    print(f"Number of users without path defined: {paths_not_defined}")
    print(f"Number of users with a infinite path length: {paths_inf_length}")
    print(f"Number of users without mobility services defined: {paths_services_not_defined}")
    print(f"Number of users without path chosen: {paths_path_not_chosen}")


# Function to load CSV file into a DataFrame
def extract_file(file):
    # Read the CSV using semicolon as separator, do not treat empty strings as NaN
    df = pd.read_csv(file, sep=';', keep_default_na=False)
    return df


# Helper function to validate that a path exists and is a file
def _path_file_type(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


# Main entry point of the script
if __name__ == "__main__":
    # Setup command-line argument parser
    parser = argparse.ArgumentParser(description="Analyze a CSV path output file for MnMS")
    parser.add_argument("path_file", type=_path_file_type, help="Path to the path output csv file")

    # Parse command-line arguments
    args = parser.parse_args()

    # Load path data and analyze it
    df_paths = extract_file(args.path_file)
    analyze_paths(df_paths)
