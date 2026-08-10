<div align="center">

# 🔐 SafingData — SSH Backup Portable

**Herramienta de backup seguro hacia servidores SSH/SFTP, ejecutable directamente desde un pendrive en Windows y Linux, sin instalación en el sistema host.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)](.)
[![GUI](https://img.shields.io/badge/GUI-Tkinter-orange)](.)

</div>

---

## 📋 Índice

- [¿Qué es SafingData?](#-qué-es-safingdata)
- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalación y configuración inicial](#-instalación-y-configuración-inicial)
- [Configurar tu servidor SSH](#-configurar-tu-servidor-ssh)
- [Uso del programa](#-uso-del-programa)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Configuración avanzada](#-configuración-avanzada)
- [Solución de problemas](#-solución-de-problemas)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)

---

## 🚀 ¿Qué es SafingData?

SafingData es una aplicación de escritorio portable (basada en Python + Tkinter) que te permite hacer **backups completos de archivos y carpetas hacia cualquier servidor SSH** que tengas disponible. Está diseñada para ejecutarse directamente desde un pendrive, sin necesidad de instalar nada en la computadora donde se use.

---

## ✨ Características

- ✅ **100% portable** — corre desde pendrive, sin instalación
- ✅ **Multiplataforma** — Windows y Linux (macOS con adaptaciones menores)
- ✅ **Múltiples servidores SSH** — asigna un **nombre clave** (alias) a cada máquina y cambia de servidor al instante
- ✅ **Protección de privacidad** — oculta por defecto el host y usuario en la interfaz (`••••••••••`) con botón **mostrar/ocultar**
- ✅ **Puerto SSH opcional** — déjalo en blanco y usará automáticamente el puerto estándar `22`
- ✅ **Prueba de conexión** — verifica el acceso SSH directamente desde la ventana de configuración
- ✅ **Backup completo** via SSH/SFTP con `paramiko`
- ✅ **Progreso en tiempo real** con barra de avance y ETA
- ✅ **Gestión de backups** — listar, descargar y eliminar desde la interfaz
- ✅ **Verificación de espacio** — reserva automática para el sistema operativo del servidor
- ✅ **Cancelación segura** — limpia los archivos parciales en el servidor al cancelar
- ✅ **Configuración persistente** — guarda tus perfiles SSH en `data/config.json`
- ✅ **Interfaz oscura** — diseño táctico de alta legibilidad

---

## 📦 Requisitos

### En la computadora donde usas el pendrive

| Sistema | Requisito mínimo |
|---------|-----------------|
| Windows | Python 3.8+ ([descargar](https://www.python.org/downloads/)) o Python embebido en `python-embed/` |
| Linux   | Python 3.8+ (generalmente preinstalado) |
| Ambos   | Tkinter (incluido con Python estándar en Windows) |

> **Linux — Instalar Tkinter si falta:**
> ```bash
> # Ubuntu/Debian
> sudo apt install python3-tk
>
> # Fedora
> sudo dnf install python3-tkinter
>
> # Arch Linux
> sudo pacman -S tk
> ```

### En el servidor remoto (donde se guardan los backups)

| Requisito | Detalle |
|-----------|---------|
| Sistema operativo | Cualquier Linux con servidor SSH activo |
| Acceso | Usuario con contraseña SSH |
| Espacio | El que quieras asignar a los backups |
| Software | Solo `sshd` estándar — no requiere nada adicional |

---

## 🛠️ Instalación y configuración inicial

### Paso 1 — Clonar o descargar el repositorio

```bash
git clone https://github.com/TU_USUARIO/SafingData.git
```

O descarga el ZIP desde GitHub y extrae en tu pendrive.

### Paso 2 — Instalar dependencias (solo la primera vez, requiere internet)

Las dependencias se instalan **localmente en la carpeta `libs/`** del proyecto, sin afectar el sistema.

**Windows:**
```
setup_libs.bat
```

**Linux / macOS:**
```bash
chmod +x setup_libs.sh run.sh
./setup_libs.sh
```

**Cualquier sistema (manual):**
```bash
python setup_libs.py
```

> ℹ️ Esto descarga `paramiko` y sus dependencias criptográficas en `libs/`. Solo necesitas hacerlo una vez; después puedes usar el pendrive sin internet.

### Paso 3 — Configurar tu servidor SSH

Antes de usar el programa, edita `data/config.json` (ver sección de [configuración](#-configurar-tu-servidor-ssh)).

---

## 🔧 Configurar tu servidor SSH

### Opción A — Desde la interfaz (recomendado)

1. Abre el programa (ver [ejecutar](#-ejecutar-el-programa))
2. Haz clic en el botón **⚙** (engranaje) en la barra superior
3. Selecciona una máquina existente o haz clic en **+ Nueva** para crear un nuevo perfil con su **NOMBRE CLAVE**
4. Rellena los campos: **NOMBRE CLAVE**, **HOST / IP**, **PUERTO** (opcional, por defecto 22), **USUARIO SSH**, **DIR. REMOTO**
5. (Opcional) Haz clic en **Probar conexión** para validar el acceso sin guardar aún
6. Haz clic en **GUARDAR**

### Opción B — Editar el archivo directamente

Crea o edita el archivo `data/config.json`:

```json
{
  "machines": [
    {
      "name": "Servidor Principal",
      "host": "192.168.1.100",
      "port": 22,
      "user": "mi_usuario",
      "remote_base": "safingdata_backups"
    },
    {
      "name": "VPS Trabajo",
      "host": "vps.ejemplo.com",
      "port": 22,
      "user": "ubuntu",
      "remote_base": "safingdata_backups"
    }
  ],
  "active_machine": "Servidor Principal",
  "selected_paths": []
}
```

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `name` | Nombre clave o alias descriptivo para la máquina | `"Servidor Casa"`, `"VPS Producción"` |
| `host` | IP o dominio del servidor SSH | `"192.168.1.100"` o `"backup.midominio.com"` |
| `port` | Puerto SSH del servidor (opcional, por defecto 22) | `22` |
| `user` | Tu nombre de usuario en el servidor | `"ubuntu"`, `"pi"`, `"root"` |
| `remote_base` | Carpeta donde se guardan los backups (relativa al home del usuario) | `"safingdata_backups"` |
| `active_machine` | Nombre clave de la máquina actualmente activa | `"Servidor Principal"` |

> ℹ️ Si abres el programa con un archivo `config.json` en el formato antiguo (versión 1.0), este **se migrará automáticamente** al nuevo formato multi-máquina.

> ⚠️ **El archivo `data/config.json` está en `.gitignore`** y nunca se sube a GitHub. Tus credenciales de servidor están seguras.

---

## ▶️ Ejecutar el programa

### Windows
```
run.bat
```
O doble clic en `run.bat` desde el Explorador de archivos.

### Linux / macOS
```bash
./run.sh
```

---

## 📖 Uso del programa

### 1. Conectar al servidor SSH

- Haz clic en el botón **CONECTAR** (esquina superior derecha)
- Ingresa tu **contraseña SSH** en el diálogo que aparece
- El indicador de estado cambiará a verde: **CONECTADO**

> 💡 La contraseña **nunca se guarda** en disco. Debes ingresarla cada vez que conectes.

### 2. Seleccionar archivos y carpetas

En el panel izquierdo:
- **+ Archivo** — agrega uno o más archivos específicos
- **+ Carpeta** — agrega una carpeta completa (se sube de forma recursiva)
- **✕** — elimina un ítem de la selección

El panel derecho muestra el **tamaño total** de lo seleccionado y el **espacio disponible** en el servidor.

### 3. Iniciar el backup

- Haz clic en **▶ INICIAR BACKUP COMPLETO**
- Asigna un nombre al backup (o usa el timestamp predeterminado)
- Confirma el diálogo de confirmación
- Observa el progreso en tiempo real con barra de avance y ETA

### 4. Gestionar backups guardados

En el panel **BACKUPS ACTIVOS** (columna derecha):

| Botón | Acción |
|-------|--------|
| ⬇ Descargar | Descarga el backup seleccionado a una carpeta local |
| ✕ Eliminar | Elimina permanentemente el backup del servidor |

> ⚠️ La eliminación es **permanente e irreversible**. Siempre descarga primero si necesitas recuperar datos.

### 5. Cancelar un backup en curso

- Haz clic en **◼ CANCELAR** durante un backup activo
- El programa cancelará la transferencia y **limpiará automáticamente** los archivos parciales en el servidor

---

## 📁 Estructura del proyecto

```
SafingData/
├── run.bat                 ← Lanzador Windows
├── run.sh                  ← Lanzador Linux/macOS
├── setup_libs.bat          ← Instalar dependencias (Windows)
├── setup_libs.sh           ← Instalar dependencias (Linux/macOS)
├── setup_libs.py           ← Script de instalación Python (cualquier OS)
│
├── app/
│   ├── __init__.py
│   ├── main.py             ← Punto de entrada y verificación de dependencias
│   ├── backup.py           ← Motor SSH/SFTP (paramiko): upload, download, delete
│   ├── storage.py          ← Cálculo de tamaño local y verificación de cuota remota
│   ├── scheduler.py        ← Registro local de sesiones de backup (session.json)
│   ├── config.py           ← Carga/guarda configuración (config.json)
│   └── ui/
│       ├── __init__.py
│       ├── app_window.py   ← Ventana principal y lógica de la UI
│       ├── file_selector.py ← Panel selector de archivos/carpetas
│       ├── progress_panel.py ← Barra de progreso y log de eventos
│       └── styles.py       ← Paleta de colores, fuentes y estilos ttk
│
├── libs/                   ← Dependencias instaladas (generado por setup_libs, en .gitignore)
│
└── data/                   ← Datos locales persistentes (en .gitignore)
    ├── config.json         ← Tu configuración de servidor SSH (NO se sube a GitHub)
    └── session.json        ← Registro de backups realizados (NO se sube a GitHub)
```

---

## ⚙️ Configuración avanzada

### Reserva de sistema

Por defecto, SafingData reserva **20 GB** del espacio total del servidor para el sistema operativo del servidor y solo permite subir backups en el espacio restante. Esta reserva está definida en `app/storage.py`:

```python
SYSTEM_RESERVE_GB = 20
```

Modifica este valor según las necesidades de tu servidor.

### Dependencias instaladas

El script `setup_libs.py` instala en `libs/`:

| Paquete | Versión mínima | Propósito |
|---------|---------------|-----------|
| `paramiko` | 3.4.0 | Protocolo SSH/SFTP |
| `bcrypt` | 4.0.0 | Hashing de claves SSH |
| `cryptography` | 41.0.0 | Operaciones criptográficas |
| `pynacl` | 1.5.0 | Criptografía NaCl |
| `cffi` | 1.16.0 | Interfaz C para cryptography |

### Python embebido (Windows sin Python instalado)

En Windows puedes colocar un Python embebido en `python-embed/` para que el programa funcione sin que el sistema tenga Python instalado. Descarga la versión embebida desde [python.org](https://www.python.org/downloads/windows/) (busca "Windows embeddable package").

---

## 🔒 Seguridad y privacidad

- La **contraseña SSH nunca se almacena en disco** — se pide cada vez que conectas
- El archivo `data/config.json` (con host/usuario) **está en `.gitignore`** — no se sube a GitHub
- El archivo `data/session.json` (registro de backups) también **está en `.gitignore`**
- La carpeta `libs/` (dependencias) también **está en `.gitignore`**
- Las transferencias van cifradas por SSH/SFTP (no texto plano)

---

## 🛟 Solución de problemas

### ❌ "ModuleNotFoundError: No module named 'paramiko'"

Las dependencias no están instaladas. Ejecuta:
```bash
./setup_libs.sh   # Linux/macOS
setup_libs.bat    # Windows
```

### ❌ "No se pudo conectar: Connection refused"

- Verifica que el servidor SSH esté activo: `sudo systemctl status ssh`
- Confirma el **puerto** correcto (por defecto 22, puede ser diferente)
- Asegúrate de que el firewall permita el puerto SSH

### ❌ "No se pudo conectar: Authentication failed"

- Verifica usuario y contraseña
- Asegúrate de que el usuario tiene acceso SSH al servidor

### ❌ Error de Tkinter en Linux

```bash
sudo apt install python3-tk    # Ubuntu/Debian
sudo dnf install python3-tkinter  # Fedora
```

### ❌ El backup se cancela solo

- Verifica tu conexión de red — la transferencia SSH se corta si hay pérdida de conexión
- Aumenta el timeout en `backup.py` si tu servidor responde lento (parámetro `timeout=30`)

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Para contribuir:

1. Haz un **fork** del repositorio
2. Crea una rama con tu feature: `git checkout -b feature/nueva-funcionalidad`
3. Haz tus cambios y commitea: `git commit -m 'feat: añadir nueva funcionalidad'`
4. Push a tu fork: `git push origin feature/nueva-funcionalidad`
5. Abre un **Pull Request**

### Ideas de mejoras

- [ ] Autenticación por clave pública (`.pem`/`.ppk`)
- [ ] Backups incrementales (solo archivos modificados)
- [ ] Programación automática (backup diario/semanal)
- [ ] Cifrado local antes del upload
- [ ] Soporte para múltiples servidores

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

<div align="center">

*SafingData v1.1.0 — Diseñado por GaboDev - CEO DE SPIDERWEB*  
[Ver Registro de Cambios (CHANGELOG.md)](CHANGELOG.md)

</div>
