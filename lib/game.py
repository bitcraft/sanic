__author__ = 'leif'

import lib.window
import lib.editor

def new_game(*args, **kwargs):
    w = lib.window.GameWindow(*args, **kwargs)
    context = lib.editor.Editor(w)
    w.context_stack.append(context)
    return w
