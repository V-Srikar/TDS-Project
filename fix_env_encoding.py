import os

def fix_encoding():
    filename = ".env"
    if not os.path.exists(filename):
        print(".env not found")
        return

    content = ""
    # Try reading as UTF-16 (PowerShell default)
    try:
        with open(filename, "r", encoding="utf-16") as f:
            content = f.read()
        print("Read as UTF-16")
    except:
        # Try UTF-8
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            print("Read as UTF-8")
        except:
            print("Could not read file")
            return

    # Write back as UTF-8 without BOM
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print("Converted to UTF-8")

if __name__ == "__main__":
    fix_encoding()
