import re

# Function to extract strings from a binary file
def extract_strings(file_path, min_length=4):
    with open(file_path, 'rb') as f:
        data = f.read()
    # Use regex to find sequences of printable characters
    strings = re.findall(b"[\x20-\x7E]{" + str(min_length).encode() + b",}", data)
    return [s.decode('utf-8', errors='ignore') for s in strings]

# Path to the executable
exe_path = "dist/PBW3 Tool v1.02.exe"

# Extract strings
strings = extract_strings(exe_path)

# Save to a text file
with open("dist/PBW3_Tool_v1.02_strings.txt", "w") as f:
    for s in strings:
        f.write(s + "\n")

print("String extraction complete.") 