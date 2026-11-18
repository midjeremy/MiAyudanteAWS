<?php
session_start();
require_once 'api.php';
require_once 'catalogo.php';

// Si no ha iniciado sesión, redirigir al login
if (!isset($_SESSION['usuario'])) {
    header('Location: login.php');
    exit;
}

$usuario = $_SESSION['usuario'];

// Datos reales que entrega Django al iniciar sesión
$nombre = $usuario['nombre'] ?? '';
$apellidos = $usuario['apellidos'] ?? '';
$nombreCompleto = trim($nombre . ' ' . $apellidos);
if ($nombreCompleto === '') {
    $nombreCompleto = $usuario['username'] ?? 'Usuario';
}

$correo = $usuario['correo'] ?? $usuario['email'] ?? 'Sin correo registrado';
$tipoEstudiante = $usuario['tipo'] ?? 'Estudiante';
$ciudad = $usuario['ciudad'] ?? 'No especificada';
$institucion = $usuario['institucion'] ?? 'No especificada';
$avatar = !empty($usuario['avatar']) ? $usuario['avatar'] : '/static/img/gato-avatar.png';

// Carreras guardadas reales (las mismas que se ven en guardados.php)
$ids_guardados = $_SESSION['favoritos'] ?? [];
$carreras_guardadas = [];
if (!empty($ids_guardados)) {
    $ids = implode(',', array_map('intval', $ids_guardados));
    $respuesta = api_get('/api/v1/ofertas/?' . http_build_query(['ids' => $ids, 'page_size' => 100]));
    foreach ($respuesta['results'] ?? [] as $row) {
        $carreras_guardadas[] = oferta_a_tarjeta($row);
    }
}
$total_guardadas = count($ids_guardados);
$guardadas_vista = array_slice($carreras_guardadas, 0, 4);

// ===================== [LEY 21.719] Derechos del titular =====================
// Rectificación (editar nombre), supresión (borrar resultados del test o la cuenta) y acceso
// (descargar mis datos, en mis_datos.php). Django hace el cambio real en la base de datos.
$token = $_SESSION['token_acceso'] ?? null;
if (empty($_SESSION['csrf_privacidad'])) {
    $_SESSION['csrf_privacidad'] = bin2hex(random_bytes(16));
}

function volver_a_privacidad(string $tipo, string $texto): void {
    // Patrón POST-redirección-GET: recargar la página no repite la acción
    $_SESSION['flash_privacidad'] = ['tipo' => $tipo, 'texto' => $texto];
    header('Location: perfil.php#privacidad');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['accion'])) {
    if (!hash_equals($_SESSION['csrf_privacidad'], (string) ($_POST['csrf'] ?? ''))) {
        volver_a_privacidad('error', 'La página expiró. Vuelve a intentarlo.');
    }
    if ($token === null) {
        volver_a_privacidad('error', 'Tu sesión expiró. Cierra sesión e inicia de nuevo.');
    }

    $accion = $_POST['accion'];
    if ($accion === 'editar_nombre') {
        $r = api_solicitud('PATCH', '/api/v1/auth/perfil/', [
            'nombre' => trim($_POST['nombre'] ?? ''),
            'apellidos' => trim($_POST['apellidos'] ?? ''),
        ], $token);
        if ($r['codigo'] === 200) {
            $_SESSION['usuario'] = array_merge($_SESSION['usuario'], $r['datos']['usuario']);
            volver_a_privacidad('ok', 'Actualizamos tu nombre.');
        }
    } elseif ($accion === 'borrar_resultado') {
        $id_resultado = (int) ($_POST['resultado_id'] ?? 0);
        $r = api_solicitud('DELETE', '/api/v1/auth/mis-datos/resultados/' . $id_resultado . '/', null, $token);
        if ($r['codigo'] === 204) {
            volver_a_privacidad('ok', 'Eliminamos ese resultado del test.');
        }
    } elseif ($accion === 'eliminar_cuenta') {
        $r = api_solicitud('DELETE', '/api/v1/auth/cuenta/', ['password' => $_POST['password'] ?? ''], $token);
        if ($r['codigo'] === 204) {
            // La cuenta y todos sus datos ya no existen: se cierra la sesión
            $_SESSION = [];
            session_destroy();
            header('Location: index.php?cuenta_eliminada=1');
            exit;
        }
        if ($r['codigo'] === 403) {
            volver_a_privacidad('error', 'La contraseña no es correcta. Tu cuenta no se eliminó.');
        }
    } else {
        volver_a_privacidad('error', 'Acción no reconocida.');
    }

    if ($r['codigo'] === 401) {
        volver_a_privacidad('error', 'Tu sesión expiró. Cierra sesión e inicia de nuevo.');
    }
    if ($r['codigo'] === 429) {
        volver_a_privacidad('error', 'Demasiados intentos. Espera un minuto e inténtalo de nuevo.');
    }
    volver_a_privacidad('error', $r['datos']['error'] ?? 'No pudimos completar la acción. Inténtalo más tarde.');
}

