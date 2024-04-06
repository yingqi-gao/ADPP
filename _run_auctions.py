from _classes_initialization import OnlineAuctionRandomInitialization
from _classes_auction import TrainingData, Auction, DOPAuction, RSOPAuction, RSKDEAuction, RSRDEAuction
from math import floor
import warnings
import dill



def run_auctions(lock,
                 online_initialization: OnlineAuctionRandomInitialization, 
                 online_initialization_name: str,
                 pricing_mechanism: float) -> list[Auction]:
    # acquire the lock
    with lock:
        num_rounds = online_initialization.num_rounds
        common_upper = online_initialization.upper
        is_upper_floated = online_initialization.is_upper_floated

        sequence_auctions = []
        training_history = []
        for i in range(num_rounds): # Test: 110
            print(i)
            auction_initialization = online_initialization.sequence_auctions[i]

            if pricing_mechanism == "DOP":
                auction = DOPAuction(initialization = auction_initialization)
            elif pricing_mechanism == "RSOP":
                auction = RSOPAuction(initialization = auction_initialization)
            elif pricing_mechanism == "RSKDE":
                auction = RSKDEAuction(initialization = auction_initialization)

            elif pricing_mechanism.startswith("RSRDE"): 
                if i >= floor(num_rounds / 2):
                    method = pricing_mechanism.split("_")[1]
                    auction = RSRDEAuction(
                        initialization = auction_initialization, 
                        common_upper = common_upper,
                        is_upper_floated = is_upper_floated,
                        training_history = training_history,
                        RSRDE_method = method
                    )
                else:
                    auction = None
                
                bids_list =  [*auction_initialization.bids.values()]
                training_data = TrainingData(observations = bids_list)
                training_history.append(training_data)
            
            sequence_auctions.append(auction)

            if i % 10 == 9:
                file_name = online_initialization_name + "_" + pricing_mechanism
                with open("data/" + file_name + ".pkl", "wb") as file:
                    dill.dump(sequence_auctions, file)
                print(f"Round {i + 1} of {file_name} done!")
            
        print("--------------------")
        print(f"All done with {pricing_mechanism} on {online_initialization_name}!")