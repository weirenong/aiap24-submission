# Delivery Rating Prediction

## Project Description

This project implements a machine learning pipeline to predict customer delivery ratings (1–5 stars) to help the company assign deliveries to the best-suited drivers and achieve better overall ratings. The pipeline covers data ingestion from a SQLite database, data cleaning, feature engineering, resampling to handle class imbalance, model training, hyperparameter tuning, and final evaluation.

---

## Prerequisites and Installation Instructions

### Requirements

* Anaconda or Miniconda
* Python 3.11
* Required packages listed in `requirements.txt`

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-folder>
```

2. Create and activate a conda environment:
```bash
conda create -n aiapenv python=3.11
conda activate aiapenv
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

---

## Instructions for Executing the Pipeline

To run the complete pipeline, execute:

```bash
bash run.sh
```

Or directly:

```bash
python main.py
```

---

## Description of Logical Steps/Flow of the Pipeline

### Logical Flow of the Pipeline

The main script orchestrates the entire pipeline by:

* Loading configuration and connecting to the SQLite database
* Merging the two source tables into a single DataFrame
* Running data preparation and feature engineering
* Resampling the training set to address class imbalance
* Training baseline and hyperparameter-tuned models
* Selecting and evaluating the best model on the held-out test set

### 1. Configuration (`config.yaml`)

The pipeline loads configuration from `src/config.yaml`, which specifies:

* SQLite database file path
* Target column name (`rating`)
* Feature categorisation (numerical, nominal, ordinal, passthrough)
* Train/validation/test split ratios
* Hyperparameter grids for model tuning
* Cross-validation folds and scoring metric

### 2. Data Ingestion (`main.py`)

The raw data is stored across two SQLite tables:

* `deliveries` — operational delivery records (route, driver, parcel, timing)
* `feedback` — customer ratings and comments per delivery

Both tables are read via `sqlite3` and inner-joined on `delivery_id`, retaining only rows present in both tables. This produces a merged DataFrame of 55,267 rows and 22 columns as the starting point for cleaning.

### 3. Data Preparation (`DataPreparation` class)

The `DataPreparation` class handles all cleaning and feature engineering:

**Cleaning:**
* Fix inconsistent string values in `branch` (e.g. `"Cnetral"` → `"Central"`), `parcel_category` (e.g. `"Fragile "` → `"fragile"`), and `vehicle_type` (e.g. `"VAN"` → `"van"`)
* Coerce `parcel_weight_kg`, `parcel_value_sgd`, `num_stops_on_route`, `driver_experience_months` from object to numeric
* Parse all datetime columns (`booking_datetime`, `pickup_datetime`, `feedback_datetime`, `promised_delivery_datetime`, `delivery_datetime`)
* Drop `delivery_id` duplicates, keeping the first occurrence as the assumed correct entry
* Drop rows where `rating` is null, as the target cannot be imputed
* Drop `comment` (free-text, too inconsistent for modelling) and `recipient_postal_code` (reserved for future route-distance features using map APIs)
* Replace negative values in `parcel_weight_kg`, `parcel_value_sgd`, `num_stops_on_route` with NaN, then drop rows missing any of those or `payment_method` / `vehicle_type`, as no reliable imputation exists for these fields
* For `driver_experience_months`, replace negatives with NaN, impute using the mean of other entries sharing the same `driver_id`, and drop any remaining nulls
* Drop all id columns as they do not contribute to model training

**Feature Engineering:**
* `delivery_hour` — hour extracted from `promised_delivery_datetime`
* `pickup_hour` — hour extracted from `pickup_datetime`
* `delivery_hour_before_midnight` — binary flag: 1 if delivery hour ≥ 4 (daytime/evening), 0 if after midnight (hours 0–3). Bivariate analysis showed a pronounced spike in low ratings for after-midnight deliveries, so this binary split captures the operational risk without inflating dimensionality
* `pickup_hour_before_midnight` — same logic applied to pickup hour

**Column selection:** the DataFrame is filtered to retain only the columns declared in `config.yaml` plus the target, dropping everything else before training.

### 4. Resampling (`main.py`)

The rating distribution is heavily left-skewed: ratings 5 and 4 account for the bulk of the data (22,555 and 12,160 respectively), while ratings 1, 2, and 3 are rare (1,204, 1,654, and 3,281). To prevent the model from ignoring minority classes, a two-step resampling strategy is applied **to the training set only** — the validation and test sets are left untouched to reflect real-world distribution:

1. **Under-sampling** — majority classes (4 and 5) are downsampled to 4,000 rows each using `RandomUnderSampler`
2. **Over-sampling** — minority classes (1, 2, 3) are upsampled to 4,000 rows each using `RandomOverSampler`

The result is a perfectly balanced training set of 20,000 rows (4,000 per class).

Stratified splitting is also used when creating the val/test sets to ensure each retains a proportional representation of all rating classes.

### 5. Model Training (`ModelTraining` class)

