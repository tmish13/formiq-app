"""
PostureV1 CNN-LSTM model architecture.

This MUST match the architecture used during training.  The checkpoint
contains a ``model_config`` dict; the loader constructs this class with
those parameters and then calls ``load_state_dict``.

Architecture (matches training repo):
    1. Temporal CNN (``cnn_1d``):  [B, J*C, T] -> [B, cnn_out, T]
       Conv1d(kernel=5, pad=2) -> ReLU -> BatchNorm -> Dropout   (per channel pair)
    2. LSTM:  [B, T, cnn_out] -> hidden state [B, lstm_hidden]
    3. Fusion MLP (``fusion_mlp``):  concat(lstm_hidden, feature_dim) -> logits
       Linear -> ReLU -> BatchNorm -> Dropout   (per mlp_dim)
       Linear -> output_dim

Forward signature:
    logits = model(keypoints, rep_features, sequence_lengths)
        keypoints       : [B, 300, 33, 3]  float32
        rep_features    : [B, 151]          float32
        sequence_lengths: [B]               int / long
    returns logits      : [B, output_dim]   (raw, pre-sigmoid)
"""

import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence
from typing import Dict, Any


class PostureV1Model(nn.Module):
    """CNN-LSTM posture fault classifier matching the training repo."""

    # Defaults mirror the manifest model_config.  Every value can be
    # overridden through ``model_config`` stored inside the checkpoint.
    DEFAULT_CONFIG: Dict[str, Any] = {
        "num_joints": 33,
        "joint_dim": 3,
        "feature_dim": 151,
        "cnn_channels": [32, 64],
        "lstm_hidden": 96,
        "lstm_layers": 2,
        "lstm_dropout": 0.0,
        "mlp_dims": [256, 128],
        "output_dim": 2,
        "cnn_dropout": 0.4,
        "mlp_dropout": 0.4,
        "sequence_length": 300,
    }

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__()
        cfg = {**self.DEFAULT_CONFIG, **(config or {})}
        self.config = cfg

        # Accept both manifest keys and legacy keys
        num_joints = cfg.get("num_joints", cfg.get("num_landmarks", 33))
        joint_dim = cfg.get("joint_dim", cfg.get("num_coords", 3))
        cnn_ch = cfg["cnn_channels"]
        cnn_dropout = cfg.get("cnn_dropout", 0.0)
        lstm_hidden = cfg["lstm_hidden"]
        lstm_layers = cfg.get("lstm_layers", 2)
        lstm_dropout = cfg.get("lstm_dropout", 0.0)
        feature_dim = cfg["feature_dim"]
        mlp_dims = cfg.get("mlp_dims", [256, 128])
        mlp_dropout = cfg.get("mlp_dropout", 0.0)
        output_dim = cfg.get("output_dim", cfg.get("num_classes", 2))

        # --- Temporal CNN ---
        # Input: [B, num_joints*joint_dim, T]  (e.g. [B, 99, 300])
        # Conv1d with kernel=5, padding=2 preserves temporal dimension.
        in_ch = num_joints * joint_dim
        cnn_layers = []
        for out_ch in cnn_ch:
            cnn_layers.extend([
                nn.Conv1d(in_ch, out_ch, kernel_size=5, padding=2),
                nn.ReLU(inplace=True),
                nn.BatchNorm1d(out_ch),
                nn.Dropout(cnn_dropout),
            ])
            in_ch = out_ch
        self.cnn_1d = nn.Sequential(*cnn_layers)
        cnn_out_dim = cnn_ch[-1]

        # --- Temporal LSTM ---
        self.lstm = nn.LSTM(
            input_size=cnn_out_dim,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=lstm_dropout if lstm_layers > 1 else 0.0,
            bidirectional=False,
        )

        # --- Fusion MLP: concat(lstm_hidden, feature_dim) -> logits ---
        mlp_layers = []
        prev_dim = lstm_hidden + feature_dim
        for dim in mlp_dims:
            mlp_layers.extend([
                nn.Linear(prev_dim, dim),
                nn.ReLU(inplace=True),
                nn.BatchNorm1d(dim),
                nn.Dropout(mlp_dropout),
            ])
            prev_dim = dim
        mlp_layers.append(nn.Linear(prev_dim, output_dim))
        self.fusion_mlp = nn.Sequential(*mlp_layers)

    def forward(
        self,
        keypoints: torch.Tensor,
        rep_features: torch.Tensor,
        sequence_lengths: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            keypoints:        [B, T, J, C]  (e.g. [B, 300, 33, 3])
            rep_features:     [B, feature_dim]  (e.g. [B, 151])
            sequence_lengths: [B]  (actual valid frame count per sample)

        Returns:
            logits: [B, output_dim]
        """
        B, T, J, C = keypoints.shape

        # Flatten joints*coords and permute for Conv1d: [B, J*C, T]
        x = keypoints.reshape(B, T, J * C).permute(0, 2, 1)
        x = self.cnn_1d(x)  # [B, cnn_out, T]

        # Permute for LSTM: [B, T, cnn_out]
        x = x.permute(0, 2, 1)

        # Pack for LSTM (handles variable-length sequences)
        lengths_cpu = sequence_lengths.cpu().clamp(min=1)
        packed = pack_padded_sequence(
            x, lengths_cpu, batch_first=True, enforce_sorted=False,
        )
        _, (hn, _) = self.lstm(packed)

        # Use final hidden state of last LSTM layer
        last_hidden = hn[-1]  # [B, lstm_hidden]

        # Combine with rep features and classify
        combined = torch.cat([last_hidden, rep_features], dim=1)
        logits = self.fusion_mlp(combined)  # [B, output_dim]

        return logits
