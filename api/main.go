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

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"golang.org/x/image/draw"
)

const (
	fallbackURL   = "https://img.owspace.com/Public/uploads/Download/2024/1210.jpg"
	targetWidth   = 619
	targetHeight  = 899
	defaultRegion = "us-east-1"
)

// ---------- 图片缩放 (匹配 Python 的 LANCZOS 品质) ----------

func resizeImage(data []byte) ([]byte, error) {
	src, err := jpeg.Decode(bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("decode image: %w", err)
	}

	// 使用 CatmullRom 插值，品质接近 Python 的 LANCZOS
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
	client := &http.Client{Timeout: 10 * time.Second}
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

// ---------- 获取今日图片（含备用回退，匹配 Python 逻辑） ----------

func fetchTodayImage(today time.Time) ([]byte, string, error) {
	// 主地址
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

	// 备用回退 (匹配 Python: 2024/1210.jpg)
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

// ---------- S3 / Vercel Blob 缓存（可选，通过环境变量启用） ----------

func s3ConfigAvailable() bool {
	return os.Getenv("VERCEL_BLOB_BUCKET") != "" &&
		os.Getenv("VERCEL_BLOB_ACCESS_KEY") != "" &&
		os.Getenv("VERCEL_BLOB_SECRET_KEY") != ""
}

func createS3Session() *session.Session {
	region := os.Getenv("VERCEL_BLOB_REGION")
	if region == "" {
		region = defaultRegion
	}
	return session.Must(session.NewSession(&aws.Config{
		Region:      aws.String(region),
		Credentials: credentials.NewStaticCredentials(
			os.Getenv("VERCEL_BLOB_ACCESS_KEY"),
			os.Getenv("VERCEL_BLOB_SECRET_KEY"),
			""),
	}))
}

func uploadToS3(sess *session.Session, key string, data []byte) error {
	svc := s3.New(sess)
	_, err := svc.PutObject(&s3.PutObjectInput{
		Bucket:      aws.String(os.Getenv("VERCEL_BLOB_BUCKET")),
		Key:         aws.String(key),
		Body:        bytes.NewReader(data),
		ContentType: aws.String("image/jpeg"),
	})
	return err
}

func getFromS3(sess *session.Session, key string) ([]byte, error) {
	svc := s3.New(sess)
	result, err := svc.GetObject(&s3.GetObjectInput{
		Bucket: aws.String(os.Getenv("VERCEL_BLOB_BUCKET")),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, err
	}
	defer result.Body.Close()
	return io.ReadAll(result.Body)
}

// ---------- JSON 错误响应 (匹配 Python 的 jsonify) ----------

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
	key := fmt.Sprintf("%d%02d%02d.jpg", today.Year(), today.Month(), today.Day())

	// 1) 尝试从 S3 缓存读取（如果配置了）
	if s3ConfigAvailable() {
		sess := createS3Session()
		if cached, err := getFromS3(sess, key); err == nil {
			log.Println("Serving cached image from S3")
			w.Header().Set("Content-Type", "image/jpeg")
			w.Write(cached)
			return
		}
	}

	// 2) 从 owspace 获取（含备用回退）
	imageData, usedURL, err := fetchTodayImage(today)
	if err != nil {
		log.Printf("Error fetching image: %v", err)
		jsonError(w, fmt.Sprintf("Failed to fetch image: %v", err), http.StatusInternalServerError)
		return
	}

	// 3) 异步写入 S3 缓存
	if s3ConfigAvailable() {
		sess := createS3Session()
		go func() {
			if err := uploadToS3(sess, key, imageData); err != nil {
				log.Printf("Failed to upload to S3: %v", err)
			} else {
				log.Printf("Uploaded to S3: %s", usedURL)
			}
		}()
	}

	w.Header().Set("Content-Type", "image/jpeg")
	w.Write(imageData)
}
