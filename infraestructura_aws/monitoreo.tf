# Monitoreo y alertas (SLA 01, SLA 02 y KPI-05 del informe).
# Las alarmas avisan por correo al Líder Cloud mediante SNS.

resource "aws_sns_topic" "alertas" {
  name = "miayudante-alertas"
}

# AWS envía un correo de confirmación: la suscripción queda activa al aceptarlo
resource "aws_sns_topic_subscription" "alertas_correo" {
  count     = var.correo_alertas == "" ? 0 : 1
  topic_arn = aws_sns_topic.alertas.arn
  protocol  = "email"
  endpoint  = var.correo_alertas
}

locals {
  acciones_alerta = [aws_sns_topic.alertas.arn]
}

# /health/deep falla (la publica cada minuto infraestructura_aws/servidor/monitor_salud.py).
# Sin datos (lab apagado) no se considera caída.
resource "aws_cloudwatch_metric_alarm" "salud_profunda" {
  alarm_name          = "miayudante-health-deep"
  alarm_description   = "La comparación de ofertas de /health/deep falló 3 minutos seguidos"
  namespace           = "MiAyudante"
  metric_name         = "HealthDeep"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.acciones_alerta
  ok_actions          = local.acciones_alerta
}

resource "aws_cloudwatch_metric_alarm" "ec2_estado" {
  alarm_name          = "miayudante-ec2-estado"
  alarm_description   = "La instancia EC2 no pasa los chequeos de estado de AWS"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.web_server.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  alarm_actions       = local.acciones_alerta
}

resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "miayudante-ec2-cpu"
  alarm_description   = "CPU de la EC2 sobre 85 % durante 10 minutos"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.web_server.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 85
  alarm_actions       = local.acciones_alerta
}

resource "aws_cloudwatch_metric_alarm" "rds_almacenamiento" {
  alarm_name          = "miayudante-rds-almacenamiento"
  alarm_description   = "Quedan menos de 2 GB libres en la base de datos"
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.postgres_db.identifier }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 2147483648
  alarm_actions       = local.acciones_alerta
}

resource "aws_cloudwatch_metric_alarm" "rds_conexiones" {
  alarm_name          = "miayudante-rds-conexiones"
  alarm_description   = "Más de 60 conexiones abiertas a la base de datos (db.t3.micro admite cerca de 80)"
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.postgres_db.identifier }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 60
  alarm_actions       = local.acciones_alerta
}
