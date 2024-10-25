from random import uniform
import scipy.stats as stats
from _price_optimization import kde, rde, ecdf, get_optimals, get_ideals
import numpy as np


def simulate_value_dists(N, dist_name, lower, upper):
    """
    Generate N value distributions drawn from a specified distribution type ("truncnorm", "truncexpon", or "truncpareto") with a common support (lower, upper).

    Args:
        N (int): An integer specifying the number of distributions to be generated.
        dist_name (str): The name of the distributions. Options include "truncnorm", "truncexpon", and "truncpareto".
        lower (float): A numeric value specifying the lower bound of the common support of the distributions.
        upper (float): A numeric value specifying the upper bound of the common support of the distributions.

    Returns:
        list of dict: A list where each dictionary contains the parameters of one distribution.
    """
    if dist_name == "truncnorm":
        params_list = [
            {
                "a": lower,
                "b": upper,
                "loc": uniform(0, 2*upper),
                    "scale": uniform(0, 2*upper)
            }
        for _ in range(N)
        ]

    elif dist_name == "truncexpon":
        params_list = []
        for _ in range(N):
            params = {"loc": lower, "scale": uniform(0, 2 * upper)}
            params["b"] = (upper - lower) / params["scale"]
            params_list.append(params)

    elif dist_name == "truncpareto":
        params_list = []
        for _ in range(N):
            params = {"b": uniform(2, upper), "scale": uniform(0, 2 * upper)}
            params["loc"] = lower - params["scale"]
            params["c"] = (upper - params["loc"]) / params["scale"]
            params_list.append(params)

    return params_list


def simulate_bids(dist_name, lower, upper, max_N = 200, max_n = 200, max_N_train = 200, max_n_train = 200):
    """
    Generate bids (or values) from each value distribution in a specified list.

    Args:
        dist_name (str): The name of the distributions. Options include "truncnorm", "truncexpon", and "truncpareto".
        lower (float): A numeric value specifying the lower bound of the common support of the distributions.
        upper (float): A numeric value specifying the upper bound of the common support of the distributions.
        params_list (list of dict): A list where each element is a dictionary containing the parameters for one application of the distribution.
        max_N (int, optional): An integer specifying the maximum number of auction rounds to generate for tetsing. Defaults to 200.
        max_n (int, optional): An integer specifying the maximum number of bids to generate for testing. Defaults to 200.
        max_N_train (int, optional): An integer specifying the maximum number of auction rounds to generate for training the RDE method. Defaults to 200.
        max_n_train (int, optional): An integer specifying the maximum number of bids  to generate for training the RDE method. Defaults to 200.

    Returns:
        dict: A dictionary that contains:
            - dist_name (str): The name of the distributions.
            - lower (float): A numeric value specifying the lower bound of the common support of the distributions.
            - upper (float): A numeric value specifying the upper bound of the common support of the distributions.
            - params_list (list of dict): A list where each element is a dictionary containing the parameters for one application of the distribution.
            - bids (numpy.ndarray): An array of max_N rows, each of which contains max_n bids generated for testing.
            - train_bids (numpy.ndarray): A array of max_N_train rows, each of which contains max_n_train bids generated for training the RDE method.
            - ideals (list of tuples): A list of tuples, each of which contains the ideal price and the ideal expected per capita revenue.
    """
    results = {"dist_name": dist_name, "lower": lower, "upper": upper}

    # Step 1: Generate two lists of parameters for training and testing, respectively.
    train_params_list = simulate_value_dists(max_N_train, dist_name, lower, upper)
    params_list = simulate_value_dists(max_N, dist_name, lower, upper)
    results["params_list"] = params_list

    # Step 2: Get the distribution function from scipy.stats based on dist_name.
    dist_func = getattr(stats, dist_name, None)
    if dist_func is None:
        raise ValueError(f"Distribution '{dist_name}' not found in scipy.stats")

    # Step 3: Generate bids according to the list of parameters.
    results["bids"] = np.array([dist_func.rvs(**params, size=max_n) for params in params_list])
    results["train_bids"] = np.array([dist_func.rvs(**params, size=max_n_train) for params in train_params_list])

    # Step 4: Calculate the ideal price and the ideal expected per capita revenue according to the list of parameters.
    results["ideals"] = get_ideals(dist_name, lower, upper, params_list)

    # Return the dictionary
    return results