$flash = $_SESSION['flash_privacidad'] ?? null;
unset($_SESSION['flash_privacidad']);

// Datos actuales del titular: cuenta y resultados del test guardados
$mis_datos = null;
if ($token !== null) {
    $r = api_solicitud('GET', '/api/v1/auth/mis-datos/', null, $token);
    if ($r['codigo'] === 200 && is_array($r['datos'])) {
        $mis_datos = $r['datos'];
    }
}
$resultados_test = $mis_datos['resultados_test'] ?? [];
$nombre_editable = $mis_datos['cuenta']['nombre'] ?? $nombre;
$apellidos_editable = $mis_datos['cuenta']['apellidos'] ?? $apellidos;

function fecha_corta(?string $iso): string {
    $fecha = $iso ? date_create($iso) : false;
    return $fecha ? $fecha->format('d-m-Y') : '';
}
// =============================================================================
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Perfil - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/carreras.css">
    <link rel="stylesheet" href="/static/css/perfil.css">
    <link rel="stylesheet" href="/static/css/privacidad.css"><!-- [LEY 21.719] -->
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body class="portal-body">

    <!-- BARRA DE NAVEGACIÓN SUPERIOR UNIFICADA -->
    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-logo-icon">🎓</span>
            <div class="nav-logo-text">
                <strong>Mi Ayudante</strong>
                <span>Tu futuro, nuestra guía</span>
            </div>
        </div>
        <ul class="nav-links">
            <li><a href="index.php">Inicio</a></li>
            <li><a href="carreras.php">Explorar carreras</a></li>
            <li><a href="comparar.php">Comparar</a></li>
            <li><a href="pages/test.php">Test vocacional</a></li>
        </ul>
        <div class="nav-actions">
            <a href="guardados.php" class="btn-action-saved" title="Guardados">
                <span>❤️</span> Guardados
            </a>
            <details class="user-menu-container">
                <summary class="user-menu-btn" title="Perfil">
                    <img src="<?= htmlspecialchars($avatar) ?>" alt="Perfil" class="user-avatar-img">
                    <span class="dropdown-arrow">▼</span>
                </summary>
                <div class="user-dropdown">
                    <a href="perfil.php" class="dropdown-item">Perfil</a>
                    <div class="dropdown-divider"></div>
                    <a href="logout.php" class="dropdown-item logout-item">Cerrar sesión</a>
                </div>
            </details>
        </div>
    </nav>

    <main class="perfil-contenedor">

        <!-- COLUMNA IZQUIERDA: DATOS DEL USUARIO -->
        <aside class="perfil-lateral">
            <div class="perfil-tarjeta perfil-usuario">
                <div class="perfil-avatar">
                    <img src="<?= htmlspecialchars($avatar) ?>" alt="Avatar de <?= htmlspecialchars($nombreCompleto) ?>"
                         onerror="this.remove()">
                </div>
                <h1><?= htmlspecialchars($nombreCompleto) ?></h1>
                <p class="perfil-tipo"><?= htmlspecialchars($tipoEstudiante) ?></p>

                <dl class="perfil-datos">
                    <div>
                        <dt>Correo electrónico</dt>
                        <dd><?= htmlspecialchars($correo) ?></dd>
                    </div>
                    <div>
                        <dt>Ciudad</dt>
                        <dd><?= htmlspecialchars($ciudad) ?></dd>
                    </div>
                    <div>
                        <dt>Institución o casa de estudios</dt>
                        <dd><?= htmlspecialchars($institucion) ?></dd>
                    </div>
                </dl>

                <!-- [LEY 21.719] Rectificación: antes era un botón deshabilitado -->
                <a href="#privacidad" class="btn-perfil btn-secundario">Editar mis datos</a>
                <a href="logout.php" class="btn-perfil btn-salir">Cerrar sesión</a>
            </div>
        </aside>

        <!-- CONTENIDO PRINCIPAL -->
        <section class="perfil-principal">
            <h2 class="perfil-titulo">Hola, <?= htmlspecialchars($nombre ?: $nombreCompleto) ?> 👋</h2>

            <nav class="perfil-pestanas" aria-label="Secciones del perfil">
                <a href="perfil.php" class="activa"><span>👤</span> Mi perfil</a>
                <a href="guardados.php"><span>❤️</span> Carreras guardadas</a>
                <a href="comparar.php"><span>⚖️</span> Comparar</a>
                <a href="pages/test.php"><span>📋</span> Test vocacional</a>
            </nav>

            <div class="perfil-resumen">
                <div class="perfil-tarjeta perfil-stat">
                    <strong><?= $total_guardadas ?></strong>
                    <span><?= $total_guardadas === 1 ? 'carrera guardada' : 'carreras guardadas' ?></span>
                </div>
                <div class="perfil-tarjeta perfil-stat">
                    <!-- [LEY 21.719] Cuántos resultados del test hay guardados en la cuenta -->
                    <strong><?= count($resultados_test) ?: '—' ?></strong>
                    <span><?= count($resultados_test) === 1 ? 'resultado del test guardado' : (count($resultados_test) ? 'resultados del test guardados' : 'test vocacional pendiente') ?></span>
                </div>
            </div>

            <!-- CARRERAS GUARDADAS -->
            <div class="perfil-tarjeta">
                <div class="perfil-tarjeta-cabecera">
                    <h3>Carreras guardadas</h3>
                    <?php if ($total_guardadas > 0): ?>
                        <a href="guardados.php" class="enlace-ver">Ver todas →</a>
                    <?php endif; ?>
                </div>

                <?php if (empty($guardadas_vista)): ?>
                    <div class="perfil-vacio">
                        <p><?= $total_guardadas > 0
                            ? 'No pudimos cargar tus carreras guardadas. Inténtalo más tarde.'
                            : 'Aún no guardas carreras. Marca el ❤️ en las que te interesen.' ?></p>
                        <a href="carreras.php" class="btn-perfil btn-primario">Explorar carreras</a>
                    </div>
                <?php else: ?>
                    <ul class="perfil-guardadas">
                        <?php foreach ($guardadas_vista as $carrera): ?>
                            <li>
                                <span class="badge <?= htmlspecialchars($carrera['categoria_clase']) ?>">
                                    <?= htmlspecialchars($carrera['categoria']) ?>
                                </span>
                                <strong><?= htmlspecialchars($carrera['nombre']) ?></strong>
                                <small><?= htmlspecialchars($carrera['institucion']) ?> · <?= htmlspecialchars($carrera['ubicacion']) ?></small>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                <?php endif; ?>
            </div>

            <!-- TEST VOCACIONAL -->
            <div class="perfil-tarjeta">
                <div class="perfil-tarjeta-cabecera">
                    <h3>Mi test vocacional</h3>
                </div>
                <?php if (empty($resultados_test)): ?>
                    <div class="perfil-vacio">
                        <p>Todavía no tienes resultados. Responde el test para descubrir qué áreas se relacionan con tus intereses.</p>
                        <a href="pages/test.php" class="btn-perfil btn-primario">Hacer el test</a>
                    </div>
                <?php else: ?>
                    <!-- [LEY 21.719] Supresión parcial: cada resultado guardado se puede borrar -->
                    <ul class="privacidad-resultados">
                        <?php foreach ($resultados_test as $res): ?>
                            <li>
                                <span>Resultado del <?= htmlspecialchars(fecha_corta($res['creado_en'] ?? null)) ?></span>
                                <form method="POST" action="perfil.php" onsubmit="return confirm('¿Eliminar este resultado del test? No se puede deshacer.');">
                                    <input type="hidden" name="csrf" value="<?= htmlspecialchars($_SESSION['csrf_privacidad']) ?>">
                                    <input type="hidden" name="accion" value="borrar_resultado">
                                    <input type="hidden" name="resultado_id" value="<?= (int) $res['id'] ?>">
                                    <button type="submit" class="btn-privacidad-peligro">Eliminar</button>
                                </form>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                    <a href="pages/test.php" class="btn-perfil btn-primario">Ver mi último resultado</a>
                <?php endif; ?>
            </div>

            <!-- ===================== [LEY 21.719] MIS DATOS Y PRIVACIDAD ===================== -->
            <div class="perfil-tarjeta" id="privacidad">
                <div class="perfil-tarjeta-cabecera">
                    <h3>Mis datos y privacidad</h3>
                    <a href="privacidad.php" class="enlace-ver">Política de privacidad →</a>
                </div>

                <?php if ($flash): ?>
                    <div class="privacidad-aviso privacidad-aviso-<?= $flash['tipo'] === 'ok' ? 'ok' : 'error' ?>">
                        <?= htmlspecialchars($flash['texto']) ?>
                    </div>
                <?php endif; ?>

                <!-- Rectificación -->
                <form method="POST" action="perfil.php" class="privacidad-bloque">
                    <h4>Corregir mi nombre</h4>
                    <input type="hidden" name="csrf" value="<?= htmlspecialchars($_SESSION['csrf_privacidad']) ?>">
                    <input type="hidden" name="accion" value="editar_nombre">
                    <div class="privacidad-campos">
                        <label>Nombre <input type="text" name="nombre" value="<?= htmlspecialchars($nombre_editable) ?>" maxlength="150" required></label>
                        <label>Apellidos <input type="text" name="apellidos" value="<?= htmlspecialchars($apellidos_editable) ?>" maxlength="150" required></label>
                    </div>
                    <button type="submit" class="btn-perfil btn-secundario">Guardar cambios</button>
                </form>

                <!-- Acceso y portabilidad -->
                <div class="privacidad-bloque">
                    <h4>Descargar mis datos</h4>
                    <p>Un archivo con tu cuenta, tus consentimientos y tus resultados del test, en formato JSON.</p>
                    <a href="mis_datos.php" class="btn-perfil btn-secundario">Descargar mis datos</a>
                </div>

                <!-- Doble factor (app autenticadora) -->
                <div class="privacidad-bloque">
                    <h4>Verificación en dos pasos</h4>
                    <p>Protege tu cuenta pidiendo, además de la contraseña, un código de una app autenticadora.</p>
                    <a href="seguridad.php" class="btn-perfil btn-secundario">Configurar seguridad</a>
                </div>

                <!-- Supresión de la cuenta (también revoca el consentimiento) -->
                <form method="POST" action="perfil.php" class="privacidad-bloque privacidad-peligro"
                      onsubmit="return confirm('Se eliminarán tu cuenta y todos tus resultados del test. No se puede deshacer. ¿Continuar?');">
                    <h4>Eliminar mi cuenta</h4>
                    <p>Borra tu cuenta y todos sus datos. Podrás seguir usando la plataforma sin cuenta.</p>
                    <input type="hidden" name="csrf" value="<?= htmlspecialchars($_SESSION['csrf_privacidad']) ?>">
                    <input type="hidden" name="accion" value="eliminar_cuenta">
                    <label>Confirma con tu contraseña <input type="password" name="password" required autocomplete="current-password"></label>
                    <button type="submit" class="btn-privacidad-peligro">Eliminar mi cuenta</button>
                </form>

                <p class="privacidad-nota">
                    ¿Otra solicitud sobre tus datos (oposición o bloqueo)? Escríbenos a
                    <a href="mailto:privacidad@mi-ayudante.cl">privacidad@mi-ayudante.cl</a>. Respondemos en un máximo de 30 días corridos.
                </p>
            </div>
            <!-- ============================================================================ -->
        </section>

    </main>

</body>
</html>