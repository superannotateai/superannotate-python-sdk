class BaseNamespace:
    """A group of SAClient methods exposed as an attribute, e.g. SAClient.explore.

    __init__ lives here rather than on the namespace, so TrackableMeta (applied to the
    namespace) does not report building one as a telemetry event.
    """

    #: Mixpanel events of the namespace's methods are reported as "<prefix>.<method>".
    TRACKING_PREFIX: str

    def __init__(self, controller):
        self.controller = controller
