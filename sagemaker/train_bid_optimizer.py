"""
SageMaker Training Script: Bid Optimization Model

Trains a model to predict optimal CPC bid based on temporal and performance features.

Usage:
    Called by SageMaker training job
    Input: Training data from S3 (CSV or Parquet)
    Output: Trained model artifacts to S3
"""

import argparse
import os
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

# ML libraries
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler

# SageMaker paths
PREFIX = '/opt/ml'
INPUT_PATH = os.path.join(PREFIX, 'input/data')
OUTPUT_PATH = os.path.join(PREFIX, 'output')
MODEL_PATH = os.path.join(PREFIX, 'model')
PARAM_PATH = os.path.join(PREFIX, 'input/config/hyperparameters.json')


def load_training_data(channel='training'):
    """Load training data from S3."""

    input_files = []
    input_dir = os.path.join(INPUT_PATH, channel)

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.csv') or file.endswith('.parquet'):
                input_files.append(os.path.join(root, file))

    if not input_files:
        raise ValueError(f"No data files found in {input_dir}")

    print(f"Found {len(input_files)} data files")

    dfs = []
    for file_path in input_files:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_parquet(file_path)
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    print(f"Loaded {len(data)} training samples")

    return data


def engineer_features(df):
    """
    Engineer additional features for bid optimization.

    Creates interaction features and temporal patterns.
    """

    df = df.copy()

    # Time-based features
    df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

    # Performance features
    df['ctr_squared'] = df['avg_ctr'] ** 2
    df['cpc_squared'] = df['avg_cpc'] ** 2

    # Interaction features
    df['ctr_x_conversion_rate'] = df['avg_ctr'] * df['avg_conversion_rate']
    df['cpc_x_clicks'] = df['avg_cpc'] * df['total_clicks']

    # Traffic volume features
    df['log_impressions'] = np.log1p(df['total_impressions'])
    df['log_clicks'] = np.log1p(df['total_clicks'])

    # Competition proxy (based on cost variance)
    df['cost_per_impression'] = df['total_cost'] / (df['total_impressions'] + 1)

    return df


def prepare_features_and_target(df, target_col='optimal_bid'):
    """
    Prepare feature matrix and target variable.
    """

    # Columns to exclude
    exclude_cols = [
        'campaign_id', target_col, 'total_cost', 'avg_cpc'
    ]

    feature_cols = [col for col in df.columns if col not in exclude_cols]

    print(f"Features selected: {feature_cols}")

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # Handle missing values
    X = X.fillna(0)

    # Remove samples with missing or invalid target
    mask = (~y.isna()) & (y > 0) & (y < 50)  # Reasonable bid range: $0.01 to $50
    X = X[mask]
    y = y[mask]

    print(f"Final dataset: {len(X)} samples, {len(feature_cols)} features")
    print(f"Target (optimal bid) range: ${y.min():.2f} to ${y.max():.2f}")
    print(f"Target (optimal bid) mean: ${y.mean():.2f}, median: ${y.median():.2f}")

    return X, y, feature_cols


def train_model(X_train, y_train, hyperparameters):
    """
    Train Gradient Boosting model for bid optimization.

    Gradient Boosting is chosen because:
    - Handles non-linear relationships well
    - Robust to outliers
    - Good for regression with complex interactions
    """

    print("\n" + "="*60)
    print("Starting Model Training")
    print("="*60)

    # Extract hyperparameters
    n_estimators = int(hyperparameters.get('n_estimators', 200))
    learning_rate = float(hyperparameters.get('learning_rate', 0.1))
    max_depth = int(hyperparameters.get('max_depth', 5))
    min_samples_split = int(hyperparameters.get('min_samples_split', 10))
    min_samples_leaf = int(hyperparameters.get('min_samples_leaf', 4))
    subsample = float(hyperparameters.get('subsample', 0.8))

    print(f"Hyperparameters:")
    print(f"  n_estimators: {n_estimators}")
    print(f"  learning_rate: {learning_rate}")
    print(f"  max_depth: {max_depth}")
    print(f"  min_samples_split: {min_samples_split}")
    print(f"  min_samples_leaf: {min_samples_leaf}")
    print(f"  subsample: {subsample}")

    # Create model
    model = GradientBoostingRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        subsample=subsample,
        random_state=42,
        verbose=1
    )

    # Train
    print("\nTraining model...")
    model.fit(X_train, y_train)
    print("✓ Training complete")

    return model


