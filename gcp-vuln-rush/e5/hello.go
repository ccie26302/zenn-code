package main

import (
	"fmt"
	"net/http"
)

// 外の HTTPS に1回つないで状態を出すだけのプログラム(証明書の検証は Go の標準ライブラリ)
func main() {
	r, err := http.Get("https://www.google.com/")
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println("status:", r.Status)
}
