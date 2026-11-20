# Mi Plaza Segura

Aplicación web para que los vecinos de Las Heras, Mendoza, informen problemas en plazas públicas y consulten su seguimiento. Está desarrollada con Flask, SQLite, HTML, CSS, JavaScript y Leaflet/OpenStreetMap.

## Requisitos

- Python 3.10 o posterior.
- `pip`.
- Acceso a Internet para cargar los mosaicos de OpenStreetMap, Leaflet y la fotografía de portada.

## Instalación y ejecución local

1. Abrí una terminal en la carpeta del proyecto.
2. Creá y activá un entorno virtual:

   **Linux/macOS**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows (PowerShell)**
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Instalá las dependencias:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Configurá una clave secreta antes de iniciar el servidor. Usá un valor aleatorio privado y no lo subas al repositorio:

   **Linux/macOS**
   ```bash
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

   **Windows (PowerShell)**
   ```powershell
   $env:SECRET_KEY = (py -c "import secrets; print(secrets.token_hex(32))")
   ```

5. Iniciá la aplicación:

   ```bash
   flask --app app run --debug
   ```

6. Abrí <http://127.0.0.1:5000>.

La base SQLite se inicializa automáticamente en `database/plaza_segura.db`. Las fotografías de plazas se guardan en `static/uploads/`; las fotos adjuntas a reclamos se guardan fuera del directorio público en `database/private_uploads/` y solo se sirven a administradores autenticados. Estos datos se excluyen del control de versiones para proteger la información de vecinos.

## Crear la cuenta de administración

En otra terminal, desde la raíz del proyecto y con el entorno virtual activado, ejecutá:

```bash
flask --app app create-admin
```

Ingresá un nombre de usuario y una contraseña de al menos 12 caracteres cuando se soliciten. Las contraseñas se almacenan con un hash seguro. Para volver a establecer la clave de un usuario existente, ejecutá el comando otra vez con el mismo nombre.

Luego iniciá sesión desde **Administración** en el menú. El panel permite filtrar reclamos, consultar sus descripciones y fotografías, actualizar su estado, ver estadísticas y crear, editar o eliminar plazas. Una plaza asociada a reclamos no puede eliminarse para conservar el historial.

## Carga de plazas y coordenadas

La aplicación inicia sin plazas precargadas: no se incluyen ubicaciones inventadas. Un administrador debe registrar nombre, dirección y coordenadas confirmadas antes de que aparezca una plaza en el mapa. Verificá latitud y longitud con una fuente oficial o confiable antes de cargarlas. El centro que muestra el mapa cuando no hay marcadores es solo una referencia general de Las Heras, no la ubicación de una plaza.

## Reclamos y privacidad

- El nombre y el correo son opcionales; no se muestran en la consulta pública de seguimiento.
- Cada reclamo recibe un código aleatorio único. El vecino puede consultarlo desde **Seguimiento**.
- Los estados disponibles son Pendiente, En revisión, En proceso y Solucionado.
- Los adjuntos aceptados son imágenes JPG, PNG y WEBP de hasta 5 MB.
- Las fotografías de reclamos no son públicas: solo se pueden abrir desde el panel administrativo después de iniciar sesión.
- Las rutas administrativas y formularios están protegidos con sesión y CSRF. Configurá `SECRET_KEY` privada y usá HTTPS en producción.
- El botón de emergencia no envía alertas: abre una confirmación con un enlace telefónico directo al 911.

## Configuración opcional

Se pueden definir las siguientes variables de entorno:

| Variable | Uso | Valor predeterminado |
|---|---|---|
| `SECRET_KEY` | Firma de sesiones y protección CSRF. Obligatoria para despliegues persistentes. | Clave aleatoria al iniciar el proceso |
| `DATABASE_PATH` | Ruta del archivo SQLite. | `database/plaza_segura.db` |
| `UPLOAD_FOLDER` | Carpeta de fotografías. | `static/uploads` |
| `COOKIE_SECURE` | Definir `1` para exigir cookies seguras bajo HTTPS. | `0` para desarrollo local |
| `FLASK_DEBUG` | Definir `1` para activar modo debug al ejecutar `python app.py`. | Desactivado |

Leaflet y los mosaicos del mapa usan servicios públicos de OpenStreetMap/Unpkg; la portada carga una fotografía alojada en Unsplash. No requieren credenciales. Para producción, revisá las políticas de uso de esos servicios y considerá alojar los recursos localmente.

## Estructura principal

```text
app.py
config.py
models.py
requirements.txt
database/
templates/
  base.html
  index.html
  reclamos.html
  confirmacion.html
  mapa.html
  seguimiento.html
  login.html
  admin.html
static/
  css/styles.css
  js/main.js
  js/map.js
  uploads/
database/private_uploads/
```
