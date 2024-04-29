import random
from functools import partial
from scipy.optimize import minimize_scalar
import numpy as np



# Find the optimal price - max ib_i
def opt(bids: dict) -> float:
    """
    Finds the optimal price that maximizes revenue gained from bids received.

    Parameter:
    - bids (dict): Bidders and corresponding bids.

    Return:
    - Optimal sale price (float).
    """
    # Step 1: Sort bids in descending order
    sorted_bids = dict(sorted(bids.items(), key = lambda item: item[1], reverse = True))
    
    # Step 2: Calculate revenues based on each bid
    revenues = {bidder: (index + 1) * bid for index, (bidder, bid) in enumerate(sorted_bids.items())}

    # Step 3: Locate the maximum revenue according to the bidder
    max_bidder = max(revenues, key = revenues.get)

    # Step 4: Backtrack the optimal price
    price = bids[max_bidder]

    # Return
    return price



# Partition a dictionary
def dict_part(input_dict, random_seed, prop = 0.5):
    """
    Partitions a disctionary into two.

    Parameter:
    - input_dict (dict): Dictionary to be partitioned.
    - random_seed (int): A random seed for all pricing mechanisms to use the same partition.
    - prop (float): Proportion of items assigned to the first partition (default = 0.5).

    Returns:
    - New dictionary 1 (dict).
    - New dictionary 2 (dict).
    """
    keys = list(input_dict.keys())

    # Calculate the number of keys for the first partition
    dict1_size = int(len(keys) * prop)

    # Randomly sample keys for the first partition
    random.seed(random_seed) # to make sure all pricing mechanisms are compared based on the same bids partition
    dict1_keys = random.sample(keys, dict1_size)

    # Create the first partition
    dict1 = {key: input_dict[key] for key in dict1_keys}

    # Create the second partition with the remaining keys
    dict2 = {key: input_dict[key] for key in keys if key not in dict1_keys}

    return dict1, dict2



# Calculated the expected per capita revenue - p(1-F(p))
def get_epc_rev(price, *, value_cdf):
    """
    Calculates expected per capita revenue given the value cdf, i.e., p(1 - F(p)).

    Parameters:
    - price (float): Price charged to every buyer.

    Keyword Arguments
    - value_cdf (callable func): Cumulative distribution function of buyers' values.

    Return:
    - Function value (float).
    """
    return price * (1 - value_cdf(price))



# Find the maximum expected per capita revenue - max_p p(1-F(p))
def max_epc_rev(value_cdf, lower, upper):
    """
    Maximizes the expected per capita revenue, i.e., max_p p(1 - F(p)).

    Parameters:
    - value_pdf (callable func): Cumulative distribution function of buyers' values.
    - lower (float): Lower limit for bidder values and bids.
    - upper (float): Upper limit for bidder values and bids.

    Return:
    - Optimal price (maximum point) (float).
    - Optimal expected per capita revenue (maximum) (float).
    """
    # Step 1: Wrap get_epc_rev with the given value cdf and extra arguments if any
    wrapped_get_epc_rev = partial(get_epc_rev, value_cdf = value_cdf)

    # Step 2: Maximization
    results = minimize_scalar(lambda x: -wrapped_get_epc_rev(x), method='bounded', bounds = [(lower, upper)])
    price = results.x
    if price < lower or price > upper:
        raise ValueError("Optimal price found outside the common support!")
    revenue = -results.fun
    if revenue < 0:
        raise ValueError("Revenue can never be negative!")

    # Return
    return price, revenue 


