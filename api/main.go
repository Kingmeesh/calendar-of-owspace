package handler

import (
	"fmt"
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

	http.Redirect(w, r, imageURL, http.StatusMovedPermanently)
}

func main() {
	http.HandleFunc("/", Handler)
	http.ListenAndServe(":8080", nil)
}
