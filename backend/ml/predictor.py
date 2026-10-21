from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence


class LSTMKnowledgeTracer(nn.Module):
    def __init__(
        self,
        num_questions,
        embedding_dim=64,
        hidden_dim=64,
    ):
        super().__init__()

        self.question_embedding = nn.Embedding(
            num_questions,
            embedding_dim,
            padding_idx=0,
        )

        self.response_embedding = nn.Embedding(
            3,
            embedding_dim,
            padding_idx=2,
        )

        self.lstm = nn.LSTM(
            input_size=embedding_dim * 2,
            hidden_size=hidden_dim,
            batch_first=True,
        )

        self.output = nn.Sequential(
            nn.Linear(hidden_dim + embedding_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, history, target_question, lengths):
        question_ids = history[:, :, 0]
        responses = history[:, :, 1]

        question_embeddings = self.question_embedding(question_ids)

        response_ids = responses.clone()
        response_ids[question_ids == 0] = 2

        response_embeddings = self.response_embedding(response_ids)

        x = torch.cat(
            [question_embeddings, response_embeddings],
            dim=-1,
        )

        packed_x = pack_padded_sequence(
            x,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )

        _, (hidden, _) = self.lstm(packed_x)

        history_representation = hidden[-1]
        target_embedding = self.question_embedding(target_question)

        combined = torch.cat(
            [history_representation, target_embedding],
            dim=-1,
        )

        return self.output(combined).squeeze(-1)


class KnowledgeTracerPredictor:
    def __init__(self, checkpoint_path):
        self.device = torch.device("cpu")
        checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.is_file():
            raise FileNotFoundError(
                f"LSTM checkpoint not found: {checkpoint_path}"
            )

        # Allow only the NumPy types identified by the checkpoint
        # loading errors. Keep weights_only=True.
        safe_numpy_types = [
            np._core.multiarray.scalar,
            np.dtype,
            type(np.dtype(np.float64)),
        ]

        with torch.serialization.safe_globals(safe_numpy_types):
            checkpoint = torch.load(
                checkpoint_path,
                map_location=self.device,
                weights_only=True,
            )

        if not isinstance(checkpoint, dict):
            raise ValueError(
                "Invalid checkpoint: expected a dictionary."
            )

        required_keys = {
            "model_state_dict",
            "num_questions",
            "embedding_dim",
            "hidden_dim",
            "max_seq_len",
            "question_to_idx",
        }

        missing_keys = required_keys - checkpoint.keys()

        if missing_keys:
            raise ValueError(
                f"Checkpoint is missing keys: {sorted(missing_keys)}"
            )

        self.max_seq_len = int(checkpoint["max_seq_len"])
        self.question_to_idx = checkpoint["question_to_idx"]

        self.model = LSTMKnowledgeTracer(
            num_questions=int(checkpoint["num_questions"]),
            embedding_dim=int(checkpoint["embedding_dim"]),
            hidden_dim=int(checkpoint["hidden_dim"]),
        ).to(self.device)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

    @torch.inference_mode()
    def predict(self, history, target_question_id):
        """
        Args:
            history:
                List of (original_question_id, answered_correctly) pairs.
                answered_correctly must be 0 or 1.

            target_question_id:
                Original question ID from the Riiid dataset.

        Returns:
            Dictionary containing probabilities of correct and
            incorrect answers.
        """

        if not history:
            raise ValueError(
                "At least one previous interaction is required."
            )

        if target_question_id not in self.question_to_idx:
            raise ValueError(
                f"Unknown target question ID: {target_question_id}"
            )

        # Keep the most recent interactions.
        history = history[-self.max_seq_len:]

        encoded_history = []

        for question_id, correct in history:
            if question_id not in self.question_to_idx:
                raise ValueError(
                    f"Unknown history question ID: {question_id}"
                )

            if correct not in (0, 1):
                raise ValueError(
                    "Each answer must be represented by 0 or 1."
                )

            encoded_history.append(
                (
                    self.question_to_idx[question_id],
                    int(correct),
                )
            )

        length = len(encoded_history)

        # Right-padding, matching the existing training format.
        history_tensor = torch.zeros(
            (1, self.max_seq_len, 2),
            dtype=torch.long,
            device=self.device,
        )

        for index, (question_idx, correct) in enumerate(
            encoded_history
        ):
            history_tensor[0, index, 0] = question_idx
            history_tensor[0, index, 1] = correct

        target_idx = self.question_to_idx[target_question_id]

        logits = self.model(
            history_tensor,
            torch.tensor(
                [target_idx],
                dtype=torch.long,
                device=self.device,
            ),
            torch.tensor(
                [length],
                dtype=torch.long,
                device=self.device,
            ),
        )

        probability_correct = torch.sigmoid(logits).item()

        return {
            "probability_correct": probability_correct,
            "probability_incorrect": 1.0 - probability_correct,
        }
