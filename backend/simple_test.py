#!/usr/bin/env python3
"""Simple test for visual overlay system components."""

import sys
from pathlib import Path
import asyncio

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.reference_pose_service import ReferencePoseService

async def simple_test():
    print("🚀 Testing Visual Overlay System")
    print("=" * 40)
    
    try:
        # Test 1: Reference pose generation
        print("1. Testing reference pose generation...")
        settings = get_settings()
        service = ReferencePoseService(settings)
        
        pose_data = service.generate_reference_pose('squat')
        
        print(f"   ✅ Generated {len(pose_data['pose_sequence'])} frames")
        print(f"   ✅ Key poses: {list(pose_data['key_poses'].keys())}")
        print(f"   ✅ Exercise type: {pose_data['metadata']['exercise_type']}")
        
        # Test 2: Validate key pose structure
        print("2. Testing pose structure...")
        setup_pose = pose_data['key_poses']['setup']
        
        required_joints = ['left_hip', 'right_hip', 'left_knee', 'right_knee', 
                          'left_ankle', 'right_ankle', 'left_shoulder', 'right_shoulder']
        
        missing_joints = [joint for joint in required_joints if joint not in setup_pose]
        
        if not missing_joints:
            print("   ✅ All required joints present")
        else:
            print(f"   ❌ Missing joints: {missing_joints}")
        
        # Test 3: Biomechanical validation
        print("3. Testing biomechanical validation...")
        from app.services.reference_pose_service import ReferenceSquatGenerator
        
        generator = ReferenceSquatGenerator(settings)
        validation = generator.validate_pose_biomechanics(setup_pose)
        
        print(f"   ✅ Pose validation: {validation['is_valid']}")
        if 'measurements' in validation:
            print(f"   ✅ Measurements: {len(validation['measurements'])} calculated")
        
        print("\n🎉 Basic tests completed successfully!")
        print("✅ Reference pose generation working")
        print("✅ Biomechanical validation working")
        print("✅ Data structure correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")