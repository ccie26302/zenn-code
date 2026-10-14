import os, sys
if __name__ == "__main__":
    os.makedirs(os.path.join(sys.argv[1], "notes")); open(os.path.join(sys.argv[1], "notes/README.md"), "w").write("メモ置き場\n")