def evaluate_model(model, X_train, y_train, X_test, y_test, feature_names):
    """
    Evaluate model performance.
    """

    print("\n" + "="*60)
    print("Model Evaluation")
    print("="*60)

    # Training set
    y_train_pred = model.predict(X_train)
    train_mse = mean_squared_error(y_train, y_train_pred)
    train_rmse = np.sqrt(train_mse)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_r2 = r2_score(y_train, y_train_pred)

    # Calculate mean absolute percentage error
    train_mape = np.mean(np.abs((y_train - y_train_pred) / y_train)) * 100

    print("\nTraining Set:")
    print(f"  MSE:  {train_mse:.6f}")
    print(f"  RMSE: ${train_rmse:.2f}")
    print(f"  MAE:  ${train_mae:.2f}")
    print(f"  MAPE: {train_mape:.2f}%")
    print(f"  R²:   {train_r2:.6f}")

    # Test set
    y_test_pred = model.predict(X_test)
    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    test_mape = np.mean(np.abs((y_test - y_test_pred) / y_test)) * 100

    print("\nTest Set:")
    print(f"  MSE:  {test_mse:.6f}")
    print(f"  RMSE: ${test_rmse:.2f}")
    print(f"  MAE:  ${test_mae:.2f}")
    print(f"  MAPE: {test_mape:.2f}%")
    print(f"  R²:   {test_r2:.6f}")

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop 10 Most Important Features:")
    print(feature_importance.head(10).to_string(index=False))

    # Cross-validation
    print("\nCross-Validation (5-fold):")
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2', n_jobs=-1)
    print(f"  CV R² scores: {cv_scores}")
    print(f"  CV R² mean:   {cv_scores.mean():.6f} (+/- {cv_scores.std() * 2:.6f})")

    # Bid prediction examples
    print("\nSample Predictions (Test Set):")
    sample_df = pd.DataFrame({
        'Actual Bid': y_test.head(10).values,
        'Predicted Bid': y_test_pred[:10],
        'Difference': y_test_pred[:10] - y_test.head(10).values
    })
    print(sample_df.to_string(index=False))

    return {
        'train_mse': train_mse,
        'train_rmse': train_rmse,
        'train_mae': train_mae,
        'train_mape': train_mape,
        'train_r2': train_r2,
        'test_mse': test_mse,
        'test_rmse': test_rmse,
        'test_mae': test_mae,
        'test_mape': test_mape,
        'test_r2': test_r2,
        'cv_r2_mean': cv_scores.mean(),
        'cv_r2_std': cv_scores.std(),
        'feature_importance': feature_importance.to_dict('records')
    }


def save_model(model, feature_names, metrics, model_path=MODEL_PATH):
    """
    Save trained model and metadata.
    """

    print("\n" + "="*60)
    print("Saving Model")
    print("="*60)

    os.makedirs(model_path, exist_ok=True)

    # Save model
    model_file = os.path.join(model_path, 'model.joblib')
    joblib.dump(model, model_file)
    print(f"✓ Model saved to {model_file}")

    # Save feature names
    features_file = os.path.join(model_path, 'features.json')
    with open(features_file, 'w') as f:
        json.dump({'features': feature_names}, f, indent=2)
    print(f"✓ Features saved to {features_file}")

    # Save metrics
    metrics_file = os.path.join(model_path, 'metrics.json')
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved to {metrics_file}")

    # Save model metadata
    metadata = {
        'model_type': 'GradientBoostingRegressor',
        'framework': 'scikit-learn',
        'target': 'optimal_bid',
        'n_features': len(feature_names),
        'test_r2': metrics['test_r2'],
        'test_rmse': metrics['test_rmse'],
        'test_mae': metrics['test_mae'],
        'test_mape': metrics['test_mape'],
        'created_at': pd.Timestamp.now().isoformat()
    }

    metadata_file = os.path.join(model_path, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to {metadata_file}")


def main():
    """Main training function."""

    print("\n" + "="*60)
    print("Bid Optimization Model Training")
    print("="*60)

    # Load hyperparameters
    hyperparameters = {}
    if os.path.exists(PARAM_PATH):
        with open(PARAM_PATH) as f:
            hyperparameters = json.load(f)

    # Load data
    print("\nLoading training data...")
    df = load_training_data('training')

    # Engineer features
    print("\nEngineering features...")
    df = engineer_features(df)

    # Prepare features and target
    X, y, feature_names = prepare_features_and_target(df, target_col='optimal_bid')

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set:  {len(X_test)} samples")

    # Train model
    model = train_model(X_train, y_train, hyperparameters)

    # Evaluate
    metrics = evaluate_model(model, X_train, y_train, X_test, y_test, feature_names)

    # Save
    save_model(model, feature_names, metrics)

    print("\n" + "="*60)
    print("✅ Training Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
