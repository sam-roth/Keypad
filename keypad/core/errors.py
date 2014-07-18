

class UserError(RuntimeError):
    '''
    An error that should be reported to the user.
    '''

class ExistenceError(UserError): 
    '''
    Something exists that prevents an operation from occuring, or something
    does not exist that is required for an operation.
    '''

class NoSuchFileError(ExistenceError, FileNotFoundError):
    '''
    A file was not found and this error should be reported to the user.
    '''

class NoCodeModelError(ExistenceError):
    '''
    The operation requires a code model and there wasn't one.

    Note: The code model provides syntax highlighting, code completion,
    and other language-specific features.
    '''

class NoSuchCommandError(ExistenceError):
    '''
    No meaning is known for the command in this context.
    '''    

class HistoryExistenceError(ExistenceError):
    '''
    The requested information about the document's history does not exist.
    '''

class NameNotFoundError(ExistenceError):
    '''
    No declaration, assignment, or definition of the given name was found.
    '''

class CantUndoError(HistoryExistenceError): pass
class CantRedoError(HistoryExistenceError): pass
class OldestHistoryItemError(HistoryExistenceError): pass
class NewestHistoryItemError(HistoryExistenceError): pass

class UnknownCommandError(ExistenceError): pass

class BufferModifiedError(UserError):
    '''
    Buffer was closed without being saved. To close a modified buffer use :destroy.
    '''


class NoBufferActiveError(ExistenceError): pass


