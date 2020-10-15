from typing import TYPE_CHECKING, Optional

from fffw.graph import base, VIDEO

if TYPE_CHECKING:
    StreamValidationTarget = base.Dest
else:
    StreamValidationTarget = object


class StreamValidationMixin(StreamValidationTarget):
    hardware: Optional[str]

    def connect_edge(self, edge: base.Edge) -> base.Edge:
        self.validate_edge_kind(edge)
        self.validate_edge_device(edge)
        return super().connect_edge(edge)

    def validate_edge_kind(self, edge: base.Edge) -> None:
        kind = getattr(self, 'kind', None)
        if kind is None:
            return
        if edge.kind != kind:
            # Audio filter can't handle video stream and so on
            raise ValueError(edge.kind)

    def validate_edge_device(self, edge: base.Edge) -> None:
        if edge.kind != VIDEO:
            return
        meta = edge.get_meta_data(self)
        if meta is None:
            return
        try:
            filter_hardware = getattr(self, 'hardware')
        except AttributeError:
            # no hardware restrictions for filter/codec
            return
        device = getattr(meta, 'device', None)
        edge_hardware = None if device is None else device.hardware
        if filter_hardware != edge_hardware:
            # A stream uploaded to a video card could not be processed with CPU
            # filter.
            raise ValueError(edge_hardware)
