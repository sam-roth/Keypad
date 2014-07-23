
import re
import pathlib

from keypad.api import *
from keypad.core.attributed_string import AttributedString
from keypad.abstract.code import IndentRetainingCodeModel, Indent, AbstractCompletionResults
from keypad.core.executors import future_wrap
from keypad.core.fuzzy import FuzzyMatcher

from keypad.core.syntaxlib import (regex, region, keyword,
                                 lazy, SyntaxHighlighter)


from keypad.control import cmdline_completer
from keypad.util import time_limited


# from keypad.plugins.semantics.syntaxlib import regex, region, keyword
# from keypad.plugins.semantics.syntax import lazy, SyntaxHighlighter

cmake_builtins = '''
add_compile_options add_custom_command add_custom_target add_definitions
add_dependencies add_executable add_library add_subdirectory add_test
aux_source_directory break build_command cmake_host_system_information
cmake_minimum_required cmake_policy configure_file create_test_sourcelist
define_property elseif else enable_language enable_testing endforeach
endfunction endif endmacro endwhile execute_process export file find_file
find_library find_package find_path find_program fltk_wrap_ui foreach function
get_cmake_property get_directory_property get_filename_component get_property
get_source_file_property get_target_property get_test_property if
include_directories include_external_msproject include_regular_expression
include install link_directories list load_cache load_command macro
mark_as_advanced math message option project qt_wrap_cpp qt_wrap_ui
remove_definitions return separate_arguments set_directory_properties
set_property set set_source_files_properties set_target_properties
set_tests_properties site_name source_group string target_compile_definitions
target_compile_options target_include_directories target_link_libraries
try_compile try_run unset variable_watch while
'''.split()

@lazy
def lexer():
    KEYWORD     = dict(lexcat='keyword')
    ESCAPE      = dict(lexcat='escape')
    STRING      = dict(lexcat='literal')
    NUMBER      = dict(lexcat='literal')
    COMMENT     = dict(lexcat='comment')
    DOC         = dict(lexcat='docstring')
    PREPROC     = dict(lexcat='preprocessor')
    TODO        = dict(lexcat='todo')
    TYPE        = dict(lexcat='type')
    FUNCTION    = dict(lexcat='function')


    builtin = keyword(cmake_builtins, KEYWORD, caseless=True)

    var = region(guard=regex(r'\${'),
                 exit=regex(r'}'),
                 contains=[regex(r'[^}]+', PREPROC)],
                 attrs=ESCAPE)

    dqstring = region(guard=regex(r'"'),
                      exit=regex(r'"'),
                      contains=[regex(r'\\.', ESCAPE),
                                var],
                      attrs=STRING)

    func = regex(r'\b(?P<body>\w+)([ \t]*)(?=\()', FUNCTION)

    comment = region(guard=regex('#'),
                     exit=regex('$'),
                     contains=[keyword(['todo', 'hack', 'xxx', 'fixme'], TODO, caseless=True)],
                     attrs=COMMENT)

    return region(guard=None,
                  exit=None,
                  contains=[var, dqstring, func, comment, builtin])



# def get_filenames(root):
#     root = pathlib.Path(root)

