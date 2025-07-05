#!/usr/bin/env python3
"""
Test the enhanced pipeline through the API layer to simulate frontend requests.
"""

import asyncio
import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.video_processing_service import VideoProcessingService
from app.services.ai_service import AIService
from app.services.form_check_service import FormCheckService
from app.services.video_service import VideoService
from app.services.user_service import UserService
from app.models.enums import ExerciseType
from app.core.config import Settings
from app.core.db_deps import get_async_db
from app.models.user import User

async def test_complete_api_flow():
    """Test the complete API flow that would happen from frontend upload."""
    
    print("🚀 **TESTING COMPLETE API FLOW WITH ENHANCED PIPELINE**")
    print("=" * 80)
    
    # Test video
    test_video_path = '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/hypertrophy_faults_1/depth_fault_3_hypertrophy_fault_1.mp4'
    
    if not os.path.exists(test_video_path):
        print(f"❌ Test video not found: {test_video_path}")
        return False
    
    try:
        settings = Settings()
        
        # Initialize services
        print("📊 **STEP 1: INITIALIZING SERVICES**")
        video_service = VideoService(settings)
        form_check_service = FormCheckService(settings)
        user_service = UserService(settings)
        
        print("   ✅ Services initialized")
        
        # Create test user (if needed)
        print("\n👤 **STEP 2: SETTING UP TEST USER**")
        
        async with get_async_db() as session:
            # Check if test user exists
            test_user = await user_service.get_user_by_email(session, "test@formiq.com")
            
            if not test_user:
                user_data = {
                    "email": "test@formiq.com",
                    "username": "testuser",
                    "password": "testpass123",
                    "first_name": "Test",
                    "last_name": "User"
                }
                test_user = await user_service.create_user(session, user_data)
                print("   ✅ Test user created")
            else:
                print("   ✅ Test user found")
            
            user_id = test_user.id
        
        # Step 3: Simulate video upload
        print(f"\n📁 **STEP 3: SIMULATING VIDEO UPLOAD**")
        
        with open(test_video_path, 'rb') as f:
            video_data = f.read()
        
        print(f"   📊 Video size: {len(video_data):,} bytes")
        
        # Create video record (simulating upload)
        async with get_async_db() as session:
            video_metadata = {
                "original_filename": "depth_fault_test.mp4",
                "file_size": len(video_data),
                "content_type": "video/mp4",
                "user_id": user_id
            }
            
            video_record = await video_service.create_video_record(session, video_metadata)
            video_id = video_record.id
            print(f"   ✅ Video record created: {video_id}")
        
        # Step 4: Simulate form check creation
        print(f"\n🎯 **STEP 4: CREATING FORM CHECK**")
        
        async with get_async_db() as session:
            form_check_data = {
                "video_id": video_id,
                "user_id": user_id,
                "exercise_type": ExerciseType.SQUAT,
                "status": "pending"
            }
            
            form_check = await form_check_service.create_form_check(session, form_check_data)
            form_check_id = form_check.id
            print(f"   ✅ Form check created: {form_check_id}")
        
        # Step 5: Simulate video processing (what happens in Celery task)
        print(f"\n🎥 **STEP 5: PROCESSING VIDEO WITH ENHANCED PIPELINE**")
        
        video_processor = VideoProcessingService(app_settings=settings)
        ai_service = AIService(app_settings=settings)
        
        # Process video
        result = await video_processor.process_video(
            video_data=video_data,
            exercise_type=ExerciseType.SQUAT,
            save_processed_frames=False
        )
        
        frames = result['frame_paths']
        print(f"   ✅ Frames extracted: {len(frames)}")
        
        # Pose detection
        pose_results = await ai_service.process_frames_for_pose(
            frames_data_np=frames,
            min_pose_confidence_threshold=0.5
        )
        
        valid_poses = [result for result in pose_results if result is not None]
        print(f"   ✅ Valid poses detected: {len(valid_poses)}")
        
        if len(valid_poses) < 3:
            print(f"   ❌ Insufficient poses for analysis")
            return False
        
        # Step 6: Enhanced feature extraction and ML analysis
        print(f"\n🧠 **STEP 6: ENHANCED ML ANALYSIS**")
        
        # Extract features with enhanced extractor
        features = ai_service.squat_feature_extractor.extract_features(valid_poses)
        print(f"   ✅ Enhanced features extracted: {len(features)}")
        
        # Get ML prediction
        squat_model = ai_service.ml_model_service.get_squat_model()
        
        if squat_model.is_model_available():
            is_good_form, confidence, details = squat_model.predict_form_quality(features)
            
            print(f"   📊 ML Analysis Results:")
            print(f"      Classification: {'GOOD FORM' if is_good_form else 'BAD FORM'}")
            print(f"      Confidence: {confidence:.3f} ({confidence*100:.1f}%)")
            print(f"      Model features: {details.get('feature_count', 'unknown')}")
            
            # Calculate individual scores for database
            ml_scores = {
                'posture_score': features.get('posture_score', 0.0),
                'stability_score': features.get('stability_score', 0.0),
                'depth_score': features.get('overall_score', 0.0) * 0.9  # Fallback calculation
            }
            
            print(f"   📊 Individual Scores:")
            print(f"      Posture: {ml_scores['posture_score']:.1f}/100")
            print(f"      Stability: {ml_scores['stability_score']:.1f}/100") 
            print(f"      Depth: {ml_scores['depth_score']:.1f}/100")
        else:
            print(f"   ❌ ML model not available")
            return False
        
        # Step 7: Update form check with results (simulating Celery task completion)
        print(f"\n💾 **STEP 7: PERSISTING RESULTS**")
        
        async with get_async_db() as session:
            # Prepare analysis results
            analysis_results = {
                'score': int((ml_scores['posture_score'] + ml_scores['stability_score'] + ml_scores['depth_score']) / 3),
                'is_good_form': is_good_form,
                'confidence_score': confidence,
                'posture_score': ml_scores['posture_score'],
                'stability_score': ml_scores['stability_score'],
                'depth_score': ml_scores['depth_score'],
                'feedback_items': [
                    {
                        'type': 'depth_analysis',
                        'message': f"Depth analysis: {'Good depth achieved' if features.get('depth_flag', 0) == 1 else 'Insufficient depth'}",
                        'severity': 'info' if features.get('depth_flag', 0) == 1 else 'warning'
                    },
                    {
                        'type': 'posture_analysis', 
                        'message': f"Posture score: {ml_scores['posture_score']:.0f}/100",
                        'severity': 'info' if ml_scores['posture_score'] > 80 else 'warning'
                    },
                    {
                        'type': 'stability_analysis',
                        'message': f"Stability score: {ml_scores['stability_score']:.0f}/100",
                        'severity': 'info' if ml_scores['stability_score'] > 80 else 'warning'
                    }
                ]
            }
            
            # Update form check status
            await form_check_service.finalize_form_check_analysis_async(
                session=session,
                form_check_id=form_check_id,
                analysis_results=analysis_results,
                status="completed"
            )
            
            print(f"   ✅ Form check updated with enhanced results")
        
        # Step 8: Verify final results
        print(f"\n🔍 **STEP 8: VERIFYING FINAL RESULTS**")
        
        async with get_async_db() as session:
            final_form_check = await form_check_service.get_form_check(session, form_check_id)
            
            if final_form_check:
                print(f"   📊 Final Form Check Results:")
                print(f"      Status: {final_form_check.status}")
                print(f"      Overall Score: {final_form_check.score}/100")
                print(f"      Posture Score: {final_form_check.posture_score}/100")
                print(f"      Stability Score: {final_form_check.stability_score}/100")
                print(f"      Depth Score: {final_form_check.depth_score}/100")
                print(f"      Is Good Form: {final_form_check.is_good_form}")
                print(f"      Confidence: {final_form_check.confidence_score:.3f}")
                
                # Validate scores were persisted
                scores_persisted = all([
                    final_form_check.posture_score is not None,
                    final_form_check.stability_score is not None,
                    final_form_check.depth_score is not None
                ])
                
                print(f"   🎯 Enhanced scores persisted: {'✅ Yes' if scores_persisted else '❌ No'}")
                
                # For our test video (bad form), verify correct classification
                expected_bad = True
                actual_bad = not final_form_check.is_good_form
                correct_classification = expected_bad == actual_bad
                
                print(f"   🎯 Expected: BAD FORM (depth fault video)")
                print(f"   🎯 Classified: {'BAD FORM' if actual_bad else 'GOOD FORM'}")
                print(f"   🎯 Classification Accuracy: {'✅ CORRECT' if correct_classification else '❌ INCORRECT'}")
                
                return scores_persisted and correct_classification
            else:
                print(f"   ❌ Could not retrieve final form check")
                return False
                
    except Exception as e:
        print(f"❌ API flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the complete API integration test."""
    print("🧪 **COMPLETE API INTEGRATION TEST**")
    print("=" * 80)
    
    success = await test_complete_api_flow()
    
    print("=" * 80)
    if success:
        print("🎉 **API INTEGRATION TEST PASSED**")
        print("✅ Enhanced pipeline works end-to-end!")
        print("🚀 Ready for frontend testing!")
    else:
        print("❌ **API INTEGRATION TEST FAILED**")
        print("🔧 Check the issues above")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)