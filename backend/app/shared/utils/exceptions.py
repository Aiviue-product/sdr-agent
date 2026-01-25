"""
Custom Exceptions for the SDR Application.

These exceptions provide clear, specific error handling for business logic scenarios.
"""


class ConcurrentModificationError(Exception):
    """
    Raised when an optimistic locking conflict is detected.
    
    This happens when two processes try to update the same record simultaneously.
    The second update will fail because the version has changed since it was read.
    
    Example:
        User A reads Lead #42 (version=1)
        User B reads Lead #42 (version=1)
        User A updates Lead #42 -> version becomes 2
        User B tries to update Lead #42 with version=1 -> ConcurrentModificationError
    
    Recovery:
        The caller should catch this exception, reload the fresh data, and retry
        or inform the user to refresh and try again.
    """
    def __init__(self, entity_type: str, entity_id: int, message: str = None):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.message = message or f"{entity_type} with ID {entity_id} was modified by another process. Please refresh and try again."
        super().__init__(self.message)


class EntityNotFoundError(Exception):
    """
    Raised when a requested entity does not exist in the database.
    """
    def __init__(self, entity_type: str, entity_id: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.message = f"{entity_type} with ID {entity_id} not found."
        super().__init__(self.message)