The `ModelTraining` class manages:

* Splitting cleaned data into training (80%), validation (10%), and test (10%) sets with stratification
* Training three baseline classifiers with default hyperparameters: Decision Tree, Random Forest, and K-Nearest Neighbors
* Hyperparameter tuning via `GridSearchCV` (5-fold CV, scoring on macro F1) across the same three model families
* Evaluating all models on the validation set using Accuracy, Precision, Recall, F1 Score, and ROC AUC (all macro-averaged)
* Selecting the best overall model by macro F1 score and evaluating it on the held-out test set

### 6. Preprocessing Pipeline (`DataPreparation._create_preprocessor`)

A `ColumnTransformer` is constructed with:

* **Numerical** (`StandardScaler`): `num_stops_on_route`, `driver_experience_months`, `distance_km`
* **Nominal** (`OneHotEncoder`, `drop='first'`): `parcel_category`, `branch`
* **Ordinal** (`OrdinalEncoder`, categories `Standard < Express < Premium < VIP`): `delivery_priority`
* **Passthrough** (no transformation): `delivery_hour_before_midnight`, `pickup_hour_before_midnight`
* `remainder='drop'` — any column not explicitly listed is excluded from the model

---

## Overview of Key Findings from EDA

### Target Variable Characteristics

The target `rating` is a discrete 1–5 star score and is heavily imbalanced:

| Rating | Count  |
|--------|--------|
| 5      | 22,555 |
| 4      | 12,160 |
| 3      |  3,281 |
| 2      |  1,654 |
| 1      |  1,204 |

The long left tail means models trained on raw data will systematically underpredict low ratings, making resampling essential.

### Key Predictors of Delivery Rating

**Strong operational risk factors (clear trends in bivariate analysis):**
- **Driver experience** — the strongest individual signal (Spearman ρ = 0.22). Drivers with 0–12 months experience generate the largest share of 1–3 star ratings; the 5-star proportion grows steadily with tenure, peaking at 60+ months
- **Number of stops on route** — second strongest (ρ = −0.10). A linear relationship exists between route density and lower ratings; overloading routes directly harms customer satisfaction
- **Distance** — moderate negative correlation (ρ ≈ −0.08). Short-haul trips (0–5 km, 6–10 km) are dominated by 5-star ratings; the low-rating bands expand as distance increases towards 26–30 km
- **Delivery hour** — late-night and early-morning deliveries (after midnight) show a pronounced spike in 1 and 2-star ratings; afternoon deliveries are the most stable

**Minor variance-contributing features:**
- **Branch** — Central branch has the highest 5-star ratio; East branch shows the largest share of 1–3 star ratings
- **Parcel category** — fragile and oversized items attract proportionally more low ratings than standard parcels, reflecting the execution difficulty of handling specialist cargo
- **Delivery priority** — VIP and Express orders show wider bands of 3 and 4-star ratings, likely because high-paying customers have stricter expectations

### Features Excluded from Model Training

| Feature | Reason for Exclusion |
|---------|----------------------|
| `payment_method` | Rating proportion virtually identical between prepaid and COD |
| `delivery_day_of_week` / `is_weekend` | Star distribution perfectly flat across all days; weekend operations show no structural rating degradation |
| `is_peak_hour` | Near-identical rating distributions inside and outside peak hours; congestion appears successfully absorbed by drivers |
| `parcel_weight_kg` / `parcel_value_sgd` | Rating stacks uniformly flat across all weight and value brackets |
| `vehicle_type` | Uniform rating distribution across van, bike, and truck |
| `comment` | Free-text with no consistent format; unsuitable for encoding and likely to introduce noise |
| `recipient_postal_code` | Reserved for a future iteration using map API route distances |
| All id columns | No predictive value; serve as row identifiers only |

Spearman correlation was used over Pearson because the target is a discrete, heavily skewed 1–5 scale — Pearson assumes normally distributed continuous data and fails to capture non-linear monotonic trends in ordinal ratings.

---

## Feature Handling Description

### Data Cleaning

* Categorical string inconsistencies in `branch`, `parcel_category`, and `vehicle_type` were corrected by mapping known variants to their canonical forms
* Columns stored as object dtype (`parcel_weight_kg`, `parcel_value_sgd`, `num_stops_on_route`, `driver_experience_months`) were coerced to numeric, with unparseable values becoming NaN
* Negative values in numeric fields are semantically impossible and were treated as missing before applying drop or imputation logic
* `driver_experience_months` nulls were imputed using the mean of other records sharing the same `driver_id`, as driver tenure is a stable characteristic — remaining nulls (drivers with no other records) were dropped
* Datetime columns were parsed uniformly to enable hour and duration feature extraction

### Feature Processing

