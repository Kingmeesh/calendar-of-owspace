package main

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

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(fmt.Sprintf(`{"image_url": "%s"}`, imageURL)))
}

func main() {}
