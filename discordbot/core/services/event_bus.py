import asyncio
from typing import Dict, List, Callable, Any, Type

class EventBus:
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable[[Any], Any]]] = {}

    def subscribe(self, event_type: Type, handler: Callable[[Any], Any]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Any):
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"[EventBus Error] in handler {handler.__name__}: {e}")