cmake_vars = '''
CMAKE_ARGC CMAKE_ARGV0 CMAKE_AR CMAKE_BINARY_DIR CMAKE_BUILD_TOOL
CMAKE_CACHEFILE_DIR CMAKE_CACHE_MAJOR_VERSION CMAKE_CACHE_MINOR_VERSION
CMAKE_CACHE_PATCH_VERSION CMAKE_CFG_INTDIR CMAKE_COMMAND CMAKE_CROSSCOMPILING
CMAKE_CTEST_COMMAND CMAKE_CURRENT_BINARY_DIR CMAKE_CURRENT_LIST_DIR
CMAKE_CURRENT_LIST_FILE CMAKE_CURRENT_LIST_LINE CMAKE_CURRENT_SOURCE_DIR
CMAKE_DL_LIBS CMAKE_EDIT_COMMAND CMAKE_EXECUTABLE_SUFFIX CMAKE_EXTRA_GENERATOR
CMAKE_EXTRA_SHARED_LIBRARY_SUFFIXES CMAKE_GENERATOR CMAKE_GENERATOR_TOOLSET
CMAKE_HOME_DIRECTORY CMAKE_IMPORT_LIBRARY_PREFIX CMAKE_IMPORT_LIBRARY_SUFFIX
CMAKE_JOB_POOL_COMPILE CMAKE_JOB_POOL_LINK CMAKE_LINK_LIBRARY_SUFFIX
CMAKE_MAJOR_VERSION CMAKE_MAKE_PROGRAM CMAKE_MINIMUM_REQUIRED_VERSION
CMAKE_MINOR_VERSION CMAKE_PARENT_LIST_FILE CMAKE_PATCH_VERSION
CMAKE_PROJECT_NAME CMAKE_RANLIB CMAKE_ROOT CMAKE_SCRIPT_MODE_FILE
CMAKE_SHARED_LIBRARY_PREFIX CMAKE_SHARED_LIBRARY_SUFFIX
CMAKE_SHARED_MODULE_PREFIX CMAKE_SHARED_MODULE_SUFFIX CMAKE_SIZEOF_VOID_P
CMAKE_SKIP_INSTALL_RULES CMAKE_SKIP_RPATH CMAKE_SOURCE_DIR
CMAKE_STANDARD_LIBRARIES CMAKE_STATIC_LIBRARY_PREFIX
CMAKE_STATIC_LIBRARY_SUFFIX CMAKE_TOOLCHAIN_FILE CMAKE_TWEAK_VERSION
CMAKE_VERBOSE_MAKEFILE CMAKE_VERSION CMAKE_VS_DEVENV_COMMAND
CMAKE_VS_INTEL_Fortran_PROJECT_VERSION CMAKE_VS_MSBUILD_COMMAND
CMAKE_VS_MSDEV_COMMAND CMAKE_VS_PLATFORM_TOOLSET CMAKE_XCODE_PLATFORM_TOOLSET
PROJECT_BINARY_DIR PROJECT-NAME_BINARY_DIR PROJECT_NAME
PROJECT-NAME_SOURCE_DIR PROJECT-NAME_VERSION PROJECT-NAME_VERSION_MAJOR
PROJECT-NAME_VERSION_MINOR PROJECT-NAME_VERSION_PATCH
PROJECT-NAME_VERSION_TWEAK PROJECT_SOURCE_DIR PROJECT_VERSION
PROJECT_VERSION_MAJOR PROJECT_VERSION_MINOR PROJECT_VERSION_PATCH
PROJECT_VERSION_TWEAK BUILD_SHARED_LIBS CMAKE_ABSOLUTE_DESTINATION_FILES
CMAKE_APPBUNDLE_PATH CMAKE_AUTOMOC_RELAXED_MODE CMAKE_BACKWARDS_COMPATIBILITY
CMAKE_BUILD_TYPE CMAKE_COLOR_MAKEFILE CMAKE_CONFIGURATION_TYPES
CMAKE_DEBUG_TARGET_PROPERTIES CMAKE_DISABLE_FIND_PACKAGE_PackageName
CMAKE_ERROR_DEPRECATED CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION
CMAKE_SYSROOT CMAKE_FIND_LIBRARY_PREFIXES CMAKE_FIND_LIBRARY_SUFFIXES
CMAKE_FIND_NO_INSTALL_PREFIX CMAKE_FIND_PACKAGE_WARN_NO_MODULE
CMAKE_FIND_ROOT_PATH CMAKE_FIND_ROOT_PATH_MODE_INCLUDE
CMAKE_FIND_ROOT_PATH_MODE_LIBRARY CMAKE_FIND_ROOT_PATH_MODE_PACKAGE
CMAKE_FIND_ROOT_PATH_MODE_PROGRAM CMAKE_FRAMEWORK_PATH CMAKE_IGNORE_PATH
CMAKE_INCLUDE_PATH CMAKE_INCLUDE_DIRECTORIES_BEFORE
CMAKE_INCLUDE_DIRECTORIES_PROJECT_BEFORE CMAKE_INSTALL_DEFAULT_COMPONENT_NAME
CMAKE_INSTALL_PREFIX CMAKE_LIBRARY_PATH CMAKE_MFC_FLAG CMAKE_MODULE_PATH
CMAKE_NOT_USING_CONFIG_FLAGS CMAKE_POLICY_DEFAULT_CMPNNNN
CMAKE_POLICY_WARNING_CMPNNNN CMAKE_PREFIX_PATH CMAKE_PROGRAM_PATH
CMAKE_PROJECT_PROJECT-NAME_INCLUDE CMAKE_SKIP_INSTALL_ALL_DEPENDENCY
CMAKE_STAGING_PREFIX CMAKE_SYSTEM_IGNORE_PATH CMAKE_SYSTEM_INCLUDE_PATH
CMAKE_SYSTEM_LIBRARY_PATH CMAKE_SYSTEM_PREFIX_PATH CMAKE_SYSTEM_PROGRAM_PATH
CMAKE_USER_MAKE_RULES_OVERRIDE CMAKE_WARN_DEPRECATED
CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION APPLE BORLAND CMAKE_CL_64
CMAKE_COMPILER_2005 CMAKE_HOST_APPLE CMAKE_HOST_SYSTEM_NAME
CMAKE_HOST_SYSTEM_PROCESSOR CMAKE_HOST_SYSTEM CMAKE_HOST_SYSTEM_VERSION
CMAKE_HOST_UNIX CMAKE_HOST_WIN32 CMAKE_LIBRARY_ARCHITECTURE_REGEX
CMAKE_LIBRARY_ARCHITECTURE CMAKE_OBJECT_PATH_MAX CMAKE_SYSTEM_NAME
CMAKE_SYSTEM_PROCESSOR CMAKE_SYSTEM CMAKE_SYSTEM_VERSION CYGWIN ENV MSVC10
MSVC11 MSVC12 MSVC60 MSVC70 MSVC71 MSVC80 MSVC90 MSVC_IDE MSVC MSVC_VERSION
UNIX WIN32 XCODE_VERSION CMAKE_ARCHIVE_OUTPUT_DIRECTORY
CMAKE_AUTOMOC_MOC_OPTIONS CMAKE_AUTOMOC CMAKE_AUTORCC CMAKE_AUTORCC_OPTIONS
CMAKE_AUTOUIC CMAKE_AUTOUIC_OPTIONS CMAKE_BUILD_WITH_INSTALL_RPATH
CMAKE_CONFIG_POSTFIX CMAKE_DEBUG_POSTFIX CMAKE_EXE_LINKER_FLAGS_CONFIG
CMAKE_EXE_LINKER_FLAGS CMAKE_Fortran_FORMAT CMAKE_Fortran_MODULE_DIRECTORY
CMAKE_GNUtoMS CMAKE_INCLUDE_CURRENT_DIR_IN_INTERFACE CMAKE_INCLUDE_CURRENT_DIR
CMAKE_INSTALL_NAME_DIR CMAKE_INSTALL_RPATH CMAKE_INSTALL_RPATH_USE_LINK_PATH
CMAKE_LANG_VISIBILITY_PRESET CMAKE_LIBRARY_OUTPUT_DIRECTORY
CMAKE_LIBRARY_PATH_FLAG CMAKE_LINK_DEF_FILE_FLAG CMAKE_LINK_DEPENDS_NO_SHARED
CMAKE_LINK_INTERFACE_LIBRARIES CMAKE_LINK_LIBRARY_FILE_FLAG
CMAKE_LINK_LIBRARY_FLAG CMAKE_MACOSX_BUNDLE CMAKE_MACOSX_RPATH
CMAKE_MAP_IMPORTED_CONFIG_CONFIG CMAKE_MODULE_LINKER_FLAGS_CONFIG
CMAKE_MODULE_LINKER_FLAGS CMAKE_NO_BUILTIN_CHRPATH
CMAKE_NO_SYSTEM_FROM_IMPORTED CMAKE_OSX_ARCHITECTURES
CMAKE_OSX_DEPLOYMENT_TARGET CMAKE_OSX_SYSROOT CMAKE_PDB_OUTPUT_DIRECTORY
CMAKE_PDB_OUTPUT_DIRECTORY_CONFIG CMAKE_POSITION_INDEPENDENT_CODE
CMAKE_RUNTIME_OUTPUT_DIRECTORY CMAKE_SHARED_LINKER_FLAGS_CONFIG
CMAKE_SHARED_LINKER_FLAGS CMAKE_SKIP_BUILD_RPATH CMAKE_SKIP_INSTALL_RPATH
CMAKE_STATIC_LINKER_FLAGS_CONFIG CMAKE_STATIC_LINKER_FLAGS
CMAKE_TRY_COMPILE_CONFIGURATION CMAKE_USE_RELATIVE_PATHS
CMAKE_VISIBILITY_INLINES_HIDDEN CMAKE_WIN32_EXECUTABLE EXECUTABLE_OUTPUT_PATH
LIBRARY_OUTPUT_PATH
CMAKE_COMPILER_IS_GNULANG CMAKE_Fortran_MODDIR_DEFAULT
CMAKE_Fortran_MODDIR_FLAG CMAKE_Fortran_MODOUT_FLAG CMAKE_INTERNAL_PLATFORM_ABI
CMAKE_CXX_ARCHIVE_APPEND CMAKE_CXX_ARCHIVE_CREATE CMAKE_CXX_ARCHIVE_FINISH
CMAKE_CXX_COMPILE_OBJECT CMAKE_CXX_COMPILER_ABI CMAKE_CXX_COMPILER_ID
CMAKE_CXX_COMPILER_LOADED CMAKE_CXX_COMPILER
CMAKE_CXX_COMPILER_EXTERNAL_TOOLCHAIN CMAKE_CXX_COMPILER_TARGET
CMAKE_CXX_COMPILER_VERSION CMAKE_CXX_CREATE_SHARED_LIBRARY
CMAKE_CXX_CREATE_SHARED_MODULE CMAKE_CXX_CREATE_STATIC_LIBRARY
CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_MINSIZEREL CMAKE_CXX_FLAGS_RELEASE
CMAKE_CXX_FLAGS_RELWITHDEBINFO CMAKE_CXX_FLAGS CMAKE_CXX_IGNORE_EXTENSIONS
CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES CMAKE_CXX_IMPLICIT_LINK_DIRECTORIES
CMAKE_CXX_IMPLICIT_LINK_FRAMEWORK_DIRECTORIES CMAKE_CXX_IMPLICIT_LINK_LIBRARIES
CMAKE_CXX_LIBRARY_ARCHITECTURE CMAKE_CXX_LINKER_PREFERENCE_PROPAGATES
CMAKE_CXX_LINKER_PREFERENCE CMAKE_CXX_LINK_EXECUTABLE
CMAKE_CXX_OUTPUT_EXTENSION CMAKE_CXX_PLATFORM_ID CMAKE_CXX_SIMULATE_ID
CMAKE_CXX_SIMULATE_VERSION CMAKE_CXX_SIZEOF_DATA_PTR
CMAKE_CXX_SOURCE_FILE_EXTENSIONS CMAKE_USER_MAKE_RULES_OVERRIDE_CXX
CMAKE_C_ARCHIVE_APPEND CMAKE_C_ARCHIVE_CREATE CMAKE_C_ARCHIVE_FINISH
CMAKE_C_COMPILE_OBJECT CMAKE_C_COMPILER_ABI CMAKE_C_COMPILER_ID
CMAKE_C_COMPILER_LOADED CMAKE_C_COMPILER CMAKE_C_COMPILER_EXTERNAL_TOOLCHAIN
CMAKE_C_COMPILER_TARGET CMAKE_C_COMPILER_VERSION CMAKE_C_CREATE_SHARED_LIBRARY
CMAKE_C_CREATE_SHARED_MODULE CMAKE_C_CREATE_STATIC_LIBRARY CMAKE_C_FLAGS_DEBUG
CMAKE_C_FLAGS_MINSIZEREL CMAKE_C_FLAGS_RELEASE CMAKE_C_FLAGS_RELWITHDEBINFO
CMAKE_C_FLAGS CMAKE_C_IGNORE_EXTENSIONS CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES
CMAKE_C_IMPLICIT_LINK_DIRECTORIES CMAKE_C_IMPLICIT_LINK_FRAMEWORK_DIRECTORIES
CMAKE_C_IMPLICIT_LINK_LIBRARIES CMAKE_C_LIBRARY_ARCHITECTURE
CMAKE_C_LINKER_PREFERENCE_PROPAGATES CMAKE_C_LINKER_PREFERENCE
CMAKE_C_LINK_EXECUTABLE CMAKE_C_OUTPUT_EXTENSION CMAKE_C_PLATFORM_ID
CMAKE_C_SIMULATE_ID CMAKE_C_SIMULATE_VERSION CMAKE_C_SIZEOF_DATA_PTR
CMAKE_C_SOURCE_FILE_EXTENSIONS CMAKE_USER_MAKE_RULES_OVERRIDE_C
'''.split()


