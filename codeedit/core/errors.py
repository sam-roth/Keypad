
class UserError(RuntimeError):
    '''
    An error that should be reported to the user.
    '''

class ExistentialError(UserError): 
    '''
    Something exists that prevents an operation from occuring, or something
    does not exist that is required for an operation.
    '''

class HistoryExistentialError(ExistentialError):
    '''
    The requested information about the document's history does not exist.
    '''

class CantUndoError(HistoryExistentialError): pass
class CantRedoError(HistoryExistentialError): pass


