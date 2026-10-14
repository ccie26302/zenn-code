import os, sys
if __name__ == "__main__":
    os.makedirs(os.path.join(sys.argv[1], "app")); open(os.path.join(sys.argv[1], "app/settings.conf"), "w").write("DB_HOST=localhost\nDB_PASSWORD=dummy-7f3a\n")
