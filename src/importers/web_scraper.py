@staticmethod
    def _extract_euro_numbers(
        winning_numbers: Dict[str, Any],
    ) -> List[int]:
        """
        Extract the two Euro numbers.

        OPAP has used different field names in API responses over time,
        so the parser checks the known structures in a safe order.
        """
        possible_fields = (
            "sideClassNum",
            "sideClassNumbers",
            "sideClassList",
            "bonus",
        )

        for field_name in possible_fields:
            value = winning_numbers.get(field_name)

            if value is None:
                continue

            values: List[Any] = []

            # Handle nested dictionary structures like {"list": [6, 7]}
            if isinstance(value, dict):
                sub_list = value.get("list")
                if isinstance(sub_list, list):
                    values = sub_list
            elif isinstance(value, list):
                values = value
            else:
                values = [value]

            numbers: List[int] = []

            for item in values:
                try:
                    number = int(item)
                except (TypeError, ValueError):
                    continue

                if 1 <= number <= 12:
                    numbers.append(number)

            if len(numbers) >= 2:
                return sorted(numbers[:2])

        return []
