# SafingData — SSH Backup Portable

Programa portable de backup seguro hacia un servidor SSH, ejecutable directamente desde un **pendrive** en Windows o Linux, sin instalación en el sistema host.

---

## Inicio rápido

### Primera vez (requiere internet)

**Windows:**
```
setup_libs.bat
```

**Linux:**
```bash
./setup_libs.sh
```

Esto descarga `paramiko` y sus dependencias en la carpeta `libs/` del pendrive.

---

### Ejecutar el programa

**Windows (doble clic o CMD):**
```
run.bat
```

**Linux:**
```bash
./run.sh
```

---

## Uso del programa

1. Hacer clic en **CONECTAR** e ingresar la contraseña SSH.
2. Usar **+ Archivo** o **+ Carpeta** para seleccionar qué backupear.
3. Hacer clic en **▶ INICIAR BACKUP COMPLETO**.
4. El programa sube todo al servidor y registra la fecha de expiración.

### Backups y expiración

- Cada backup dura **14 días** en el servidor.
- Al cumplirse las 2 semanas, el programa te preguntará si quieres **descargar** los datos antes de eliminarlos.
- También puedes descargar o eliminar manualmente desde el panel "BACKUPS ACTIVOS".

### Espacio disponible

El programa reserva automáticamente **20 GB** del servidor para el sistema operativo y solo usa el espacio restante para los backups.

---

## Estructura del pendrive

```
SafingData/
├── run.bat              ← Lanzador Windows
├── run.sh               ← Lanzador Linux
├── setup_libs.bat       ← Instalar dependencias (Windows)
├── setup_libs.sh        ← Instalar dependencias (Linux)
├── setup_libs.py        ← Script de instalación (cualquier OS)
├── app/
│   ├── main.py          ← Punto de entrada
│   ├── backup.py        ← Motor SSH/SFTP
│   ├── storage.py       ← Gestión de espacio
│   ├── scheduler.py     ← Control de expiración 14 días
│   ├── config.py        ← Configuración persistente
│   └── ui/              ← Interfaz gráfica Tkinter
├── libs/                ← Dependencias (generado por setup_libs)
└── data/                ← Configuración y sesiones locales
```

---

## Servidor SSH

| Parámetro | Valor |
|-----------|-------|
| Host | `190.220.229.45` |
| Puerto | `3025` |
| Usuario | `gabodev24` |
| Auth | Contraseña |

Los backups se guardan en `~/safingdata_backups/` en el servidor.

---

## Requisitos

| Sistema | Requisito |
|---------|-----------|
| Windows | Python 3.8+ (o Python embebido en `python-embed/`) |
| Linux | Python 3.8+ (generalmente preinstalado) |
| Ambos | Tkinter (incluido con Python estándar) |

> **Nota:** Tkinter viene incluido con Python en Windows. En Linux puede requerir:
> ```bash
> sudo apt install python3-tk   # Ubuntu/Debian
> sudo dnf install python3-tkinter  # Fedora
> ```

---

## Configuración avanzada

La configuración se guarda en `data/config.json`. Puedes modificarla directamente o usando el botón **⚙** en la interfaz.

```json
{
  "host": "190.220.229.45",
  "port": 3025,
  "user": "gabodev24",
  "remote_base": "safingdata_backups",
  "selected_paths": []
}
```

---

*SafingData v1.0.0 — Diseñado con el sistema táctico SpiderWeb*
