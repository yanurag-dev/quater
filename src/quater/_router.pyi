from collections.abc import Mapping, Sequence

class RouteMatcher:
    def insert_route(
        self,
        method: str,
        path: str,
        route: object,
        params: Sequence[tuple[str, str]],
    ) -> None: ...
    def insert_allowed(
        self,
        path: str,
        methods: Sequence[str],
        params: Sequence[tuple[str, str]],
    ) -> None: ...
    def match_route(
        self,
        method: str,
        path: str,
    ) -> tuple[object, Mapping[str, object] | None] | None: ...
    def allowed_methods(self, path: str) -> tuple[str, ...] | None: ...
