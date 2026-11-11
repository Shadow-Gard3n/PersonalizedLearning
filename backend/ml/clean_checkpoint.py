import torch
from pathlib import Path

def clean_model():
    # Adjust path if you place this script elsewhere
    checkpoint_path = Path(__file__).resolve().parent.parent / "saved_models" / "lstm_knowledge_tracer.pt"
    
    print(f"Loading {checkpoint_path}...")
    # We set weights_only=False here because we generated and trust this file locally
    checkpoint = torch.load(checkpoint_path, weights_only=False)
    
    # Force all NumPy types in the dictionary keys/values into native Python ints
    print("Normalizing question_to_idx mapping...")
    checkpoint["question_to_idx"] = {
        int(k): int(v) for k, v in checkpoint["question_to_idx"].items()
    }
    
    # Overwrite the file with the clean, safe-to-load dictionary
    torch.save(checkpoint, checkpoint_path)
    print("Checkpoint cleaned successfully!")

if __name__ == "__main__":
    clean_model()