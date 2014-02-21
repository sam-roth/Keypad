
class UserError(RuntimeError):
    '''
    An error that should be reported to the user.
    '''

class ExistentialError(UserError): 
    '''
    Something exists that prevents an operation from occuring, or something
    does not exist that is required for an operation.
    '''
    
class NoSuchCommandError(ExistentialError):
    '''
    No meaning is known for the command in this context.
    '''    

class HistoryExistentialError(ExistentialError):
    '''
    The requested information about the document's history does not exist.
    '''

class CantUndoError(HistoryExistentialError): pass
class CantRedoError(HistoryExistentialError): pass
class OldestHistoryItemError(HistoryExistentialError): pass
class NewestHistoryItemError(HistoryExistentialError): pass

class UnknownCommandError(ExistentialError): pass

class BufferModifiedError(UserError):
    '''
    Buffer was closed without being saved. To close a modified buffer use :destroy.
    '''


class NoBufferActiveError(ExistentialError): pass


