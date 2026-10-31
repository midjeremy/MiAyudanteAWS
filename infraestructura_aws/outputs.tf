output "servidor_ip_publica" {
  value = aws_eip.web_eip.public_ip
}
output "base_de_datos_endpoint" {
  value = aws_db_instance.postgres_db.endpoint
}
output "bucket_mallas" {
  value = data.aws_s3_bucket.mallas_bucket.bucket
}