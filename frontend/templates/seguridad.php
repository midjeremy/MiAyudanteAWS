<?php
// Verificación en dos pasos (app autenticadora, TOTP): activar con QR, confirmar el primer código,
// mostrar los códigos de recuperación (una sola vez) y desactivar. Django hace todo el trabajo real.
session_start();
require_once 'api.php';

if (empty($_SESSION['usuario']) || empty($_SESSION['token_acceso'])) {
    header('Location: login.php');
    exit;
}
if (empty($_SESSION['csrf_seguridad'])) {
    $_SESSION['csrf_seguridad'] = bin2hex(random_bytes(16));
}
$token = $_SESSION['token_acceso'];

// El JWT venció (dura 1 hora): se pide iniciar sesión de nuevo
function sesion_vencida(array $r): void{
    if ($r['codigo'] === 401) {
        header('Location: logout.php');
        exit;
    }
}

function mensaje_error(array $r, string $por_defecto): string{
    if ($r['codigo'] === 429) {
        return 'Demasiados intentos. Espera un minuto e inténtalo de nuevo.';
    }
    return $r['datos']['error'] ?? $por_defecto;
}

$error = '';
$aviso = '';
$codigos_recuperacion = null;  // Solo se llenan justo después de confirmar: no se guardan en la sesión

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $accion = $_POST['accion'] ?? '';
    $codigo = trim($_POST['codigo'] ?? '');

    if (!hash_equals($_SESSION['csrf_seguridad'], (string) ($_POST['csrf'] ?? ''))) {
        $error = 'La página expiró. Vuelve a intentarlo.';
    } elseif ($accion === 'activar') {
        $r = api_post('/api/v1/auth/2fa/activar/', [], $token);
        sesion_vencida($r);
        if ($r['codigo'] === 200) {
            // Se guarda mientras se confirma, para volver a mostrar el QR si el primer código falla
            $_SESSION['2fa_pendiente'] = [
                'qr' => $r['datos']['qr_png_base64'],
                'secreto' => $r['datos']['secreto'],
            ];
        } else {
            $error = mensaje_error($r, 'No pudimos generar el código QR. Inténtalo más tarde.');
        }
    } elseif ($accion === 'confirmar') {
        $r = api_post('/api/v1/auth/2fa/confirmar/', ['codigo' => $codigo], $token);
        sesion_vencida($r);
        if ($r['codigo'] === 200) {
            unset($_SESSION['2fa_pendiente']);
            $codigos_recuperacion = $r['datos']['codigos_recuperacion'];
        } else {
            $error = mensaje_error($r, 'No pudimos activar la verificación en dos pasos.');
        }
    } elseif ($accion === 'cancelar') {
        unset($_SESSION['2fa_pendiente']);
    } elseif ($accion === 'desactivar') {
        $r = api_post('/api/v1/auth/2fa/desactivar/', ['codigo' => $codigo], $token);
        sesion_vencida($r);
        if ($r['codigo'] === 200) {
            $aviso = 'Desactivaste la verificación en dos pasos. Ahora solo se pide tu contraseña.';
        } else {
            $error = mensaje_error($r, 'No pudimos desactivar la verificación en dos pasos.');
        }
    }
}

