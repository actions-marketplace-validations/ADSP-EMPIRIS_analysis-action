from dotenv import load_dotenv
import os
from supabase import create_client, Client
import json
import numpy as np
from scipy.stats import wilcoxon

# Load environment variables from .env file
load_dotenv()

# Get Supabase URL and Key from environment variables
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Create Supabase client
supabase: Client = create_client(supabase_url, supabase_key)


def bootstrap_analysis(data, n_bootstrap=10000, confidence_level=0.99):
    bootstrap_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=len(data), replace=True)
        bootstrap_means.append(np.mean(sample))
    alpha = 100 - confidence_level * 100
    confidence_interval = np.percentile(bootstrap_means, [alpha / 2, 100 - alpha / 2])
    return np.mean(bootstrap_means), confidence_interval


def wilcoxon_test(data1, data2):
    stat, p = wilcoxon(data1, data2, zero_method="wilcox", correction=False, alternative="two-sided", method="auto")
    return stat, p


def insert_analysis_results(run_id, user_id, app_name, bootstrap_mean, bootstrap_ci, wilcoxon_stat, wilcoxon_p):
    result = supabase.table('analysis_results').insert({
        'run_id': run_id,  # Add the run_id to the database record
        'user_id': user_id,
        'app_name': app_name,
        'bootstrap_mean': bootstrap_mean,
        'bootstrap_ci_low': bootstrap_ci[0],
        'bootstrap_ci_high': bootstrap_ci[1],
        'wilcoxon_stat': wilcoxon_stat,
        'wilcoxon_p': wilcoxon_p
    }).execute()

    if result.error:
        print(f"Error updating database: {result.error}")
    else:
        print(f"Database updated successfully for run ID: {run_id}.")


def fetch_data_and_analyze(api_key, app_name):
    # Query the api_keys table to get user_id
    user_data = supabase.table('apikeys').select('user_id').eq('key_id', api_key).execute()

    # Extract user_id
    user_id = user_data.data[0]['user_id'] if user_data.data else None

    if not user_id:
        return "User ID not found for the given API key."

    # Query the experiment_run table for data specific to this user
    experiment_data = supabase.table('experiment_run').select('*').eq('user_id', user_id).execute()

    if not experiment_data.data:
        return "No data found for the user."

    for entry in experiment_data.data:
        # Filter based on app_name and prepare data for analysis
        if any(app_name == item[1] for item in entry.get('general_data', []) if
               len(item) >= 2 and item[0] == "Application name"):
            run_id = entry['id']
            latencies = [d['Latency'] for d in entry.get('data', [])]

            # Perform analysis if latencies data is present
            if latencies:
                bootstrap_mean, bootstrap_ci = bootstrap_analysis(latencies)
                wilcoxon_stat, wilcoxon_p = wilcoxon_test(latencies[:len(latencies) // 2],
                                                          latencies[len(latencies) // 2:])
                insert_analysis_results(run_id, user_id, app_name, bootstrap_mean, bootstrap_ci, wilcoxon_stat,
                                        wilcoxon_p)
            else:
                print(f"No latency data found for run ID: {run_id}.")


api_key = 'key_9dWvLH5RNrUi7kkruwBpZz'
app_name = "App1"
result = fetch_data_and_analyze(api_key, app_name)


# Check if result is a string (indicating an error) or a list (run ids)
if isinstance(result, str):
    print(result)
else:
    pretty_json_output = json.dumps(result, indent=4)
    print(pretty_json_output)
