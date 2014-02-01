
from __future__ import print_function
import os
import clang.cindex
from . import clangutil, util
import textwrap


def printing(x):
    print(x)
    return x

def members(root, typename):
    '''
    Find all members of the type `typename` under the cursor `root`.
    
    :type root: clang.cindex.Cursor
    '''
    match = util.first(n for n in clangutil.walk_children(root)
                       if n.is_definition() and n.spelling == typename)
    return match.get_children()


def classes(root):

    for child in clangutil.walk_children(root):
        assert isinstance(child, clang.cindex.Cursor)

        if child.kind in (clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.CLASS_DECL):
            print(child.displayname)


def method_stub(cursor):
    '''
    Return a method stub for the item under the cursor provided.
    :type cursor: clang.cindex.Cursor
    :rtype: str
    '''

    template = '''\
    {return_type_name}{type_name}::{display_name}
    {{
    }}
    '''
    
    return_type_name = cursor.result_type.spelling
        
    if not return_type_name.endswith('*'):
        return_type_name += ' '

    return textwrap.dedent(template).format(
        return_type_name=return_type_name,
        type_name=cursor.lexical_parent.displayname,
        display_name=cursor.displayname
    )

def try_resolving_hier_name(cursor, hier_name):
    '''
    Resolve a hierarchical name, hier_name, of the form:
        hier_name ::= ident | ident '::' hier_name

    If the name does not exist under the cursor, try_resolving_hier_name
    returns `None`.

    :type cursor: clang.cindex.Cursor
    :rtype clang.cindex.Cursor:
    '''
    if hier_name is None:
        # base case
        return cursor 
    else:
        # recursive case 
        parts = hier_name.split('::', 1)
        if len(parts) == 2:
            first, rest = parts
        else:
            first, rest = parts[0], None
        
        for child in cursor.get_children():
            if child.spelling == first:
                result = try_resolving_hier_name(child, rest)
                if result is not None:
                    return result
        else:
            return None

def resolve_hier_name(cursor, hier_name):
    '''
    Resolve a hierarchical name, hier_name, of the form:
        hier_name ::= ident | ident '::' hier_name

    If the name does not exist under the cursor, resolve_hier_name
    raises `KeyError(hier_name)`.

    :type cursor: clang.cindex.Cursor
    :rtype clang.cindex.Cursor:
    '''

    result = try_resolving_hier_name(cursor, hier_name)
    if result is None:
        raise KeyError(hier_name)

    return result


def main():
    import sys, os
    os.chdir('/Users/Sam/Desktop/Projects/proper/')
    index = clang.cindex.Index.create()
    
    tu = index.parse(sys.argv[1], args=[
            '-DQT_CORE_LIB',
            '-DQT_GUI_LIB',
            '-DQT_NO_DEBUG',
            '-DQT_OPENGL_LIB',
            '-DQT_STATICPLUGIN',
            '-DQT_SVG_LIB',
            '-DQT_XML_LIB',
            '-g',
            '-O3',
            '-Wall',
            '-std=c++11',
            '-stdlib=libc++',
            '-isystem',
            '/opt/local/include',
            '-isystem',
            '/opt/local/include/QtOpenGL',
            '-isystem',
            '/opt/local/include/QtSvg',
            '-isystem',
            '/opt/local/include/QtGui',
            '-isystem',
            '/opt/local/include/QtXml',
            '-isystem',
            '/opt/local/include/QtCore',
            '-I/Users/Sam/Desktop/Projects/proper',
            '-Xpreprocessor',
            '-include-pch',
            '-Xpreprocessor',
            '/Users/Sam/Desktop/Projects/proper/Prefix.hpp.gch',
             '-Winvalid-pch',
#            '-xc++',
#            '-std=c++11',
#            '-stdlib=libc++',
#            '-I/opt/local/include', 
#            '-I/Users/Sam/Desktop/Projects/proper', 
#            '-include\\/Users/Sam/Desktop/Projects/proper/Prefix.hpp',
#            ''
        ],
        options=clang.cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE|
        clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )#,
        #options=clang.cindex.TranslationUnit.PARSE_INCOMPLETE)
    for diag in tu.diagnostics:
        assert isinstance(diag, clang.cindex.Diagnostic)
        print(diag, file=sys.stderr)
    #print('Found translation unit:', tu.spelling)
    rq_cursor = resolve_hier_name(tu.cursor, sys.argv[2])
    #print('Resolved hier name', sys.argv[2], ':', rq_cursor.spelling)
    print(method_stub(rq_cursor))
    #classes(tu.cursor)
    #for mbr in members(tu.cursor, sys.argv[2]):
    #    assert isinstance(mbr, clang.cindex.Cursor)
    #    if mbr.kind == clang.cindex.CursorKind.CXX_METHOD:
    #        print(method_stub(mbr))
        #print(mbr.kind, mbr.result_type.spelling, mbr.displayname)
