from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from utils.model_encryption import get_default_encryption_key, load_encrypted_model


def predict_from_spectrum(model_path: str | Path, spectrum: np.ndarray) -> float:
    load_dotenv()
    key = get_default_encryption_key()
    model = load_encrypted_model(model_path, key)

    coefficients = np.array(model["coefficients"], dtype=float)
    intercept = float(model.get("intercept", 0.0))
    spectrum = np.array(spectrum, dtype=float)

    if spectrum.shape[0] != coefficients.shape[0]:
        raise ValueError(
            f"Spectrum length {spectrum.shape[0]} does not match model length {coefficients.shape[0]}."
        )

    return float(np.dot(spectrum, coefficients) + intercept)


if __name__ == "__main__":
    example_spectrum = np.array([0.1, 0.2, 0.3], dtype=float)
    prediction = predict_from_spectrum("your_model.agnextpro", example_spectrum)
    print(f"Prediction: {prediction:.6f}")
