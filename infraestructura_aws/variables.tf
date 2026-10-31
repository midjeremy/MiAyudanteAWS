variable "aws_region" {
  default = "us-east-1"
}

variable "key_name" {
  description = "Par de claves SSH de la instancia EC2 (vockey en AWS Learner Lab)"
  type        = string
  default     = "vockey"
}

variable "db_password" {
  description = "Contraseña para RDS PostgreSQL"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 8
    error_message = "db_password debe tener al menos 8 caracteres."
  }
}
