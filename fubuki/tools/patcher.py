class Patcher:
    """
    Utility class to facilitate monkeypatching... stuff

    Initialise class with a target, which can be a module, or a class, etc
    """

    def __init__(self, target):
        self.target = target
        self._patches = {}
        self._original = {}
        for name, attr in map(
                lambda _attr: (_attr, getattr(target, _attr)),
                dir(target)):
            self._original[name] = attr

    def attribute(self, value=None, *, name=None):
        """
        Patch an attribute onto the target.

        This method can be used as a normal function or as a decorator.

        If `value` is given, then that value will be patched, under
        the name parameter, or its __name__ value

        This can also be used to decorate a function or a class.
        It can be used to add methods to classes, classes to modules, etc.

        Note that by itself, this method only stores the new attribute
        internally. The patch() method applies the patch itself.
        """
        if value is not None:
            self._patches[getattr(value, "__name__", name)] = value
            return

        def inner(attr):
            self._patches[getattr(attr, "__name__", name)] = attr
        return inner

    def patch(self) -> None:
        """
        Applies all staged patches to the target.
        """
        for name, attr in self._patches.items():
            setattr(self.target, name, attr)

    def revert(self) -> None:
        """
        Reverts the target back to its state at the time that the
        Patcher was instantiated.

        Any *new* attributes will be removed, and all overridden
        attributes will be reverted.
        """
        for name in self._patches.keys():
            delattr(self.target, name)
        for name, attr in self._original.items():
            try:
                setattr(self.target, name, attr)
            except (TypeError, AttributeError):
                continue
