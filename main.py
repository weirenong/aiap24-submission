# Standard library imports
import logging
import sqlite3

# Third-party imports
import pandas as pd
import yaml
from imblearn.under_sampling import RandomUnderSampler
from imblearn.over_sampling import RandomOverSampler
from sklearn.utils._testing import ignore_warnings

# Local application/library specific imports
from src.data_preparation import DataPreparation
from src.model_training import ModelTraining

logging.basicConfig(level=logging.INFO)


@ignore_warnings(category=Warning)
def main():

    # Configuration file path
    config_path = "./src/config.yaml"

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    # Connect to SQLite database and load both tables
    logging.info(f"Connecting to database: {config['file_path']}")
    conn = sqlite3.connect(config["file_path"])

    df_deliveries = pd.read_sql_query("SELECT * FROM deliveries", conn)
    logging.info(f"Deliveries table shape: {df_deliveries.shape}")

    df_feedback = pd.read_sql_query("SELECT * FROM feedback", conn)
    logging.info(f"Feedback table shape: {df_feedback.shape}")

    conn.close()

    # Merge on delivery_id — inner join to keep only rows present in both tables
    df = df_feedback.merge(df_deliveries, on="delivery_id", how="inner")
    logging.info(f"Merged DataFrame shape: {df.shape}")

    # Initialize and run data preparation
    data_prep = DataPreparation(config)
    cleaned_df = data_prep.clean_data(df)

    # Initialize model training with the created preprocessor
    model_training = ModelTraining(config, data_prep.preprocessor)

    # Split the data (stratified to preserve class distribution across imbalanced ratings)
    X_train, X_val, X_test, y_train, y_val, y_test = model_training.split_data(
        cleaned_df
    )

    # Resample training data to address class imbalance:
    # Step 1 — undersample majority classes (4.0 and 5.0) down to 4000 rows each
    current_counts = y_train.value_counts()
    under_strategy = {
        5.0: 4000,
        4.0: 4000,
        3.0: current_counts.get(3.0, 0),
        2.0: current_counts.get(2.0, 0),
        1.0: current_counts.get(1.0, 0),
    }
    rus = RandomUnderSampler(sampling_strategy=under_strategy, random_state=42)
    X_train_under, y_train_under = rus.fit_resample(X_train, y_train)

    # Step 2 — oversample minority classes (1.0, 2.0, 3.0) up to 4000 rows each
    over_strategy = {5.0: 4000, 4.0: 4000, 3.0: 4000, 2.0: 4000, 1.0: 4000}
    ros = RandomOverSampler(sampling_strategy=over_strategy, random_state=42)
    X_train_resampled, y_train_resampled = ros.fit_resample(X_train_under, y_train_under)

    logging.info(f"Resampled training set shape: {X_train_resampled.shape}")
    logging.info(f"Resampled class distribution:\n{y_train_resampled.value_counts().sort_index()}")

    # Train and evaluate baseline models with default hyperparameters
    baseline_models, baseline_metrics = (
        model_training.train_and_evaluate_baseline_models(
            X_train_resampled, y_train_resampled, X_val, y_val
        )
    )

    # Train and evaluate tuned models with hyperparameter tuning
    tuned_models, tuned_metrics = model_training.train_and_evaluate_tuned_models(
        X_train_resampled, y_train_resampled, X_val, y_val
    )

    # Combine all models and their metrics into dictionaries
    all_models = {**baseline_models, **tuned_models}
    all_metrics = {**baseline_metrics, **tuned_metrics}

    # Find the best model based on F1 Score (macro-averaged classification metric)
    best_model_name = max(all_metrics, key=lambda k: all_metrics[k]["F1 Score"])
    best_model = all_models[best_model_name]
    logging.info(f"Best Model Found: {best_model_name}")

    # Evaluate the best model on the held-out test set
    final_metrics = model_training.evaluate_final_model(
        best_model, X_test, y_test, best_model_name
    )


if __name__ == "__main__":
    main()