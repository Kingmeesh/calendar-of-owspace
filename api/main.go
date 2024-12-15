package handler

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
	"io/ioutil"
	"strings"
)

const cacheDir = "./cache/"

func getCacheFilePath(date string) string {
	return fmt.Sprintf("%s/%s.jpg", cacheDir, date)
}

func downloadImage(imageURL string, cachePath string) error {
	resp, err := http.Get(imageURL)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	out, err := os.Create(cachePath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

func Handler(w http.ResponseWriter, r *http.Request) {
	location, _ := time.LoadLocation("Asia/Shanghai")
	today := time.Now().In(location)
	dateStr := fmt.Sprintf("%d%02d%02d", today.Year(), today.Month(), today.Day())

	cachePath := getCacheFilePath(dateStr)

	if _, err := os.Stat(cachePath); err == nil {
		file, err := os.Open(cachePath)
		if err != nil {
			http.Error(w, "Failed to open cached image", http.StatusInternalServerError)
			return
		}
		defer file.Close()
		w.Header().Set("Content-Type", "image/jpeg")
		io.Copy(w, file)
		return
	}

	imageURL := fmt.Sprintf(
		"https://img.owspace.com/Public/uploads/Download/%d/%02d%02d.jpg",
		today.Year(),
		today.Month(),
		today.Day(),
	)

	err := downloadImage(imageURL, cachePath)
	if err != nil {
		http.Error(w, "Failed to fetch image", http.StatusInternalServerError)
		return
	}

	file, err := os.Open(cachePath)
	if err != nil {
		http.Error(w, "Failed to open downloaded image", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	w.Header().Set("Content-Type", "image/jpeg")
	io.Copy(w, file)
}

func main() {
	if _, err := os.Stat(cacheDir); os.IsNotExist(err) {
		err := os.Mkdir(cacheDir, 0755)
		if err != nil {
			fmt.Println("Failed to create cache directory:", err)
			return
		}
	}

	http.HandleFunc("/", Handler)
	http.ListenAndServe(":8080", nil)
}
