

from stem.core.nconfig import Settings, Field

class PythonCompletionSettings(Settings):
    _ns_ = 'python'

    case_insensitive_completion = Field(bool, True)
    add_dot_after_module = Field(bool, False)
    add_bracket_after_function = Field(bool, True)
    no_completion_duplicates = Field(bool, True)


    def apply_settings(self):
        from jedi import settings as s

        s.case_insensitive_completion = self.case_insensitive_completion
        s.add_dot_after_module = self.add_dot_after_module
        s.add_bracket_after_function = self.add_bracket_after_function
        s.no_completion_duplicates = self.no_completion_duplicates
        
