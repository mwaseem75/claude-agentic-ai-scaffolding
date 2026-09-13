def calculate_average(numbers):
    """Return the mean of `numbers`, or 0.0 if there are none.

    Accepts any iterable, including generators.
    """
    values = list(numbers) if numbers is not None else []
    if not values:
        return 0.0
    return sum(values) / len(values)


def get_user_name(user):
    """Return the user's name uppercased, or "" if it is missing or blank."""
    if not user:
        return ""
    name = user.get("name")
    if not isinstance(name, str):
        return ""
    return name.upper()