class CMakeCodeModel(IndentRetainingCodeModel):
    statement_start = '('
    reindent_triggers = ')'
    indent_after = r'\(\s*$'
    dedent_before = r'^\s*\)\s*$'
    completion_triggers = []


    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.__builtins = [(AttributedString(x), ) for x in cmake_builtins]
        self.__builtins += [(AttributedString(x), ) for x in cmake_vars]

    def alignment_column(self, pos, *, timeout_ms=50):
        return None

    @future_wrap
    def completions_async(self, pos):
        c = Cursor(self.buffer).move(pos)
        text_to_pos = c.line.text[:c.x]

        for x, ch in reversed(list(enumerate(text_to_pos))):
            if not ch.isalnum() and ch not in '_/.-':
                x += 1
                break
        else:
            x = 0

        pos = c.y, x

        compls = [(AttributedString(s), ) 
                  for s in sorted(frozenset(re.findall(r'[\w\d_]+',
                                                       self.buffer.text)))]


        try:
            if self.path:
                working = pathlib.Path(self.path).parent
            else:
                working = None

            itr = cmdline_completer.get_filename_completions(text_to_pos, working)
            filename_compls = [(AttributedString(x), )
                               for x in time_limited(itr, ms=100)]
        except errors.NoSuchFileError:
            filename_compls = []

        return CMakeCompletionResults(pos, compls + filename_compls + self.__builtins)

    def highlight(self):
        highlighter = SyntaxHighlighter(
            'keypad.plugins.cmake',
            lexer(),
            dict(lexcat=None)
        )

        highlighter.highlight_buffer(self.buffer)

