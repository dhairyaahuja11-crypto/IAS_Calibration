import json
from datetime import datetime
from pathlib import Path

from utils.model_encryption import get_default_encryption_key, save_encrypted_model
from services.project_service import ProjectService


class ModelManagementService:
    """Persist and retrieve saved calibration models from analysis_results."""

    TABLE_COLUMNS = [
        "model_id",
        "model_name",
        "project_name",
        "measurement_index",
        "instrument",
        "wavelength_points",
        "calibration_count",
        "validation_count",
        "intercept_data",
        "average_enable",
        "pretreatment_summary",
        "intercept_after_pretreatment",
        "dimension_reduction_algorithm",
        "dimension",
        "analysis_algorithm",
        "analysis_algorithm_parameters",
        "user_id",
        "creation_time",
    ]

    @staticmethod
    def get_results_directory() -> Path:
        base_dir = Path(__file__).parent.parent
        results_dir = base_dir / "analysis_results"
        results_dir.mkdir(exist_ok=True)
        return results_dir

    @staticmethod
    def _load_json(path: Path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    @staticmethod
    def _is_saved_model(data: dict) -> bool:
        if not isinstance(data, dict):
            return False
        if data.get("record_type") == "saved_model":
            return True
        return "rows" in data and "metrics" in data and "algorithm" in data

    @staticmethod
    def _parse_created_at(data: dict, path: Path) -> datetime:
        creation_time = str(data.get("creation_time", "")).strip()
        if creation_time:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%d %B %Y %H:%M:%S"):
                try:
                    return datetime.strptime(creation_time, fmt)
                except ValueError:
                    continue

        timestamp = str(data.get("timestamp", "")).strip()
        if timestamp:
            try:
                return datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            except ValueError:
                pass

        return datetime.fromtimestamp(path.stat().st_mtime)

    @staticmethod
    def _stringify(value):
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _resolve_project_instrument(data: dict) -> str:
        """Fallback to the project's stored instrument when model JSON metadata is blank."""
        project_id = data.get("project_id")
        if project_id:
            project = ProjectService.get_project_by_id(str(project_id).strip())
            if project:
                instrument = project.get("instrument")
                if instrument is not None and str(instrument).strip():
                    return str(instrument).strip()

        project_name = data.get("project_name")
        if project_name:
            try:
                projects = ProjectService.get_projects_by_filters(
                    date_from=None,
                    date_to=None,
                    project_name=str(project_name).strip()
                )
                for project in projects:
                    if str(project.get("project_name", "")).strip() == str(project_name).strip():
                        instrument = project.get("instrument")
                        if instrument is not None and str(instrument).strip():
                            return str(instrument).strip()
            except Exception:
                pass

        return ""

    @staticmethod
    def build_model_record(data: dict, path: Path) -> dict:
        rows = data.get("rows") or []
        first_row = rows[0] if rows else {}
        created_at = ModelManagementService._parse_created_at(data, path)

        dimension_value = data.get("dimension")
        if dimension_value in (None, ""):
            dimension_value = data.get("best_n_components", "")

        instrument = data.get("instrument")
        if not instrument:
            instrument = first_row.get("instrument", "")
        if not instrument:
            instrument = ModelManagementService._resolve_project_instrument(data)

        measurement_index = data.get("measurement_index")
        if not measurement_index:
            measurement_index = first_row.get("property_name", "")

        wavelength_points = data.get("wavelength_points")
        if wavelength_points in (None, ""):
            wavelength_points = first_row.get("wavelength_points", "")

        user_id = data.get("user_id")
        if not user_id:
            user_id = first_row.get("user_id", "")

        record = {
            "model_id": ModelManagementService._stringify(
                data.get("model_id") or data.get("timestamp") or path.stem
            ),
            "model_name": ModelManagementService._stringify(
                data.get("model_name") or data.get("project_name") or path.stem
            ),
            "project_name": ModelManagementService._stringify(data.get("project_name", "")),
            "measurement_index": ModelManagementService._stringify(measurement_index),
            "instrument": ModelManagementService._stringify(instrument),
            "wavelength_points": ModelManagementService._stringify(wavelength_points),
            "calibration_count": ModelManagementService._stringify(
                data.get("calibration_count", len(rows) if data.get("data_scope") == "calibration set" else "")
            ),
            "validation_count": ModelManagementService._stringify(data.get("validation_count", "")),
            "intercept_data": ModelManagementService._stringify(data.get("intercept_data", "")),
            "average_enable": ModelManagementService._stringify(data.get("average_enable", "")),
            "pretreatment_summary": ModelManagementService._stringify(data.get("pretreatment_summary", "")),
            "intercept_after_pretreatment": ModelManagementService._stringify(
                data.get("intercept_after_pretreatment", "")
            ),
            "dimension_reduction_algorithm": ModelManagementService._stringify(
                data.get("dimension_reduction_algorithm", data.get("algorithm", ""))
            ),
            "dimension": ModelManagementService._stringify(dimension_value),
            "analysis_algorithm": ModelManagementService._stringify(data.get("analysis_algorithm", data.get("algorithm", ""))),
            "analysis_algorithm_parameters": ModelManagementService._stringify(
                data.get("analysis_algorithm_parameters", "")
            ),
            "user_id": ModelManagementService._stringify(user_id),
            "creation_time": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "_path": str(path),
            "_created_at": created_at,
        }
        return record

    @staticmethod
    def list_models() -> list[dict]:
        results_dir = ModelManagementService.get_results_directory()
        records = []

        for path in results_dir.glob("*.json"):
            data = ModelManagementService._load_json(path)
            if not ModelManagementService._is_saved_model(data):
                continue
            records.append(ModelManagementService.build_model_record(data, path))

        records.sort(key=lambda item: item["_created_at"], reverse=True)
        return records

    @staticmethod
    def load_model(path: str):
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"Model file not found: {target}")
        with open(target, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def save_model(data: dict, model_name: str) -> Path:
        results_dir = ModelManagementService.get_results_directory()
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in model_name).strip("_")
        if not safe_name:
            safe_name = "model"

        filename = f"saved_model_{safe_name}_{data['timestamp']}.json"
        path = results_dir / filename
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, default=str)
        return path

    @staticmethod
    def export_model(path: str, export_path: str | None = None) -> Path:
        model_data = ModelManagementService.load_model(path)
        deployable_model = model_data.get("deployable_model") or {}
        if not deployable_model:
            raise ValueError(
                "This saved model does not contain deployable PLS parameters yet. "
                "Please re-run analysis and save the model again before exporting."
            )

        model_name = str(
            deployable_model.get("model_name")
            or model_data.get("model_name")
            or model_data.get("project_name")
            or "model"
        )
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in model_name).strip("_") or "model"

        target = Path(export_path) if export_path else (ModelManagementService.get_results_directory() / f"{safe_name}.agnextpro")
        if target.suffix.lower() != ".agnextpro":
            target = target.with_suffix(".agnextpro")

        encryption_key = get_default_encryption_key()
        return save_encrypted_model(target, deployable_model, encryption_key)

    @staticmethod
    def delete_model(path: str) -> None:
        target = Path(path)
        if target.exists():
            target.unlink()
