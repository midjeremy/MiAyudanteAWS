<?php
// Segundo paso del login cuando la cuenta tiene el doble factor activo. login.php deja aquí el
// token temporal de Django (vale 5 minutos); con el código de la app se canjea por el JWT.
session_start();
require_once 'api.php';

if (isset($_SESSION['usuario'])) {
    header("Location: index.php");
    exit();
}
if (empty($_SESSION['token_2fa'])) {
    header("Location: login.php");
    exit();
}
if (empty($_SESSION['csrf_2fa'])) {
    $_SESSION['csrf_2fa'] = bin2hex(random_bytes(16));
}

$error = "";
$reiniciar = false;

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $codigo = trim($_POST["codigo"] ?? "");

    if (!hash_equals($_SESSION['csrf_2fa'], (string) ($_POST['csrf'] ?? ''))) {
        $error = "La página expiró. Vuelve a intentarlo.";
    } elseif ($codigo === "") {
        $error = "Ingresa el código de tu app autenticadora.";
    } else {
        $resultado = api_post('/api/v1/auth/2fa/verificar/', [
            'token_temporal' => $_SESSION['token_2fa'],
            'codigo' => $codigo,
        ]);

        if ($resultado['codigo'] === 200) {
            // Igual que en login.php: nuevo identificador de sesión y tokens en la sesión
            session_regenerate_id(true);
            unset($_SESSION['token_2fa'], $_SESSION['csrf_2fa']);
            $_SESSION['usuario'] = $resultado['datos']['usuario'];
            $_SESSION['token_acceso'] = $resultado['datos']['access'];
            $_SESSION['token_refresco'] = $resultado['datos']['refresh'];

            // [LEY 21.719] Igual que en login.php
            if (($resultado['datos']['consentimiento_vigente'] ?? true) === false) {
                $_SESSION['consentimiento_pendiente'] = true;
                header("Location: aceptar_politica.php");
                exit();
            }

            header("Location: index.php");
            exit();
        } elseif ($resultado['codigo'] === 401 && !empty($resultado['datos']['reiniciar'])) {
            // El token temporal venció o no es válido: hay que volver a dar la contraseña
            unset($_SESSION['token_2fa']);
            $reiniciar = true;
            $error = $resultado['datos']['error'] ?? "La verificación venció. Inicia sesión de nuevo.";
        } elseif ($resultado['codigo'] === 401) {
            $error = "El código no es correcto. Revisa que la hora de tu teléfono esté bien.";
        } elseif ($resultado['codigo'] === 429) {
            $error = "Demasiados intentos. Espera un minuto e inténtalo de nuevo.";
        } else {
            $error = "No pudimos conectar con el servidor. Inténtalo más tarde.";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificación en dos pasos - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/login.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body class="login-body">

    <div class="login-wrapper">
        <div class="login-left">
            <div class="login-brand">
                <div class="logo-icon">🎓</div>
                <div class="logo-info">
                    <h2>Mi Ayudante</h2>
                    <span>Tu futuro, nuestra guía</span>
                </div>
            </div>

            <div class="login-hero-text">
                <h1>Tu cuenta <span>más segura</span></h1>
                <p>Tienes activada la verificación en dos pasos: además de tu contraseña, te pedimos un código de tu app autenticadora.</p>
            </div>

            <div class="login-image-container">
                <img src="/static/img/login-ilustracion.png" alt="Estudiantes orientándose">
            </div>
        </div>

        <div class="login-right">
            <div class="login-form-container">
                <h2>Verificación en dos pasos</h2>
                <p class="login-subtitle">Ingresa el código de 6 dígitos que muestra tu app autenticadora.</p>

                <?php if (!empty($error)): ?>
                    <div class="alert-error" style="color: #dc2626; background: #ffeeef; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px;">
                        <?= htmlspecialchars($error) ?>
                    </div>
                <?php endif; ?>

                <?php if ($reiniciar): ?>
                    <a href="login.php" class="btn-submit" style="display: block; text-align: center; text-decoration: none;">Volver a iniciar sesión</a>
                <?php else: ?>
                    <form action="verificar_2fa.php" method="POST" autocomplete="off">
                        <input type="hidden" name="csrf" value="<?= htmlspecialchars($_SESSION['csrf_2fa']) ?>">
                        <div class="form-group">
                            <label for="codigo">Código de verificación</label>
                            <div class="input-with-icon">
                                <span class="input-icon">🔐</span>
                                <input type="text" id="codigo" name="codigo" placeholder="123456"
                                       inputmode="text" autocomplete="one-time-code" maxlength="20" autofocus required>
                            </div>
                        </div>

                        <button type="submit" class="btn-submit">Verificar</button>
                    </form>

                    <p class="register-redirect">
                        ¿No tienes tu teléfono? Escribe uno de tus <strong>códigos de recuperación</strong> (cada uno sirve una sola vez).
                    </p>
                    <p class="register-redirect">
                        <a href="logout.php">Cancelar e iniciar sesión con otra cuenta</a>
                    </p>
                <?php endif; ?>
            </div>
        </div>
    </div>

</body>
</html>
