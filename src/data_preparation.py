# Standard library imports
import logging
from typing import Any, Dict

# Related third-party imports
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler


class DataPreparation:
    """
    A class used to clean and preprocess delivery rating data.

    The raw data comes from two merged SQLite tables (deliveries + feedback).
    Cleaning follows the EDA logic: type coercions, categorical fixes,
    negative-value handling, driver experience imputation, feature engineering,
    column selection, and preprocessor construction.

    Attributes:
    -----------
    config : Dict[str, Any]
        Configuration dictionary containing feature lists and the target column.
    preprocessor : sklearn.compose.ColumnTransformer
        A preprocessor pipeline for transforming numerical, nominal, ordinal,
        and passthrough features.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the DataPreparation class with a configuration dictionary.

        Args:
        -----
        config (Dict[str, Any]): Configuration dictionary containing feature lists
            and target column name.
        """
        self.config = config
        self.preprocessor = self._create_preprocessor()

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the merged deliveries+feedback DataFrame following EDA logic.

        Steps performed:
          1. Fix inconsistent categorical string values (branch, parcel_category, vehicle_type).
          2. Coerce numeric columns stored as objects.
          3. Parse datetime columns.
          4. Drop delivery_id duplicates (keep first).
          5. Drop rows where the target (rating) is null.
          6. Drop columns not useful for modelling (comment, recipient_postal_code, id columns).
          7. Replace negative numeric values with NaN, then drop rows missing
             parcel_weight_kg, parcel_value_sgd, num_stops_on_route, payment_method, vehicle_type.
          8. Impute null/negative driver_experience_months from same driver_id; drop remaining nulls.
          9. Engineer features: delivery_hour_before_midnight, pickup_hour_before_midnight
             (and intermediate datetime-derived features used to derive them).
         10. Select only the columns declared in config.

        Args:
        -----
        df (pd.DataFrame): The merged raw DataFrame.

        Returns:
        --------
        pd.DataFrame: The cleaned and feature-engineered DataFrame.
        """
        logging.info("Starting data cleaning.")
        df_cleaned = df.copy()

        # Fix inconsistent categorical string values
        df_cleaned["branch"] = df_cleaned["branch"].replace(
            {"EAST": "East", "Cnetral": "Central", "west ": "West", "Noth": "North"}
        )
        df_cleaned["parcel_category"] = df_cleaned["parcel_category"].replace(
            {
                "Fragile ": "fragile",
                "Standard": "standard",
                "over-sized": "oversized",
                "refrig.": "refrigerated",
            }
        )
        df_cleaned["vehicle_type"] = df_cleaned["vehicle_type"].replace(
            {"VAN": "van", "Bike": "bike", "truck ": "truck"}
        )

        # Coerce numeric columns from object dtype
        for col in ["parcel_weight_kg", "parcel_value_sgd", "num_stops_on_route",
                    "driver_experience_months"]:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors="coerce")

        # Parse datetime columns
        datetime_cols = [
            "booking_datetime",
            "pickup_datetime",
            "feedback_datetime",
            "promised_delivery_datetime",
            "delivery_datetime",
        ]
        for col in datetime_cols:
            df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors="coerce")

        # Drop delivery_id duplicates; keep first (assumed correct entry)
        df_cleaned = df_cleaned.sort_index()
        df_cleaned = df_cleaned.drop_duplicates(subset="delivery_id", keep="first")
        logging.info(f"Shape after dropping delivery_id duplicates: {df_cleaned.shape}")

        # Drop rows where target (rating) is null
        df_cleaned = df_cleaned.dropna(subset=["rating"])
        logging.info(f"Shape after dropping null ratings: {df_cleaned.shape}")

        # Drop columns not used for modelling
        cols_to_drop = ["comment", "recipient_postal_code"]
        # Also drop any id columns present that are not needed downstream
        id_cols = [c for c in df_cleaned.columns if c.endswith("_id")]
        cols_to_drop += id_cols
        df_cleaned = df_cleaned.drop(
            columns=[c for c in cols_to_drop if c in df_cleaned.columns]
        )

        # Negative replace with NaN, then drop rows missing critical columns
        for col in ["parcel_weight_kg", "parcel_value_sgd", "num_stops_on_route"]:
            df_cleaned[col] = df_cleaned[col].apply(
                lambda x: np.nan if pd.notna(x) and x < 0 else x
            )
        df_cleaned = df_cleaned.dropna(
            subset=["parcel_weight_kg", "parcel_value_sgd", "num_stops_on_route",
                    "payment_method", "vehicle_type"]
        )
        logging.info(f"Shape after dropping rows with missing critical fields: {df_cleaned.shape}")

        # Impute driver_experience_months
        # Negative values are treated as missing
        df_cleaned["driver_experience_months"] = df_cleaned[
            "driver_experience_months"
        ].apply(lambda x: np.nan if pd.notna(x) and x < 0 else x)

        logging.info(
            f"Null driver_experience_months before imputation: "
            f"{df_cleaned['driver_experience_months'].isnull().sum()}"
        )
        # Re-attach driver_id from the original df for groupby imputation if it was dropped
        # (driver_id is dropped in step 6 but we need it here — so we impute before dropping)
        # NOTE: driver_id is added back temporarily via the original merged df; the column
        # was present in df so it survives until we explicitly dropped it above.
        # Re-read driver_id from the original df by index alignment.
        if "driver_id" not in df_cleaned.columns:
            df_cleaned = df_cleaned.join(
                df[["driver_id"]].reindex(df_cleaned.index), how="left"
            )

        driver_exp_map = df_cleaned.groupby("driver_id")["driver_experience_months"].transform("mean")
        df_cleaned["driver_experience_months"] = df_cleaned[
            "driver_experience_months"
        ].fillna(driver_exp_map)
        df_cleaned = df_cleaned.dropna(subset=["driver_experience_months"])

        logging.info(
            f"Null driver_experience_months after imputation: "
            f"{df_cleaned['driver_experience_months'].isnull().sum()}"
        )

        # Now drop driver_id (and any remaining id cols not already removed)
        df_cleaned = df_cleaned.drop(
            columns=[c for c in ["driver_id"] if c in df_cleaned.columns]
        )
        logging.info(f"Shape after driver_experience_months imputation: {df_cleaned.shape}")

        # Feature engineering
        # Intermediate features used to derive the final passthrough features
        df_cleaned["delivery_day_of_week"] = df_cleaned["promised_delivery_datetime"].dt.dayofweek
        df_cleaned["delivery_hour"] = df_cleaned["promised_delivery_datetime"].dt.hour
        df_cleaned["pickup_hour"] = df_cleaned["pickup_datetime"].dt.hour

        # Final passthrough binary features (combined after-midnight indicator)
        # Hours 0–3 are considered after midnight; hours 4–23 are before midnight
        df_cleaned["delivery_hour_before_midnight"] = (
            df_cleaned["delivery_hour"] >= 4
        ).astype(int)
        df_cleaned["pickup_hour_before_midnight"] = (
            df_cleaned["pickup_hour"] >= 4
        ).astype(int)

        # Select only columns declared in config
        keep_cols = (
            self.config["numerical_features"]
            + self.config["nominal_features"]
            + self.config["ordinal_features"]
            + self.config["passthrough_features"]
            + [self.config["target_column"]]
        )
        df_cleaned = df_cleaned[[c for c in keep_cols if c in df_cleaned.columns]]

        logging.info(f"Final cleaned DataFrame shape: {df_cleaned.shape}")
        logging.info("Data cleaning completed.")
        return df_cleaned

    def _create_preprocessor(self) -> ColumnTransformer:
        """
        Creates a preprocessor pipeline matching the EDA feature encoding choices:
          - Numerical: StandardScaler
          - Nominal: OneHotEncoder (drop='first', handle_unknown='ignore')
          - Ordinal: OrdinalEncoder with explicit category order for delivery_priority
          - Passthrough: binary integer features passed through unchanged

        Returns:
        --------
        sklearn.compose.ColumnTransformer
        """
        numerical_transformer = Pipeline(steps=[("scaler", StandardScaler())])

        nominal_transformer = Pipeline(
            steps=[("onehot", OneHotEncoder(drop="first", handle_unknown="ignore"))]
        )

        # delivery_priority has a meaningful order: Standard < Express < Premium < VIP
        delivery_priority_categories = ["Standard", "Express", "Premium", "VIP"]
        ordinal_transformer = Pipeline(
            steps=[
                (
                    "ordinal",
                    OrdinalEncoder(
                        categories=[delivery_priority_categories],
                        handle_unknown="use_encoded_value",
                        unknown_value=-1,
                    ),
                )
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numerical_transformer, self.config["numerical_features"]),
                ("nom", nominal_transformer, self.config["nominal_features"]),
                ("ord", ordinal_transformer, self.config["ordinal_features"]),
                ("pass", "passthrough", self.config["passthrough_features"]),
            ],
            remainder="drop",  # drop anything not explicitly listed
            n_jobs=-1,
        )
        return preprocessor