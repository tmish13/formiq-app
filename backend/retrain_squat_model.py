#!/usr/bin/env python3
"""
Comprehensive squat model retraining script using enhanced feature extraction.

This script will:
1. Load video data from the training dataset
2. Extract features using the enhanced feature extraction service
3. Train a new XGBoost model with proper feature handling
4. Validate the model with known good/bad form videos
5. Export the trained model for production use
"""

import asyncio
import sys
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb
import joblib

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.video_processing_service import VideoProcessingService
from app.services.ai_service import AIService
from app.services.enhanced_feature_extraction_service import EnhancedSquatFeatureExtractor
from app.models.enums import ExerciseType
from app.core.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SquatModelRetrainer:
    """Comprehensive squat model retraining with enhanced features."""
    
    def __init__(self, training_data_path: str):
        """
        Initialize the model retrainer.
        
        Args:
            training_data_path: Path to the training video dataset
        """
        self.training_data_path = Path(training_data_path)
        self.settings = Settings()
        self.extractor = EnhancedSquatFeatureExtractor()
        self.video_processor = None
        self.ai_service = None
        
        # Training data storage
        self.features_df = None
        self.labels = None
        
    async def initialize_services(self):
        """Initialize video processing and AI services."""
        self.video_processor = VideoProcessingService(app_settings=self.settings)
        self.ai_service = AIService(app_settings=self.settings)
        
    def discover_training_videos(self) -> List[Dict[str, Any]]:
        """
        Discover all training videos and their labels.
        
        Returns:
            List of video metadata with paths and labels
        """
        videos = []
        
        # Define the expected dataset structure
        dataset_structure = {
            'good_form': 1,  # Good form label
            'bad_form': 0,   # Bad form label
        }
        
        for form_type, label in dataset_structure.items():
            form_path = self.training_data_path / 'squat' / form_type
            
            if not form_path.exists():
                logger.warning(f"Form type directory not found: {form_path}")
                continue
                
            # Handle subdirectories for bad form types
            if form_type == 'bad_form':
                # Look for fault-specific subdirectories
                fault_dirs = [d for d in form_path.iterdir() if d.is_dir()]
                
                for fault_dir in fault_dirs:
                    fault_type = fault_dir.name
                    for video_file in fault_dir.glob('*.mp4'):
                        videos.append({
                            'path': str(video_file),
                            'label': label,
                            'form_type': form_type,
                            'fault_type': fault_type,
                            'filename': video_file.name
                        })
            else:
                # Good form videos directly in the directory
                for video_file in form_path.glob('*.mp4'):
                    videos.append({
                        'path': str(video_file),
                        'label': label,
                        'form_type': form_type,
                        'fault_type': 'none',
                        'filename': video_file.name
                    })
        
        logger.info(f"Discovered {len(videos)} training videos")
        
        # Log distribution
        good_count = sum(1 for v in videos if v['label'] == 1)
        bad_count = sum(1 for v in videos if v['label'] == 0)
        logger.info(f"Good form videos: {good_count}")
        logger.info(f"Bad form videos: {bad_count}")
        
        return videos
    
    async def extract_features_from_video(self, video_path: str) -> Dict[str, float]:
        """
        Extract features from a single video using enhanced feature extraction.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary of extracted features
        """
        try:
            # Read video data
            with open(video_path, 'rb') as f:
                video_data = f.read()
            
            # Process video
            result = await self.video_processor.process_video(
                video_data=video_data,
                exercise_type=ExerciseType.SQUAT,
                save_processed_frames=False
            )
            
            frames = result['frame_paths']
            if len(frames) < 3:
                logger.warning(f"Insufficient frames in {video_path}: {len(frames)}")
                return self.extractor._get_default_features()
            
            # Pose detection
            pose_results = await self.ai_service.process_frames_for_pose(
                frames_data_np=frames,
                min_pose_confidence_threshold=0.5
            )
            
            valid_poses = [result for result in pose_results if result is not None]
            if len(valid_poses) < 3:
                logger.warning(f"Insufficient valid poses in {video_path}: {len(valid_poses)}")
                return self.extractor._get_default_features()
            
            # Extract features using enhanced extractor
            features = self.extractor.extract_features(valid_poses)
            
            logger.info(f"✅ Features extracted from {os.path.basename(video_path)}: {len(features)} features")
            return features
            
        except Exception as e:
            logger.error(f"❌ Failed to extract features from {video_path}: {e}")
            return self.extractor._get_default_features()
    
    async def extract_all_features(self, videos: List[Dict[str, Any]], max_videos: int = None) -> Tuple[pd.DataFrame, List[int]]:
        """
        Extract features from all training videos.
        
        Args:
            videos: List of video metadata
            max_videos: Maximum number of videos to process (for testing)
            
        Returns:
            Tuple of (features_dataframe, labels_list)
        """
        if max_videos:
            # Ensure balanced sampling when limiting videos
            good_videos = [v for v in videos if v['label'] == 1]
            bad_videos = [v for v in videos if v['label'] == 0]
            
            videos_per_class = max_videos // 2
            selected_videos = (
                good_videos[:videos_per_class] + 
                bad_videos[:videos_per_class]
            )
            videos = selected_videos
            logger.info(f"🔄 Balanced sampling: {len([v for v in videos if v['label'] == 1])} good, {len([v for v in videos if v['label'] == 0])} bad")
            
        all_features = []
        all_labels = []
        all_metadata = []
        
        logger.info(f"🔄 Starting feature extraction from {len(videos)} videos...")
        
        for i, video_info in enumerate(videos, 1):
            logger.info(f"📹 Processing video {i}/{len(videos)}: {video_info['filename']}")
            
            features = await self.extract_features_from_video(video_info['path'])
            
            if features:
                all_features.append(features)
                all_labels.append(video_info['label'])
                all_metadata.append({
                    'filename': video_info['filename'],
                    'form_type': video_info['form_type'],
                    'fault_type': video_info['fault_type']
                })
                
                # Log some key features for debugging
                logger.info(f"   Key features: depth_flag={features.get('depth_flag', 'N/A'):.1f}, "
                          f"posture_score={features.get('posture_score', 'N/A'):.1f}, "
                          f"min_knee_angle={features.get('min_knee_angle', 'N/A'):.1f}")
            else:
                logger.warning(f"❌ Failed to extract features from {video_info['filename']}")
        
        # Convert to DataFrame
        features_df = pd.DataFrame(all_features)
        labels = all_labels
        
        logger.info(f"✅ Feature extraction completed")
        logger.info(f"📊 Dataset shape: {features_df.shape}")
        logger.info(f"📊 Features: {list(features_df.columns)}")
        logger.info(f"📊 Label distribution: {pd.Series(labels).value_counts().to_dict()}")
        
        return features_df, labels, all_metadata
    
    def analyze_feature_distribution(self, features_df: pd.DataFrame, labels: List[int]) -> Dict[str, Any]:
        """
        Analyze the distribution of features across good/bad form.
        
        Args:
            features_df: Features dataframe
            labels: List of labels
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("🔍 **FEATURE DISTRIBUTION ANALYSIS**")
        
        analysis = {}
        
        # Create combined dataframe
        df = features_df.copy()
        df['label'] = labels
        df['form_quality'] = df['label'].map({1: 'good_form', 0: 'bad_form'})
        
        # Analyze each feature
        feature_analysis = {}
        
        critical_features = [
            'depth_flag', 'posture_score', 'stability_score', 'overall_score',
            'min_knee_angle', 'max_torso_lean_angle', 'knee_valgus_flag',
            'torso_control_flag', 'asymmetry_flag'
        ]
        
        for feature in critical_features:
            if feature in df.columns:
                good_values = df[df['label'] == 1][feature]
                bad_values = df[df['label'] == 0][feature]
                
                feature_stats = {
                    'good_form': {
                        'mean': good_values.mean(),
                        'std': good_values.std(),
                        'min': good_values.min(),
                        'max': good_values.max()
                    },
                    'bad_form': {
                        'mean': bad_values.mean(),
                        'std': bad_values.std(),
                        'min': bad_values.min(),
                        'max': bad_values.max()
                    },
                    'separation': abs(good_values.mean() - bad_values.mean())
                }
                
                feature_analysis[feature] = feature_stats
                
                logger.info(f"📊 {feature}:")
                logger.info(f"   Good form: {good_values.mean():.2f} ± {good_values.std():.2f}")
                logger.info(f"   Bad form:  {bad_values.mean():.2f} ± {bad_values.std():.2f}")
                logger.info(f"   Separation: {feature_stats['separation']:.2f}")
        
        analysis['feature_stats'] = feature_analysis
        analysis['total_samples'] = len(df)
        analysis['good_form_count'] = sum(labels)
        analysis['bad_form_count'] = len(labels) - sum(labels)
        
        return analysis
    
    def train_models(self, features_df: pd.DataFrame, labels: List[int]) -> Dict[str, Any]:
        """
        Train multiple models and select the best one.
        
        Args:
            features_df: Features dataframe
            labels: List of labels
            
        Returns:
            Dictionary with trained models and metrics
        """
        logger.info("🤖 **MODEL TRAINING**")
        
        X = features_df.values.astype(np.float64)  # Ensure float64 dtype
        y = np.array(labels, dtype=np.int32)      # Ensure int32 dtype
        
        # Check we have both classes
        unique_classes = np.unique(y)
        logger.info(f"📊 Classes in dataset: {unique_classes}")
        
        if len(unique_classes) < 2:
            raise ValueError(f"Need both good and bad form samples, got only class(es): {unique_classes}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"📊 Training set: {X_train.shape[0]} samples")
        logger.info(f"📊 Test set: {X_test.shape[0]} samples")
        logger.info(f"📊 Training classes: {np.unique(y_train)}")
        logger.info(f"📊 Test classes: {np.unique(y_test)}")
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train).astype(np.float64)
        X_test_scaled = scaler.transform(X_test).astype(np.float64)
        
        models = {}
        
        # 1. XGBoost (simplified for faster training)
        logger.info("🔄 Training XGBoost...")
        
        # Simplified parameters for faster training
        xgb_params = {
            'n_estimators': [100, 200],
            'max_depth': [4, 6],
            'learning_rate': [0.1, 0.2]
        }
        
        xgb_grid = GridSearchCV(
            xgb.XGBClassifier(random_state=42, eval_metric='logloss'),
            xgb_params,
            cv=3,  # Reduced CV folds for speed
            scoring='roc_auc',
            n_jobs=1  # Avoid parallel issues
        )
        
        xgb_grid.fit(X_train_scaled, y_train)
        xgb_best = xgb_grid.best_estimator_
        
        models['xgboost'] = {
            'model': xgb_best,
            'scaler': scaler,
            'best_params': xgb_grid.best_params_,
            'cv_score': xgb_grid.best_score_
        }
        
        # 2. Random Forest (simplified)
        logger.info("🔄 Training Random Forest...")
        
        rf_params = {
            'n_estimators': [100, 200],
            'max_depth': [10, None],
            'min_samples_split': [2, 5]
        }
        
        rf_grid = GridSearchCV(
            RandomForestClassifier(random_state=42),
            rf_params,
            cv=3,
            scoring='roc_auc',
            n_jobs=1
        )
        
        rf_grid.fit(X_train, y_train)  # RF doesn't need scaling
        rf_best = rf_grid.best_estimator_
        
        models['random_forest'] = {
            'model': rf_best,
            'scaler': None,
            'best_params': rf_grid.best_params_,
            'cv_score': rf_grid.best_score_
        }
        
        # Evaluate all models
        results = {}
        
        for model_name, model_info in models.items():
            logger.info(f"📊 Evaluating {model_name}...")
            
            model = model_info['model']
            
            if model_info['scaler']:
                y_pred = model.predict(X_test_scaled)
                y_proba = model.predict_proba(X_test_scaled)[:, 1]
            else:
                y_pred = model.predict(X_test)
                y_proba = model.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            auc_score = roc_auc_score(y_test, y_proba)
            accuracy = np.mean(y_pred == y_test)
            
            # Classification report
            report = classification_report(y_test, y_pred, output_dict=True)
            
            results[model_name] = {
                'auc_score': auc_score,
                'accuracy': accuracy,
                'classification_report': report,
                'cv_score': model_info['cv_score'],
                'best_params': model_info['best_params']
            }
            
            logger.info(f"   AUC: {auc_score:.3f}")
            logger.info(f"   Accuracy: {accuracy:.3f}")
            logger.info(f"   CV Score: {model_info['cv_score']:.3f}")
        
        # Select best model
        best_model_name = max(results.keys(), key=lambda k: results[k]['auc_score'])
        best_model_info = models[best_model_name]
        
        logger.info(f"🏆 Best model: {best_model_name} (AUC: {results[best_model_name]['auc_score']:.3f})")
        
        return {
            'best_model': best_model_info,
            'best_model_name': best_model_name,
            'all_results': results,
            'feature_names': list(features_df.columns),
            'X_test': X_test,
            'y_test': y_test,
            'X_test_scaled': X_test_scaled if best_model_info['scaler'] else X_test
        }
    
    def export_model(self, model_results: Dict[str, Any], output_dir: str) -> None:
        """
        Export the trained model for production use.
        
        Args:
            model_results: Results from model training
            output_dir: Directory to save the model
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        logger.info(f"💾 **EXPORTING MODEL TO {output_path}**")
        
        best_model_info = model_results['best_model']
        feature_names = model_results['feature_names']
        
        # Save model
        model_path = output_path / 'binary_classification_model.joblib'
        joblib.dump(best_model_info['model'], model_path)
        logger.info(f"✅ Model saved: {model_path}")
        
        # Save scaler if exists
        if best_model_info['scaler']:
            scaler_path = output_path / 'feature_scaler.joblib'
            joblib.dump(best_model_info['scaler'], scaler_path)
            logger.info(f"✅ Scaler saved: {scaler_path}")
        
        # Save feature names
        features_path = output_path / 'feature_names.json'
        with open(features_path, 'w') as f:
            json.dump(feature_names, f, indent=2)
        logger.info(f"✅ Feature names saved: {features_path}")
        
        # Calculate optimal threshold (balanced accuracy)
        model = best_model_info['model']
        X_test = model_results['X_test_scaled']
        y_test = model_results['y_test']
        
        y_proba = model.predict_proba(X_test)[:, 1]
        
        # Find optimal threshold
        thresholds = np.linspace(0.1, 0.9, 100)
        best_threshold = 0.5
        best_score = 0
        
        for threshold in thresholds:
            y_pred_thresh = (y_proba >= threshold).astype(int)
            accuracy = np.mean(y_pred_thresh == y_test)
            
            if accuracy > best_score:
                best_score = accuracy
                best_threshold = threshold
        
        # Save optimal threshold
        threshold_path = output_path / 'optimal_threshold.json'
        with open(threshold_path, 'w') as f:
            json.dump({
                'optimal_threshold': best_threshold,
                'threshold_accuracy': best_score
            }, f, indent=2)
        logger.info(f"✅ Optimal threshold saved: {threshold_path} (threshold: {best_threshold:.3f})")
        
        # Save metadata
        metadata = {
            'model_type': model_results['best_model_name'],
            'training_date': pd.Timestamp.now().isoformat(),
            'feature_count': len(feature_names),
            'best_params': best_model_info['best_params'],
            'performance_metrics': model_results['all_results'][model_results['best_model_name']],
            'optimal_threshold': best_threshold
        }
        
        metadata_path = output_path / 'production_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✅ Metadata saved: {metadata_path}")
        
        logger.info(f"🎉 **MODEL EXPORT COMPLETED**")
        logger.info(f"📂 Files saved in: {output_path}")
    
    async def test_with_known_videos(self, model_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test the trained model with known good/bad form videos.
        
        Args:
            model_results: Results from model training
            
        Returns:
            Dictionary with test results
        """
        logger.info("🧪 **TESTING WITH KNOWN VIDEOS**")
        
        # Known test videos
        test_videos = [
            {
                'path': '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/hypertrophy_faults_1/depth_fault_3_hypertrophy_fault_1.mp4',
                'expected_label': 0,
                'description': 'Depth fault video'
            },
            {
                'path': '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/stability_faults/1692_stability_fault_1.mp4',
                'expected_label': 0,
                'description': 'Stability fault video'
            }
        ]
        
        model = model_results['best_model']['model']
        scaler = model_results['best_model']['scaler']
        feature_names = model_results['feature_names']
        
        test_results = []
        
        for test_video in test_videos:
            if not os.path.exists(test_video['path']):
                logger.warning(f"Test video not found: {test_video['path']}")
                continue
                
            logger.info(f"🎥 Testing: {test_video['description']}")
            
            # Extract features
            features = await self.extract_features_from_video(test_video['path'])
            
            # Prepare features for prediction
            feature_vector = np.array([[features.get(name, 0.0) for name in feature_names]])
            
            if scaler:
                feature_vector = scaler.transform(feature_vector)
            
            # Predict
            prediction = model.predict(feature_vector)[0]
            probability = model.predict_proba(feature_vector)[0]
            
            # Analyze result
            correct = prediction == test_video['expected_label']
            confidence = max(probability)
            
            result = {
                'video': test_video['description'],
                'expected': 'BAD' if test_video['expected_label'] == 0 else 'GOOD',
                'predicted': 'BAD' if prediction == 0 else 'GOOD',
                'correct': correct,
                'confidence': confidence,
                'probabilities': {
                    'bad_form': probability[0],
                    'good_form': probability[1]
                },
                'key_features': {
                    'depth_flag': features.get('depth_flag', 0),
                    'posture_score': features.get('posture_score', 0),
                    'min_knee_angle': features.get('min_knee_angle', 180)
                }
            }
            
            test_results.append(result)
            
            logger.info(f"   Expected: {result['expected']}")
            logger.info(f"   Predicted: {result['predicted']} ({'✅' if correct else '❌'})")
            logger.info(f"   Confidence: {confidence:.1%}")
            logger.info(f"   Key features: {result['key_features']}")
        
        # Summary
        total_tests = len(test_results)
        correct_predictions = sum(1 for r in test_results if r['correct'])
        accuracy = correct_predictions / total_tests if total_tests > 0 else 0
        
        logger.info(f"🎯 **TEST SUMMARY**")
        logger.info(f"   Total tests: {total_tests}")
        logger.info(f"   Correct predictions: {correct_predictions}")
        logger.info(f"   Accuracy: {accuracy:.1%}")
        
        return {
            'test_results': test_results,
            'accuracy': accuracy,
            'total_tests': total_tests
        }


async def main():
    """Main function to run the complete retraining pipeline."""
    
    # Configuration
    TRAINING_DATA_PATH = '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos'
    OUTPUT_MODEL_PATH = '/Users/tarpanmishra/formiq-app-3/backend/app/ml_models/squat'
    MAX_VIDEOS_FOR_TESTING = 20  # Set to None for full dataset
    
    logger.info("🚀 **STARTING SQUAT MODEL RETRAINING**")
    logger.info("=" * 80)
    
    # Initialize retrainer
    retrainer = SquatModelRetrainer(TRAINING_DATA_PATH)
    await retrainer.initialize_services()
    
    try:
        # Step 1: Discover training videos
        logger.info("📹 **STEP 1: DISCOVERING TRAINING VIDEOS**")
        videos = retrainer.discover_training_videos()
        
        if not videos:
            logger.error("❌ No training videos found!")
            return False
        
        # Step 2: Extract features
        logger.info("🧮 **STEP 2: EXTRACTING FEATURES**")
        features_df, labels, metadata = await retrainer.extract_all_features(videos, MAX_VIDEOS_FOR_TESTING)
        
        if features_df.empty:
            logger.error("❌ No features extracted!")
            return False
        
        # Step 3: Analyze features
        logger.info("🔍 **STEP 3: ANALYZING FEATURE DISTRIBUTION**")
        analysis = retrainer.analyze_feature_distribution(features_df, labels)
        
        # Step 4: Train models
        logger.info("🤖 **STEP 4: TRAINING MODELS**")
        model_results = retrainer.train_models(features_df, labels)
        
        # Step 5: Test with known videos
        logger.info("🧪 **STEP 5: TESTING WITH KNOWN VIDEOS**")
        test_results = await retrainer.test_with_known_videos(model_results)
        
        # Step 6: Export model
        logger.info("💾 **STEP 6: EXPORTING MODEL**")
        retrainer.export_model(model_results, OUTPUT_MODEL_PATH)
        
        # Final summary
        logger.info("=" * 80)
        logger.info("🎉 **RETRAINING COMPLETED SUCCESSFULLY**")
        logger.info(f"📊 Best model: {model_results['best_model_name']}")
        logger.info(f"📊 AUC Score: {model_results['all_results'][model_results['best_model_name']]['auc_score']:.3f}")
        logger.info(f"📊 Test accuracy: {test_results['accuracy']:.1%}")
        logger.info(f"📂 Model saved to: {OUTPUT_MODEL_PATH}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Retraining failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)