
# as it turns out, the Clang API already does this when you use cursor.get_children()

def walk_children(cursor):
    '''
    Generator recursively finding children of `cursor`.
    :type cursor: clang.cindex.Cursor
    :rtype:       clang.cindex.Cursor
    '''

    for child in cursor.get_children():
        yield child

        for descendant in walk_children(child):
            yield descendant

    
