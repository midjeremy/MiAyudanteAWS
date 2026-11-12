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
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Perfil - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/carreras.css">
    <link rel="stylesheet" href="/static/css/perfil.css">
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

                <button type="button" class="btn-perfil btn-secundario" disabled title="Disponible próximamente">
                    Editar perfil (próximamente)
                </button>
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
                    <strong>—</strong>
                    <span>test vocacional pendiente</span>
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
                <div class="perfil-vacio">
                    <p>Todavía no tienes resultados. Responde el test para descubrir qué áreas se relacionan con tus intereses.</p>
                    <a href="pages/test.php" class="btn-perfil btn-primario">Hacer el test</a>
                </div>
            </div>
        </section>

    </main>

</body>
</html>