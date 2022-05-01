ITEM_EXPECTED_KEYS = [
    "name", "path", "url", "annotation_status", "annotator_email",
    "qa_email", "entropy_value", "createdAt", "updatedAt"
]

IMAGE_EXPECTED_KEYS = ITEM_EXPECTED_KEYS + ["segmentation_status", "prediction_status", "approval_status"]

__all__ = [
    ITEM_EXPECTED_KEYS,
    IMAGE_EXPECTED_KEYS
]
