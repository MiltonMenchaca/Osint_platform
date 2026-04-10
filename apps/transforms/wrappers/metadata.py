import json
import logging
from typing import Any, Dict, List

from .base import BaseWrapper

logger = logging.getLogger(__name__)


class ExifToolWrapper(BaseWrapper):
    def get_tool_name(self) -> str:
        return "exiftool"

    def get_supported_input_types(self) -> List[str]:
        return ["image", "document", "file", "url", "other"]

    def get_supported_output_types(self) -> List[str]:
        return ["other"]

    def execute(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self._validate_input(input_data)
        input_type = input_data["type"]
        input_value = str(input_data["value"]).strip()

        timeout = int(kwargs.get("timeout", 60))

        # If it's a URL, we might need to download it first,
        # but for now assume input_value is a file path if it's a file/image
        # If it is a URL, we assume the user/tool handling logic downloads it.
        # However, BaseWrapper assumes local execution.
        # TODO: Add logic to handle URL download if not local file.

        command = [self.tool_path, "-j", input_value]
        result = self._run_command(command, timeout=timeout)

        metadata_results: List[Dict[str, Any]] = []
        try:
            raw_output = result.get("stdout") or "[]"
            if raw_output.strip().startswith("["):
                data = json.loads(raw_output)
                if data and isinstance(data, list):
                    file_info = data[0]
                    # Convert to flat properties
                    properties = {k: v for k, v in file_info.items()}

                    metadata_results.append(
                        {
                            "type": "other",
                            "value": f"Metadata: {input_value}",
                            "source": "exiftool",
                            "confidence": 1.0,
                            "properties": properties,
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to parse exiftool output: {e}")

        execution_info = {
            "input_type": input_type,
            "input_value": input_value,
            "execution_time": result["execution_time"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "command": result["command"],
        }
        return self._format_output(metadata_results, execution_info)