* **Numerical features** — `num_stops_on_route`, `driver_experience_months`, `distance_km` standardised with `StandardScaler` because they are on different scales and tree-based models with preprocessing pipelines benefit from consistent scaling for distance-based steps
* **Nominal features** — `parcel_category`, `branch` one-hot encoded with `drop='first'` to avoid multicollinearity
* **Ordinal feature** — `delivery_priority` ordinally encoded with explicit category order `Standard=0, Express=1, Premium=2, VIP=3`, preserving the meaningful hierarchy rather than treating it as unordered nominal data
* **Passthrough features** — `delivery_hour_before_midnight`, `pickup_hour_before_midnight` are already binary integers requiring no transformation

---

## Explanation of Model Choices

### Models Implemented and Justifications

1. **Decision Tree Classifier** — interpretable baseline tree model that captures non-linear decision boundaries and serves as a reference for more complex ensembles. The tree structure can also be visualised to inspect the learned splits.
2. **Random Forest Classifier** — ensemble of decision trees that reduces overfitting through bagging and random feature subsets. Strong default performance on tabular classification tasks with imbalanced classes.
3. **K-Nearest Neighbors Classifier** — included as a distance-based alternative to tree models. Sensitive to feature scaling and high dimensionality, making it a useful discriminator for whether the feature space has natural cluster structure.

### Hyperparameter Tuning

* Grid search is performed for all three models to systematically explore hyperparameter combinations
* Scoring is macro F1 to give equal weight to all rating classes, including the rare 1, 2, and 3-star categories
* 5-fold cross-validation is used during tuning to reduce the risk of overfitting to a single train/validation split
* Models are fitted on the resampled training set so tuning respects the balanced class distribution

---

## Evaluation of Models

### Evaluation Metrics

All metrics are computed with `average='macro'` to give equal weight to each rating class, preventing the majority classes (4 and 5) from dominating the score.

* **Accuracy** — proportion of correctly predicted ratings overall
* **Precision** (macro) — average precision per class; penalises false positives in minority classes
* **Recall** (macro) — average recall per class; penalises false negatives in minority classes
* **F1 Score** (macro) — harmonic mean of precision and recall; primary selection metric for model comparison
* **ROC AUC** (macro, One-vs-Rest) — average area under the ROC curve across all five classes; measures class separation ability independent of the decision threshold

### Model Performance Comparison

#### Baseline Models (Before Hyperparameter Tuning)

| Model | Accuracy | Precision | Recall | F1 Score | ROC AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dummy Classifier (stratified) | 0.20490 | 0.19979 | 0.20797 | 0.15664 | 0.50391 |
| Random Forest Classifier | 0.37479 | 0.23866 | 0.24805 | 0.23149 | 0.58077 |
| Decision Tree Classifier | 0.31652 | 0.24780 | 0.26890 | 0.20389 | 0.58616 |
| K-Nearest Neighbors Classifier | 0.23721 | 0.23281 | 0.24448 | 0.17920 | 0.53720 |

The Decision Tree achieved the highest baseline macro recall and ROC AUC, proving tree-based architectures can extract predictive signals from the overlapping feature space. KNN failed to meaningfully outperform the stratified dummy baseline, justifying its lower priority in tuning.

#### Hyperparameter Tuned Models (After Grid Search)

| Model | Accuracy | Precision | Recall | F1 Score | ROC AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Tuned Decision Tree | 0.32191 | 0.22349 | 0.23100 | 0.20890 | 0.52125 |
| Tuned Random Forest | 0.38237 | 0.23980 | 0.24923 | 0.23387 | 0.58375 |
| Tuned KNN | 0.30135 | 0.22686 | 0.23704 | 0.20235 | 0.52978 |

### Final Model Selection and Interpretation

The **Tuned Random Forest Classifier** was selected as the best model, achieving the highest validation accuracy (0.38237) and ROC AUC (0.58375) after hyperparameter tuning. It demonstrated the best resilience against dataset noise and the most reliable class separation across all five rating categories.

Key observations from the evaluation:

1. The performance ceiling across all models indicates that the current feature architecture provides a meaningful but incomplete signal — the most impactful individual features (driver experience, stops on route, distance) each carry only moderate correlations with rating due to the heavy concentration of 5-star reviews in the raw data
2. Macro F1 was used as the primary selection metric rather than accuracy, because accuracy on an imbalanced test set would reward models that ignore rare low-rating classes
3. The model is not yet viable for standalone production deployment, but provides a strong foundation — expanding the feature set with richer driver behaviour signals or external route data would likely push performance higher

---

## Considerations for Deployment

### Model Persistence

To make this project production-ready, implement model persistence:

1. Add model saving functionality to `ModelTraining` class:
```python
import joblib

def save_model(self, model, filename):
    """Save the trained model to a file."""
    joblib.dump(model, filename)

def load_model(self, filename):
    """Load a trained model from a file."""
    return joblib.load(filename)
```

2. Create a separate inference script (`inference.py`) for making predictions with saved models:
```python
import pandas as pd
import joblib
from src.data_preparation import DataPreparation

# Load configuration and model
# Preprocess new data
# Make predictions
```