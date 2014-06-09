'''
Workaround for Sphinx Issue #1453
https://bitbucket.org/birkenfeld/sphinx/issue/1453/index-out-of-range-during-make
'''

from sphinx.ext.viewcode import *
from sphinx.ext.viewcode import _

def collect_pages(app):
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    highlighter = app.builder.highlighter
    urito = app.builder.get_relative_uri

    modnames = set(env._viewcode_modules)

    app.builder.info(' (%d module code pages)' %
                     len(env._viewcode_modules), nonl=1)

    for modname, entry in env._viewcode_modules.items():
        if not entry:
            continue
        code, tags, used = entry
        # construct a page name for the highlighted source
        pagename = '_modules/' + modname.replace('.', '/')
        # highlight the source using the builder's highlighter
        highlighted = highlighter.highlight_block(code, 'python', linenos=False)
        # split the code into lines
        lines = highlighted.splitlines()
        # split off wrap markup from the first line of the actual code
        before, after = lines[0].split('<pre>')
        lines[0:1] = [before + '<pre>', after]
        # nothing to do for the last line; it always starts with </pre> anyway
        # now that we have code lines (starting at index 1), insert anchors for
        # the collected tags (HACK: this only works if the tag boundaries are
        # properly nested!)
        maxindex = len(lines) - 1
        for name, docname in used.items():
            type, start, end = tags[name]

            # HACK: BEGIN CHANGED CODE
            if start >= len(lines):
                continue
            # HACK: END CHANGED CODE
            
            backlink = urito(pagename, docname) + '#' + modname + '.' + name
            lines[start] = (
                '<div class="viewcode-block" id="%s"><a class="viewcode-back" '
                'href="%s">%s</a>' % (name, backlink, _('[docs]'))
                + lines[start])
            lines[min(end - 1, maxindex)] += '</div>'
        # try to find parents (for submodules)
        parents = []
        parent = modname
        while '.' in parent:
            parent = parent.rsplit('.', 1)[0]
            if parent in modnames:
                parents.append({
                    'link': urito(pagename, '_modules/' +
                                  parent.replace('.', '/')),
                    'title': parent})
        parents.append({'link': urito(pagename, '_modules/index'),
                        'title': _('Module code')})
        parents.reverse()
        # putting it all together
        context = {
            'parents': parents,
            'title': modname,
            'body': _('<h1>Source code for %s</h1>') % modname + \
                    '\n'.join(lines)
        }
        yield (pagename, context, 'page.html')

    if not modnames:
        return

    app.builder.info(' _modules/index')
    html = ['\n']
    # the stack logic is needed for using nested lists for submodules
    stack = ['']
    for modname in sorted(modnames):
        if modname.startswith(stack[-1]):
            stack.append(modname + '.')
            html.append('<ul>')
        else:
            stack.pop()
            while not modname.startswith(stack[-1]):
                stack.pop()
                html.append('</ul>')
            stack.append(modname + '.')
        html.append('<li><a href="%s">%s</a></li>\n' % (
            urito('_modules/index', '_modules/' + modname.replace('.', '/')),
            modname))
    html.append('</ul>' * (len(stack) - 1))
    context = {
        'title': _('Overview: module code'),
        'body': _('<h1>All modules for which code is available</h1>') + \
            ''.join(html),
    }

    yield ('_modules/index', context, 'page.html')

import sphinx.ext.viewcode
sphinx.ext.viewcode.collect_pages = collect_pages
