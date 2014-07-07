
import unittest
import warnings

from stem.core.nconfig import (Config, 
                               Settings,
                               Field,
                               EnumField,
                               SetField,
                               SafetyContext,
                               Conversions)


class Settings1(Settings):
    _ns_ = 'stem.test.Settings1'
    
    unsafe_str_field = Field(str, None)
    maybe_safe_int_field   = Field(int, 2, safe=True)
    
    unsafe_enum = EnumField(int, dict(foo=1, bar=2), safe=False)
    partially_safe_enum = EnumField(int, dict(foo=1, bar=2), safe=True, allow_others=SafetyContext.safe)
    very_safe_enum = EnumField(int, dict(foo=1, bar=2), safe=True, allow_others=SafetyContext.either)
    
    test_set = Field(frozenset, frozenset(), safe=True)
#     test_set = Field(int, None, safe=True)
    
class Settings2(Settings):
    _ns_ = 'stem.test.Settings2'
    
    maybe_safe_int_field = Field(str, 'foo')
    
    
class TestConfig(unittest.TestCase):
    
    def setUp(self):
        self.config = Config()
    
    def test_sets(self):
        
        s1 = Settings1.from_config(self.config)
        
        assert not s1.test_set

        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                test_set.add: [1,2]
            '''
        )
        
        assert s1.test_set == {1,2}
        
        
        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                test_set.remove: [1]
            '''
        )
        
        assert s1.test_set == {2}
        s1.test_set |= {3}
        assert s1.test_set == {2,3}
        
        # make sure these don't cause exceptions
        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                test_set.foo: bar
            '''
        )
        
        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                test_set.remove: 1
            '''
        )     
        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                test_set.add: 1
            '''
        )     


        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                test_set.remove: [1]
            '''
        )     
        
#     def test_sets(self):
# 
# #         print(Conversions._entries)
#         self.config.load_yaml_safely(
#             '''
#             - !stem.test.Settings1
#                 test_set: [1,2,3]
#             '''
#         )
#         s1 = Settings1.from_config(self.config)        
# #         Settings1.test_set.set_safely(s1, frozenset([1,2,3]))
#         assert s1.test_set == frozenset([1,2,3])
#     
    def test_enum_maps_values(self):
        s1 = Settings1.from_config(self.config)
        s1.unsafe_enum = 'foo'
        assert s1.unsafe_enum == 1
        
        s1.unsafe_enum = 2
        assert s1.unsafe_enum == 2
        
        try:
            s1.unsafe_enum = 3
        except ValueError:
            pass
        else:
            assert False, 'expected ValueError'
            
    def test_enum_wont_load_unsafe_values(self):
        s1 = Settings1.from_config(self.config)
        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                unsafe_enum: 2
                partially_safe_enum: 2
            '''
        )

        assert s1.unsafe_enum is None
        assert s1.partially_safe_enum == 2 
        try:
            self.config.load_yaml_safely(
                '''
                stem.test.Settings1:
                    partially_safe_enum: 4
                '''
            )
        except ValueError:
            pass
        else:
            assert False, 'expected ValueError'
            
        assert s1.partially_safe_enum == 2
        s1.partially_safe_enum = 4
        assert s1.partially_safe_enum == 4
        
        self.config.load_yaml_safely(
            '''
            stem.test.Settings1:
                very_safe_enum: 4
            '''
        )
        
        assert s1.very_safe_enum == 4
        
    def test_settings_should_have_initial_values(self):
        s1 = Settings1.from_config(self.config)
        s2 = Settings2.from_config(self.config)
        
        assert s1.unsafe_str_field is None
        assert s1.maybe_safe_int_field == 2
        assert s2.maybe_safe_int_field == 'foo'
        
    def test_settings_should_be_scoped(self):
        
        s1a = Settings1.from_config(self.config)
        s2a = Settings2.from_config(self.config)
        
        config_b = self.config.derive()
        
        s1b = Settings1.from_config(config_b)
        s2b = Settings2.from_config(config_b)
        
        s2a.maybe_safe_int_field = 'bar'
        
        assert s2a.maybe_safe_int_field == 'bar'
        assert s2b.maybe_safe_int_field == 'bar'
        
        s1b.maybe_safe_int_field = 1
        assert s1a.maybe_safe_int_field == 2
        assert s1b.maybe_safe_int_field == 1
        
    def test_unsafe_values_discarded(self):

        dc = self.config.derive()
        dc.load_yaml_safely(
            '''
            stem.test.Settings1:
                unsafe_str_field: 'a'
                maybe_safe_int_field: 4
            stem.test.Settings2:
                maybe_safe_int_field: 'bar'
            '''
        )
            
        s1 = Settings1.from_config(dc)
        s2 = Settings2.from_config(dc)
        
        assert s1.unsafe_str_field is None
        assert s1.maybe_safe_int_field == 4
        assert s2.maybe_safe_int_field == 'foo'
        
    def test_typing_works(self):
        dc = self.config.derive()
        try:
            dc.load_yaml_safely(
                '''
                stem.test.Settings1:
                    maybe_safe_int_field: 'a'
                '''
            )
        except TypeError:
            pass
        else:
            assert False, 'expected exception'