class CMakeCompletionResults(AbstractCompletionResults):

    def __init__(self, token_start, results):
        super().__init__(token_start)

        self.results = results
        self.filter()        

    @future_wrap
    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
        AttributedString.        
        '''

        return []

    @property
    def rows(self):
        '''
        Return a list of tuples of AttributedString containing the contents of 
        each column for each row in the completion results.
        '''
        return self._filtered.rows


    def text(self, index):
        '''
        Return the text that should be inserted for the given completion.
        '''
        return self._filtered.rows[index][0].text


    def filter(self, text=''):
        '''
        Filter the completion results using the given text.
        '''

        self._filtered = FuzzyMatcher(text).filter(self.results, lambda item: item[0].text)
        self._filtered.sort(lambda item: len(item[0].text))


    def dispose(self):
        pass


@register_plugin
class CMakePlugin(Plugin):
    name = 'CMake Code Model'
    author = 'Sam Roth'
    version = '2014.06.1'

    def attach(self):
        Filetype('cmake', ('.cmake', ), CMakeCodeModel)

        self.app.editor_created.connect(self.editor_created)

    def editor_path_changed(self, editor):
        assert isinstance(editor, AbstractEditor)
        import pathlib
        if editor.path.name == 'CMakeLists.txt':
            editor.buffer_controller.code_model = CMakeCodeModel(editor.buffer_controller.buffer,
                                                                 editor.config)



    def editor_created(self, editor):
        assert isinstance(editor, AbstractEditor)
        editor.path_changed.connect(self.editor_path_changed, add_sender=True)

    def detach(self):
        self.app.editor_created.disconnect(self.editor_created)


