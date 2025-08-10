"""AnyType for wildcard input matching in ComfyUI nodes."""


class AnyType(str):
    """A special type that matches any input type in ComfyUI."""

    def __ne__(self, other):
        return False
