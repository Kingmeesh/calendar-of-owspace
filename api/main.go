package handler

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)

const (
	bucketName = "your-vercel-blob-bucket-name"
	region     = "us-east-1"
)

func createS3Session() *session.Session {
	return session.Must(session.NewSession(&aws.Config{
		Region:      aws.String(region),
		Credentials: credentials.NewStaticCredentials(
			"your-vercel-access-key", 
			"your-vercel-secret-key", 
			""),
	}))
}

func downloadImage(imageURL string) ([]byte, error) {
	resp, err := http.Get(imageURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	return io.ReadAll(resp.Body)
}

func uploadToS3(sess *session.Session, key string, data []byte) error {
	svc := s3.New(sess)

	_, err := svc.PutObject(&s3.PutObjectInput{
		Bucket:      aws.String(bucketName),
		Key:         aws.String(key),
		Body:        bytes.NewReader(data),
		ContentType: aws.String("image/jpeg"),
	})

	return err
}

func getFromS3(sess *session.Session, key string) ([]byte, error) {
	svc := s3.New(sess)

	result, err := svc.GetObject(&s3.GetObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, err
	}
	defer result.Body.Close()

	return io.ReadAll(result.Body)
}

func Handler(w http.ResponseWriter, r *http.Request) {
	location, _ := time.LoadLocation("Asia/Shanghai")
	today := time.Now().In(location)

	key := fmt.Sprintf("%d%02d%02d.jpg", today.Year(), today.Month(), today.Day())
	sess := createS3Session()

	imageData, err := getFromS3(sess, key)
	if err == nil {
		w.Header().Set("Content-Type", "image/jpeg")
		w.Write(imageData)
		return
	}

	imageURL := fmt.Sprintf(
		"https://img.owspace.com/Public/uploads/Download/%d/%02d%02d.jpg",
		today.Year(), today.Month(), today.Day(),
	)

	imageData, err = downloadImage(imageURL)
	if err != nil {
		http.Error(w, "Failed to download image", http.StatusInternalServerError)
		return
	}

	err = uploadToS3(sess, key, imageData)
	if err != nil {
		fmt.Println("Failed to upload to S3:", err)
	}

	w.Header().Set("Content-Type", "image/jpeg")
	w.Write(imageData)
}
