GreenLineEdit = "QLabel {color: green; font-weight: bold}"
ErrorLabelStyleSheet = """QLabel { color: red; font-weight: bold }"""
ErrorLineEdit = """QLineEdit { border: 1px solid red; }"""


# XXX this is bad.
# and you should feel bad for it.
# The original style has a sort of box color
# white/beige left-top/right-bottom or something like
# that.

RegularLineEdit = """
QLineEdit {
    border: 1px solid black;
}
"""
