package handler

import (
	"fmt"
	"io"
	"net/http"
	"time"
)

func Handler(w http.ResponseWriter, r *http.Request) {
	location, _ := time.LoadLocation("Asia/Shanghai")
	today := time.Now().In(location)

	imageURL := fmt.Sprintf(
		"https://img.owspace.com/Public/uploads/Download/%d/%02d%02d.jpg",
		today.Year(),
		today.Month(),
		today.Day(),
	)

	resp, err := http.Get(imageURL)
	if err != nil {
		http.Error(w, "Failed to fetch image", http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "image/jpg")
	io.Copy(w, resp.Body)
}

func main() {
	http.HandleFunc("/", Handler)
	http.ListenAndServe(":8080", nil)
}
