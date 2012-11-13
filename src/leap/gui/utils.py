"""
utility functions to work with gui objects
"""


def layout_widgets(layout):
    """
    return a generator with all widgets in a layout
    """
    return (layout.itemAt(i) for i in range(layout.count()))
