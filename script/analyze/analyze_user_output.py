import os
import argparse
import pandas as pd


# Function to analyze user data from the DataFrame
def analyze_users(df_users):
    # Display the earliest and latest activity times
    print(f"First user activity time: {df_users['TIME'].min()}")
    print(f"Last user activity time: {df_users['TIME'].max()}")

    # Initialize counters
    users_without_link = 0
    users_without_position = 0
    users_deadend = 0
    users_arrived = 0

    # Iterate over each user row to analyze their state
    for index, user in df_users.iterrows():
        if user["LINK"] == '':
            users_without_link = users_without_link + 1
        if user["POSITION"] == '':
            users_without_position = users_without_position + 1
        if user["STATE"] == "DEADEND":
            users_deadend = users_deadend + 1
        if user["STATE"] == "ARRIVED":
            users_arrived = users_arrived + 1

    # Print summary statistics
    print(f"Number of users without link: {users_without_link}")
    print(f"Number of users without position: {users_without_position}")
    print(f"Number of users in deadend state: {users_deadend}")
    print(f"Number of users arrived to destination: {users_arrived}")


# Function to load the CSV file into a DataFrame
def extract_file(file):
    # Read CSV file using semicolon as delimiter and treat empty strings as valid values
    df = pd.read_csv(file, sep=';', keep_default_na=False)
    return df


# Helper function to validate the file path argument
def _path_file_type(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


# Entry point when script is run directly
if __name__ == "__main__":
    # Set up argument parser for command-line usage
    parser = argparse.ArgumentParser(description="Analyze a CSV user output file for MnMS")
    parser.add_argument("user_file", type=_path_file_type, help="Path to the user output csv file")

    # Parse arguments
    args = parser.parse_args()

    # Load CSV data and analyze it
    df_users = extract_file(args.user_file)
    analyze_users(df_users)
