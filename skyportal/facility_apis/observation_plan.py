from datetime import datetime, timedelta


def mma_interface():

    """A generic interface to MMA operations."""

    form_json_schema = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "default": str(datetime.utcnow()).replace("T", ""),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": str(datetime.utcnow() + timedelta(days=1)).replace("T", ""),
            },
            "program_id": {
                "type": "string",
                "enum": ["Partnership", "Caltech"],
                "default": "Partnership",
            },
            "subprogram_name": {
                "type": "string",
                "enum": ["GW", "GRB", "Neutrino", "SolarSystem", "Other"],
                "default": "GRB",
            },
            "scheduling_type": {
                "type": "string",
                "enum": ["block", "integrated"],
                "default": "block",
            },
            "scheduling_strategy": {
                "type": "string",
                "enum": ["tiling", "catalog"],
                "default": "tiling",
            },
            "exposure_time": {"type": "string", "default": "300"},
            "filters": {"type": "string", "default": "g,r,i"},
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
                "minimum": 1,
                "maximum": 3,
            },
            "integrated_probability": {
                "title": "Integrated Probability (0-100)",
                "type": "number",
                "default": 90.0,
                "minimum": 0,
                "maximum": 100,
            },
            "minimum_time_difference": {
                "title": "Minimum time difference [min] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "queue_name": {"type": "string", "default": f"ToO_{datetime.utcnow()}"},
        },
        "required": [
            "start_date",
            "end_date",
            "program_id",
            "filters",
            "queue_name",
            "subprogram_name",
            "scheduling_type",
            "scheduling_strategy",
            "exposure_time",
            "maximum_airmass",
            "integrated_probability",
            "minimum_time_difference",
        ],
    }

    ui_json_schema = {}

    return form_json_schema, ui_json_schema
