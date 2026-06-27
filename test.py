import shutil

with open ("result.txt", encoding='utf-8') as f:
    print(f.read())

shutil.move("F:/multidrive/result.txt", "F:/multidrive/test")