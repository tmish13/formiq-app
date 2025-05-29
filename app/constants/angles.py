UNIVERSAL_ANGLE_DEFINITIONS = {
    # Left Leg
    "left_hip": {"p1_idx": 11, "p2_idx": 23, "p3_idx": 25},  # Left Shoulder, Left Hip, Left Knee
    "left_knee": {"p1_idx": 23, "p2_idx": 25, "p3_idx": 27}, # Left Hip, Left Knee, Left Ankle
    "left_ankle": {"p1_idx": 25, "p2_idx": 27, "p3_idx": 31}, # Left Knee, Left Ankle, Left Foot Index

    # Right Leg
    "right_hip": {"p1_idx": 12, "p2_idx": 24, "p3_idx": 26}, # Right Shoulder, Right Hip, Right Knee
    "right_knee": {"p1_idx": 24, "p2_idx": 26, "p3_idx": 28},# Right Hip, Right Knee, Right Ankle
    "right_ankle": {"p1_idx": 26, "p2_idx": 28, "p3_idx": 32},# Right Knee, Right Ankle, Right Foot Index

    # Left Arm
    "left_shoulder": {"p1_idx": 23, "p2_idx": 11, "p3_idx": 13},# Left Hip, Left Shoulder, Left Elbow
    "left_elbow": {"p1_idx": 11, "p2_idx": 13, "p3_idx": 15}, # Left Shoulder, Left Elbow, Left Wrist

    # Right Arm
    "right_shoulder": {"p1_idx": 24, "p2_idx": 12, "p3_idx": 14},# Right Hip, Right Shoulder, Right Elbow
    "right_elbow": {"p1_idx": 12, "p2_idx": 14, "p3_idx": 16}, # Right Shoulder, Right Elbow, Right Wrist

    # Spine - More complex, might need different definitions or multiple angles
    # Example: Torso angle relative to vertical (requires a vertical reference)
    # Example: Spine bend (e.g., MidHip, MidShoulder, Nose)
    # For now, a simple trunk flexion/extension might be:
    "spine_hip_shoulder_nose": {"p1_idx": 23, "p2_idx": 11, "p3_idx": 0}, # Left Hip, Left Shoulder, Nose (can be averaged with right side for more robustness)
                                                                    # Or more simply, an angle involving the midpoint of shoulders and hips
    # A more direct torso angle might involve averaging shoulder and hip points.
    # Let's define a simple "trunk" angle using average of shoulders, average of hips, and one of the knees (e.g. left_knee)
    # This would represent the angle of the torso relative to the thigh.
    # For a more general spine angle, one might compare the vector from mid-hips to mid-shoulders against a reference (e.g. vertical).
    # Given the request for "Spine" angle, and without further exercise context,
    # let's provide an angle representing general torso flexion/extension relative to the hips.
    # This will be (Midpoint of Shoulders) - (Midpoint of Hips) - (Midpoint of Knees) - this is not standard.

    # Let's define spine as an angle between torso and average hip position, and neck
    # For "Spine" angle, let's consider the angle at the "center" of the hips, using the shoulders as the other two points.
    # This might represent torso lean.
    # Shoulder_Mid = (L_Shoulder + R_Shoulder) / 2
    # Hip_Mid = (L_Hip + R_Hip) / 2
    # Angle at Hip_Mid, with Shoulder_Mid and a point below Hip_Mid (e.g., average of Knees)
    # For simplicity and given no "mid" points directly from MediaPipe, we will define two angles
    # that can be later combined or selected based on exercise.

    "left_torso_pitch": {"p1_idx": 25, "p2_idx": 23, "p3_idx": 11}, # Left Knee, Left Hip, Left Shoulder
    "right_torso_pitch": {"p1_idx": 26, "p2_idx": 24, "p3_idx": 12}, # Right Knee, Right Hip, Right Shoulder
} 