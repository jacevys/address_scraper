import multiprocessing
from functools import partial
from set_bcs_label import set_label_proc

def run_main_with_args(db_name, upper_bound, lower_bound, batch, get_label_method):
    set_label_proc(db_name, upper_bound, lower_bound, batch, get_label_method)

if __name__ == "__main__":
    # Define your databases and bounds here
    databases_and_bounds = [
        ("db1", 1000, 0, 100, "ai"),
        ("db2", 2000, 1000, 100, "misttrack"),
        # Add more as needed
    ]

    # Create a pool of workers
    with multiprocessing.Pool(processes=len(databases_and_bounds)) as pool:
        # Use partial to create a function with some arguments pre-filled
        func = partial(run_main_with_args, batch=100)  # Assuming batch size is constant for simplicity

        # Map databases_and_bounds to the worker function
        pool.starmap(func, databases_and_bounds)