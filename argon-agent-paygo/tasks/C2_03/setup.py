import os, sys
if __name__ == "__main__":
    open(os.path.join(sys.argv[1], "report.txt"), "w").write("月次レポート: 売上 1,234 万円\n")