// Estado actual (después de procesar el formulario)
$perfil = api_solicitud('GET', '/api/v1/auth/perfil/', null, $token);
sesion_vencida($perfil);
$activo = !empty($perfil['datos']['doble_factor_activo']);
if ($activo) {
    unset($_SESSION['2fa_pendiente']);
}
$pendiente = $_SESSION['2fa_pendiente'] ?? null;
$csrf = htmlspecialchars($_SESSION['csrf_seguridad']);
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seguridad de la cuenta - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/login.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
    <style>
        .seguridad-estado { font-size: 14px; margin-bottom: 16px; }
        .seguridad-qr { display: block; margin: 16px auto; width: 200px; height: 200px; image-rendering: pixelated; }
        .seguridad-secreto { font-family: monospace; font-size: 14px; word-break: break-all; background: #f3f4f6; padding: 8px; border-radius: 6px; }
        .seguridad-codigos { font-family: monospace; font-size: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px;
                             background: #f3f4f6; padding: 12px; border-radius: 8px; margin: 12px 0; list-style: none; }
        .seguridad-aviso { color: #166534; background: #ecfdf5; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px; }
        .seguridad-pasos { font-size: 14px; padding-left: 18px; margin-bottom: 12px; }
        .btn-secundario-link { display: inline-block; margin-top: 12px; font-size: 14px; }
    </style>
</head>
<body class="login-body">
    <div class="login-wrapper">
        <div class="login-right" style="margin: 0 auto;">
            <div class="login-form-container">
                <h2>Verificación en dos pasos</h2>
                <p class="login-subtitle">
                    Además de tu contraseña, te pediremos un código de una app autenticadora
                    (Google Authenticator, Microsoft Authenticator, Authy u otra).
                </p>

                <?php if ($error): ?>
                    <div class="alert-error" style="color: #dc2626; background: #ffeeef; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px;">
                        <?= htmlspecialchars($error) ?>
                    </div>
                <?php endif; ?>
                <?php if ($aviso): ?>
                    <div class="seguridad-aviso"><?= htmlspecialchars($aviso) ?></div>
                <?php endif; ?>

                <?php if ($codigos_recuperacion !== null): ?>
                    <!-- Recién activado: los códigos se muestran esta única vez -->
                    <div class="seguridad-aviso">La verificación en dos pasos quedó activada.</div>
                    <h3>Tus códigos de recuperación</h3>
                    <p class="seguridad-estado">
                        Guárdalos en un lugar seguro. Si pierdes tu teléfono, cada código te deja entrar <strong>una sola vez</strong>.
                        <strong>No volverás a verlos.</strong>
                    </p>
                    <ul class="seguridad-codigos">
                        <?php foreach ($codigos_recuperacion as $c): ?>
                            <li><?= htmlspecialchars($c) ?></li>
                        <?php endforeach; ?>
                    </ul>
                    <a href="perfil.php" class="btn-submit" style="display: block; text-align: center; text-decoration: none;">Ya los guardé</a>

                <?php elseif ($activo): ?>
                    <p class="seguridad-estado">Estado: <strong>activada</strong> ✅</p>
                    <form method="POST" action="seguridad.php" autocomplete="off"
                          onsubmit="return confirm('¿Desactivar la verificación en dos pasos? Tu cuenta quedará protegida solo por la contraseña.');">
                        <input type="hidden" name="csrf" value="<?= $csrf ?>">
                        <input type="hidden" name="accion" value="desactivar">
                        <div class="form-group">
                            <label for="codigo">Para desactivarla, ingresa un código de tu app o de recuperación</label>
                            <div class="input-with-icon">
                                <span class="input-icon">🔐</span>
                                <input type="text" id="codigo" name="codigo" placeholder="123456" maxlength="20"
                                       autocomplete="one-time-code" required>
                            </div>
                        </div>
                        <button type="submit" class="btn-submit">Desactivar</button>
                    </form>

                <?php elseif ($pendiente): ?>
                    <ol class="seguridad-pasos">
                        <li>Abre tu app autenticadora y escanea este código QR.</li>
                        <li>Escribe el código de 6 dígitos que aparece en la app.</li>
                    </ol>
                    <img class="seguridad-qr" alt="Código QR para la app autenticadora"
                         src="data:image/png;base64,<?= htmlspecialchars($pendiente['qr']) ?>">
                    <p class="seguridad-estado">¿No puedes escanearlo? Escribe esta clave en la app:</p>
                    <p class="seguridad-secreto"><?= htmlspecialchars($pendiente['secreto']) ?></p>

                    <form method="POST" action="seguridad.php" autocomplete="off" style="margin-top: 16px;">
                        <input type="hidden" name="csrf" value="<?= $csrf ?>">
                        <input type="hidden" name="accion" value="confirmar">
                        <div class="form-group">
                            <label for="codigo">Código de la app</label>
                            <div class="input-with-icon">
                                <span class="input-icon">🔐</span>
                                <input type="text" id="codigo" name="codigo" placeholder="123456" inputmode="numeric"
                                       maxlength="7" autocomplete="one-time-code" autofocus required>
                            </div>
                        </div>
                        <button type="submit" class="btn-submit">Confirmar y activar</button>
                    </form>
                    <form method="POST" action="seguridad.php">
                        <input type="hidden" name="csrf" value="<?= $csrf ?>">
                        <input type="hidden" name="accion" value="cancelar">
                        <button type="submit" class="btn-secundario-link" style="background: none; border: none; color: #6b7280; cursor: pointer;">Cancelar</button>
                    </form>

                <?php else: ?>
                    <p class="seguridad-estado">Estado: <strong>desactivada</strong></p>
                    <form method="POST" action="seguridad.php">
                        <input type="hidden" name="csrf" value="<?= $csrf ?>">
                        <input type="hidden" name="accion" value="activar">
                        <button type="submit" class="btn-submit">Activar verificación en dos pasos</button>
                    </form>
                <?php endif; ?>

                <p class="register-redirect">
                    <a href="perfil.php">← Volver a mi perfil</a>
                </p>
            </div>
        </div>
    </div>
</body>
</html>