def simulate_regrets(bids_dict, method, N, n, N_train = None, n_train = None):
    """
    Simulate N rounds of auctions. Each aution receives n bids. Apply the Max-Price ADPP mechanism with an initial auction using eCDF, KDE, or RDE to estimate the optimal price, and compute the regret.

    Args:
        bids_dict (dict): A dictionary that contains:
                            - dist_name (str): The name of the distributions.
                            - lower (float): A numeric value specifying the lower bound of the common support of the distributions.
                            - upper (float): A numeric value specifying the upper bound of the common support of the distributions.
                            - params_list (list of dict): A list where each element is a dictionary containing the parameters for one application of the distribution.
                            - bids (numpy.ndarray): An array of max_N rows, each of which contains max_n bids generated for testing.
                            - train_bids (numpy.ndarray): A array of max_N_train rows, each of which contains max_n_train bids generated for training the RDE method.
                            - ideals (list of tuples): A list of tuples, each of which contains the ideal price and the ideal expected per capita revenue.
        method (str): The method of the initial auction to be used for price optimization. Options include "ecdf", "kde", and "rde".
        N (int): An integer specifying the number of auction rounds to be generated.
        n (int): An integer specifying the number of bids received at each auction round.
        N_train (int, optional): An integer specifying the number of past auction rounds available for training with the RDE method.
        n_train (int, optional): An integer specifying the number of bids received at each past auction round for training with the RDE method.

    Returns:
        list: A list of regrets involved in the N rounds of auctions.
    """
    regrets = []

    # Step 1: Extract the parameters to be used.
    samples = bids_dict["bids"][:N, :n]
    lower = bids_dict["lower"]
    upper = bids_dict["upper"]

    # Step 2: Construct the CDFs using the specified method.
    if method == "ecdf":
        cdfs = ecdf(samples)
    elif method == "kde":
        cdfs = kde(samples, lower, upper)
    elif method == "rde":
        train_samples = bids_dict["train_bids"][:N_train, :n_train]
        cdfs = rde(train_samples, samples, lower, upper)
    else:
        raise ValueError(f"Method '{method}' not supported.")

    # Step 3: Calculate the optimal prices and the corresponding expected per capita revenues.
    optimals = get_optimals(
        cdfs,
        bids_dict["dist_name"],
        lower,
        upper,
        bids_dict["params_list"][:N]
    )

    # Step 4: Calculate the regrets.
    optimal_revenues = [optimal[1] for optimal in optimals]
    ideal_revenues = [ideal[1] for ideal in bids_dict["ideals"]]
    regrets = [ideal_revenues[i] - optimal_revenues[i] for i in range(N)]

    # Return the list of regrets.
    return regrets


if __name__ == "__main__":
    print("running tests...")
    from random import randrange

    # test simulate_value_dists
    params_list = simulate_value_dists(N=200, dist_name="truncnorm", lower=1, upper=10)
    print(params_list[randrange(200)])
    params_list = simulate_value_dists(N=200, dist_name="truncexpon", lower=1, upper=10)
    print(params_list[randrange(200)])
    params_list = simulate_value_dists(
        N=200, dist_name="truncpareto", lower=1, upper=10
    )
    print(params_list[randrange(200)])

    # test simulate_bids
    bids_dict = simulate_bids(
        "truncnorm",
        lower=1,
        upper=10,
        max_N=200,
        max_n=200,
        max_N_train=200,
        max_n_train=200,
    )
    print(bids_dict["dist_name"])
    print(bids_dict["lower"])
    print(bids_dict["upper"])
    print(bids_dict["params_list"][randrange(200)])
    print(bids_dict["bids"][randrange(200)])
    print(bids_dict["train_bids"][randrange(200)])
    print(bids_dict["ideals"][randrange(200)])
    bids_dict = simulate_bids(
        "truncexpon",
        lower=1,
        upper=10,
        max_N=200,
        max_n=200,
        max_N_train=200,
        max_n_train=200,
    )
    print(bids_dict["dist_name"])
    print(bids_dict["lower"])
    print(bids_dict["upper"])
    print(bids_dict["params_list"][randrange(200)])
    print(bids_dict["bids"][randrange(200)])
    print(bids_dict["train_bids"][randrange(200)])
    print(bids_dict["ideals"][randrange(200)])
    bids_dict = simulate_bids(
        "truncpareto",
        lower=1,
        upper=10,
        max_N=200,
        max_n=200,
        max_N_train=200,
        max_n_train=200,
    )
    print(bids_dict["dist_name"])
    print(bids_dict["lower"])
    print(bids_dict["upper"])
    print(bids_dict["params_list"][randrange(200)])
    print(bids_dict["bids"][randrange(200)])
    print(bids_dict["train_bids"][randrange(200)])
    print(bids_dict["ideals"][randrange(200)])

    # test simulate_regrets
    results = simulate_regrets(
        bids_dict, "ecdf", N=100, n=10, N_train=None, n_train=None
    )
    print(results[randrange(100)])
    results = simulate_regrets(
        bids_dict, "kde", N=100, n=10, N_train=None, n_train=None
    )
    print(results[randrange(100)])
    results = simulate_regrets(
        bids_dict, "rde", N=100, n=10, N_train=100, n_train=100
    )
    print(results[randrange(100)])


