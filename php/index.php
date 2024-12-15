<?php
date_default_timezone_set("Asia/Shanghai");
$year = date("Y");
$month = date("m");
$day = date("d");

$image_url = "https://img.owspace.com/Public/uploads/Download/$year/{$month}{$day}.jpg";

header("Location: $image_url");
exit();
?>
