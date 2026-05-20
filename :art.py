from pyfiglet import Figlet

def generate_ascii_art(text, color="white"):
    fig = Figlet(font="slant")
    art = fig.renderText(text)
    print(f"\033[1;{color}m{art}\033[0m")

if __name__ == "__main__":
    text = input("Enter text for ASCII art: ")
    color = input("Enter color (e.g., red, green, blue): ")
    generate_ascii_art(text, color)