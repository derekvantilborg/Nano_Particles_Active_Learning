"""
Evaluation functions.

Derek van Tilborg | 06-03-2023 | Eindhoven University of Technology

"""

import numpy as np
from nano.models import XGBoostEnsemble
from nano.utils import augment_data
import pandas as pd


def evaluate_model(x: np.ndarray, y: np.ndarray, id: np.ndarray, filename: str, hyperparameters: dict,
                   bootstrap: int = 10, n_folds: int = 5, ensemble_size=10, augment=5):
    """ Function to evaluate model performance through bootstrapped k-fold cross-validation"""

    # estimate model performance over b bootstraps
    y_hats, y_hats_uncertainty = [], []
    for b in range(bootstrap):
        y_hat, y_hat_uncertainty = k_fold_cross_validation(x, y, seed=b,
                                                           n_folds=n_folds,
                                                           ensemble_size=ensemble_size,
                                                           augment=augment,
                                                           **hyperparameters)
        y_hats.append(y_hat)
        y_hats_uncertainty.append(y_hat_uncertainty)

    # Take the mean over the bootstraps
    mean_y_hat = np.mean(y_hats, axis=0)
    mean_y_uncertainty = np.mean(y_hats_uncertainty, axis=0)

    # Put everything in a dataframe and save it somewhere
    df = pd.DataFrame({'ID': id,
                       'PLGA': x[:, 0],
                       'PP-L': x[:, 1],
                       'PP-COOH': x[:, 2],
                       'PP-NH2': x[:, 3],
                       'S/AS': x[:, 4],
                       'y': y,
                       'y_hat': mean_y_hat,
                       'y_uncertainty': mean_y_uncertainty})
    df.to_csv(filename)

    # calculate the RMSE
    rmse = calc_rmse(y, mean_y_hat)

    return df, rmse


def k_fold_cross_validation(x: np.ndarray, y: np.ndarray, n_folds: int = 5, ensemble_size: int = 10, seed: int = 42,
                            augment: int = False, **kwargs) -> (np.ndarray, np.ndarray):
    assert len(x) == len(y), f"x and y should contain the same number of samples x:{len(x)}, y:{len(y)}"

    y_hats, y_hats_uncertainty = np.zeros(y.shape), np.zeros(y.shape)

    rng = np.random.default_rng(seed)
    folds = rng.integers(low=0, high=n_folds, size=len(x))

    for i in range(n_folds):
        x_train, y_train = x[folds != i], y[folds != i]

        if augment:
            x_train, y_train = augment_data(x_train, y_train, n_times=augment, seed=seed)

        x_val, y_val = x[folds == i], y[folds == i]

        ensmbl = XGBoostEnsemble(ensemble_size=ensemble_size, **kwargs)
        ensmbl.train(x_train, y_train)

        y_hat, y_hat_mean, y_hat_uncertainty = ensmbl.predict(x_val)

        y_hats[folds == i] = y_hat_mean
        y_hats_uncertainty[folds == i] = y_hat_uncertainty

    return y_hats, y_hats_uncertainty


def calc_rmse(y: np.ndarray, y_hat: np.ndarray) -> float:
    """ Calculates the Root Mean Square Error """
    assert type(y) is np.ndarray and type(y_hat) is np.ndarray, 'y and y_hat should be Numpy Arrays'
    assert len(y) == len(y_hat), f"y and y_hat should contain the same number of samples y:{len(y)}, y_hat:{len(y_hat)}"

    return np.sqrt(np.mean(np.square(y - y_hat)))
