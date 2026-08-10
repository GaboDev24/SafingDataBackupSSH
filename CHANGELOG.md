# 📜 Registro de Cambios (Changelog) - SafingData

Todos los cambios notables en este proyecto serán documentados en este archivo.

---

## [1.1.0] - 2026-08-10

### 🚀 Nuevas Características
- **Gestión de Múltiples Máquinas SSH (Nombres Clave / Aliases)**:
  - Ahora se pueden agregar, editar y guardar múltiples servidores SSH asignando a cada uno un **nombre clave** o alias distintivo (ej. *"Servidor Casa"*, *"VPS Producción"*, *"Trabajo"*).
  - Selector desplegable en el panel de configuración para alternar la máquina activa rápidamente.
  - Opción para agregar (`+ Nueva`) o eliminar perfiles de servidor SSH fácilmente.
- **Privacidad y Enmascaramiento de Datos Sensibles**:
  - En el panel principal *"SERVIDOR SSH"*, el **HOST** y el **USUARIO** se ocultan por defecto con caracteres de protección (`••••••••••`).
  - Se añade un botón interactivo **"mostrar / ocultar"** en la tarjeta del servidor para revelar o esconder los datos sensibles según el usuario lo requiera.
- **Puerto SSH Opcional**:
  - El puerto SSH pasa a ser **opcional**. Si se deja en blanco o no se especifica, el sistema utiliza el puerto predeterminado `22` automáticamente con un placeholder descriptivo.
- **Prueba de Conexión Integrada**:
  - Incorporación del botón **"Probar conexión"** directamente en la ventana de configuración para verificar si las credenciales y el host responden correctamente sin necesidad de iniciar una transferencia.
- **Migración Automática de Configuración**:
  - Retrocompatibilidad asegurada: si el sistema detecta un archivo `config.json` con el formato anterior (un único servidor suelto), se migra automáticamente a la nueva estructura de lista `machines`.

---

## [1.0.0] - Versión Inicial

- Lanzamiento inicial de SafingData SSH Backup Portable.
- Transferencias SSH/SFTP recursivas con `paramiko`.
- Selección de archivos/carpetas locales y monitoreo de espacio remoto.
- Interfaz gráfica oscura con diseño táctico SpiderWeb en Tkinter.
