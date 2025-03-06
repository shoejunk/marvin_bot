import keyboard

def handle_dictate(dictated_text: str):
    """Simulate keyboard input to type the dictated text at the current cursor position."""
    if dictated_text.startswith(':'):
        dictated_text = dictated_text[1:].lstrip()
    keyboard.write(dictated_text)
