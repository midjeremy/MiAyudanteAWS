resource "aws_security_group" "sg_web" {
  name        = "miayudante-web-sg"
  description = "Trafico web y SSH"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "sg_db" {
  name        = "miayudante-db-sg"
  description = "PostgreSQL interno"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_web.id]
  }
}

resource "aws_instance" "web_server" {
  ami                    = "ami-0d97d7f07b25dd693"
  instance_type          = "t3.large"
  iam_instance_profile   = "LabInstanceProfile"
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.sg_web.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              apt-get update && apt-get upgrade -y
              apt-get install -y software-properties-common python3-pip python3-venv postgresql-client nginx curl git

              # PHP Seguro y dependencias BFF (repositorio Sury, requerido en Ubuntu 26.04)
              apt-get install -y lsb-release ca-certificates
              curl -sSLo /tmp/debsuryorg-archive-keyring.deb https://packages.sury.org/debsuryorg-archive-keyring.deb
              dpkg -i /tmp/debsuryorg-archive-keyring.deb
              echo "deb [signed-by=/usr/share/keyrings/debsuryorg-archive-keyring.gpg] https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list
              apt-get update -y
              apt-get install -y php8.5 php8.5-fpm php8.5-cli php8.5-pgsql php8.5-curl

              # Chrome para web scraping
              wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
              apt-get install -y ./google-chrome-stable_current_amd64.deb

              # Entorno Python global
              pip3 install django djangorestframework psycopg2-binary gunicorn pandas selenium

              # PHP2Shell: no levantar PHP sin el parche (minimo 8.5.12)
              if ! php8.5 -r 'exit(version_compare(PHP_VERSION, "8.5.12", ">=") ? 0 : 1);'; then
                echo "ERROR: PHP anterior a 8.5.12, se detiene php8.5-fpm"
                systemctl stop php8.5-fpm
                exit 1
              fi

              systemctl restart php8.5-fpm && systemctl restart nginx
              EOF

  tags = { Name = "miayudante-backend" }
}

resource "aws_eip" "web_eip" {
  instance = aws_instance.web_server.id
  domain   = "vpc"
}

resource "aws_db_instance" "postgres_db" {
  identifier             = "miayudante-db"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = "db.t3.micro"
  db_name                = "miayudantedb"
  username               = "postgres"
  password               = var.db_password
  skip_final_snapshot    = true
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.sg_db.id]
}

data "aws_caller_identity" "current" {}

# Learner Lab bloquea s3:GetBucketObjectLockConfiguration, que aws_s3_bucket necesita como resource.
# El bucket se crea una vez a mano y Terraform solo lo consulta.
data "aws_s3_bucket" "mallas_bucket" {
  bucket = "miayudante-static-${data.aws_caller_identity.current.account_id}"
}
