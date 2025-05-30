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

    # Spine / Torso
    "left_torso_pitch": {"p1_idx": 25, "p2_idx": 23, "p3_idx": 11}, # Left Knee, Left Hip, Left Shoulder
    "right_torso_pitch": {"p1_idx": 26, "p2_idx": 24, "p3_idx": 12}, # Right Knee, Right Hip, Right Shoulder
} 