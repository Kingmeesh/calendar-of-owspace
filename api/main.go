package main

import (
	"fmt"
	"github.com/gin-gonic/gin"
	"net/http"
	"time"
)

func main() {
	r := gin.Default()

	r.GET("/", func(c *gin.Context) {
		location, err := time.LoadLocation("Asia/Shanghai")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load time zone"})
			return
		}

		today := time.Now().In(location)
		year := today.Year()
		month := today.Month()
		day := today.Day()

		imageURL := fmt.Sprintf("https://img.owspace.com/Public/uploads/Download/%d/%02d%02d.jpg", year, month, day)

		c.JSON(http.StatusOK, gin.H{
			"image_url": imageURL,
		})
	})

	r.Run(":8080")
}
