package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"image"
	"image/jpeg"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"golang.org/x/image/draw"
)

const (
	fallbackURL     = "https://img.owspace.com/Public/uploads/Download/2024/1210.jpg"
	targetWidth     = 619
	targetHeight    = 899
	blobAPIBase     = "https://blob.vercel-storage.com"
	downloadTimeout = 9 * time.Second
)

// ---------- Vercel Blob 客户端 ----------

func blobToken() string {
	return os.Getenv("BLOB_READ_WRITE_TOKEN")
}

func blobAvailable() bool {
	return blobToken() != ""
}

func blobKey(t time.Time) string {
	return fmt.Sprintf("%d%02d%02d.jpg", t.Year(), t.Month(), t.Day())
}

func blobPut(data []byte, pathname string) error {
	url := fmt.Sprintf("%s/%s", blobAPIBase, pathname)
	req, err := http.NewRequest("PUT", url, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+blobToken())
	req.Header.Set("Content-Type", "image/jpeg")
	req.Header.Set("x-vercel-blob-access", "private")
	req.Header.Set("x-vercel-blob-add-random-suffix", "false")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("blob put status %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

func blobGet(pathname string) ([]byte, error) {
	url := fmt.Sprintf("%s/%s", blobAPIBase, pathname)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+blobToken())

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("blob get status %d: %s", resp.StatusCode, string(body))
	}
	return body, nil
}

// ---------- 图片缩放 ----------

func resizeImage(data []byte) ([]byte, error) {
	src, err := jpeg.Decode(bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("decode image: %w", err)
	}
	dst := image.NewRGBA(image.Rect(0, 0, targetWidth, targetHeight))
	draw.CatmullRom.Scale(dst, dst.Bounds(), src, src.Bounds(), draw.Over, nil)

	output := new(bytes.Buffer)
	if err := jpeg.Encode(output, dst, &jpeg.Options{Quality: 95}); err != nil {
		return nil, fmt.Errorf("encode image: %w", err)
	}
	return output.Bytes(), nil
}

// ---------- 下载图片 ----------

func downloadImage(imageURL string) ([]byte, error) {
	client := &http.Client{Timeout: downloadTimeout}
	resp, err := client.Get(imageURL)
	if err != nil {
		return nil, fmt.Errorf("http get %s: %w", imageURL, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status %d for %s", resp.StatusCode, imageURL)
	}
	return io.ReadAll(resp.Body)
}

// ---------- 获取今日图片（含备用回退） ----------

func fetchTodayImage(today time.Time) ([]byte, string, error) {
	primaryURL := fmt.Sprintf(
		"https://img.owspace.com/Public/uploads/Download/%d/%02d%02d.jpg",
		today.Year(), today.Month(), today.Day(),
	)
	log.Printf("Attempting to fetch image from: %s", primaryURL)

	data, err := downloadImage(primaryURL)
	if err == nil {
		resized, err := resizeImage(data)
		if err != nil {
			return nil, primaryURL, fmt.Errorf("resize primary image: %w", err)
		}
		return resized, primaryURL, nil
	}

	log.Printf("Primary failed (%v), fallback to: %s", err, fallbackURL)
	fallbackData, fallbackErr := downloadImage(fallbackURL)
	if fallbackErr != nil {
		return nil, primaryURL, fmt.Errorf("primary: %v, fallback: %v", err, fallbackErr)
	}

	resized, err := resizeImage(fallbackData)
	if err != nil {
		return nil, fallbackURL, fmt.Errorf("resize fallback image: %w", err)
	}
	return resized, fallbackURL, nil
}

// ---------- JSON 错误响应 ----------

func jsonError(w http.ResponseWriter, msg string, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"error": msg})
}

// ---------- Vercel Handler ----------

func Handler(w http.ResponseWriter, r *http.Request) {
	location, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		jsonError(w, "Internal server error: load location", http.StatusInternalServerError)
		return
	}
	today := time.Now().In(location)
	key := blobKey(today)

	// 1) 尝试从 Vercel Blob 读取缓存
	if blobAvailable() {
		if cached, err := blobGet(key); err == nil {
			log.Printf("Serving cached image from Vercel Blob: %s", key)
			w.Header().Set("Content-Type", "image/jpeg")
			w.Write(cached)
			return
		}
	}

	// 2) 从 owspace 获取（含备用回退）
	imageData, _, err := fetchTodayImage(today)
	if err != nil {
		log.Printf("Error fetching image: %v", err)
		jsonError(w, fmt.Sprintf("Failed to fetch image: %v", err), http.StatusInternalServerError)
		return
	}

	// 3) 异步写入 Blob 缓存
	if blobAvailable() {
		go func() {
			if err := blobPut(imageData, key); err != nil {
				log.Printf("Failed to upload to Blob: %v", err)
			} else {
				log.Printf("Uploaded to Blob: %s", key)
			}
		}()
	}

	w.Header().Set("Content-Type", "image/jpeg")
	w.Write(imageData)
}
