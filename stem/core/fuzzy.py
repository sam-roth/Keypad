
import re



def fuzzy_regex(pattern):
    if pattern:
        return re.compile('.*?' + '.*?'.join(map(re.escape, pattern)))
    else:
        return re.compile('')


class Filter(object):
    def __init__(self, coll, pred):
        fcoll = [(index, item) for (index, item) 
                                in enumerate(coll)
                                if pred(item)]        
        self._rebuild(fcoll)
        
    def _rebuild(self, fcoll):
        self.indices = [x[0] for x in fcoll]
        self.rows = [x[1] for x in fcoll]
        
    def enumerate(self):
        return zip(self.indices, self.rows)
        
    def sort(self, key):
        pairs = sorted(self.enumerate(), key=lambda item: key(item[1]))
        self._rebuild(pairs)
        

    
class FuzzyMatcher(object):
    def __init__(self, pattern, case_sensitive=False):
        if not case_sensitive:
            pattern = pattern.lower()
        self.__case_sensitive = case_sensitive
        self.__regex = fuzzy_regex(pattern)
        
    def match(self, string):
        if not self.__case_sensitive:
            string = string.lower()
        return self.__regex.match(string) is not None
  
    def filter(self, items, key=None):
        
        if key is None:
            pred = self.match
        else:
            def pred(x):
                return self.match(key(x))
        
        return Filter(items, pred)
        
    
#     def filter(self, items, key=None):
#         indices = []
#         filtered = []
#         for index, item in enumerate(items):
#             if key is None:
#                 k  = item
#             else:
#                 k = key(item)
#             
#             if self.match(k):
#                 indices.append(index)
#                 filtered.append(item)
#         return indices, filtered
# 
# 